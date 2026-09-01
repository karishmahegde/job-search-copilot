"""Pydantic schema for the user-supplied profile configuration (`profile.yaml`).

Defines the full shape of a clone's profile: resume, preferred roles,
location and compensation preferences, dream companies, referral contacts,
LLM provider selection, scoring thresholds, listing sources, digest
notifications, and shared-mode partners. This module only defines and
validates the shape — no consumer logic lives here.
"""

# Allows `X | None` union syntax safely across Python versions.
from __future__ import annotations

import re
from typing import Annotated, Literal

# ZoneInfo is used to validate real IANA timezone names (not just string shape).
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Pydantic building blocks:
#   ConfigDict         - configures model behavior, e.g. extra="forbid"
#   EmailStr           - built-in type that validates a string looks like an email
#   Field              - attaches constraints/defaults (ge=, le=, min_length=, ...)
#   StringConstraints  - string-specific constraints (strip whitespace, min length)
#   field_validator    - decorator for custom validation of ONE field
#   model_validator    - decorator for custom validation across MULTIPLE fields
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

# Reusable type alias: any field typed NonEmptyStr must have at least one
# non-whitespace character after trimming. Defined once, reused everywhere
# instead of repeating the same constraint on every field.
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_RESUME_SUFFIXES = (".pdf", ".docx")  # allowed resume file extensions
_TIME_24H = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")  # HH:MM, 24-hour
_ISO_4217 = re.compile(r"^[A-Z]{3}$")  # 3-letter uppercase currency code

# Literal types restrict a field to EXACTLY these string values and nothing
# else — this is what makes an unsupported source/provider name fail
# validation with a clear error instead of being silently accepted.
AtsSource = Literal["greenhouse", "lever", "ashby"]
AggregatorSource = Literal["adzuna_india", "remoteok", "himalayas"]
LlmProvider = Literal["anthropic", "openai", "ollama"]


class _Base(BaseModel):
    """Base model: reject unknown keys so a typo in `profile.yaml` is caught.

    Every other model in this file inherits from `_Base` instead of
    `BaseModel` directly. That's how `extra="forbid"` applies uniformly
    everywhere without repeating this config on every single class — it's
    a DRY pattern: set once here, inherited by every subclass below.

    The leading underscore is a Python convention meaning "private to this
    module" — `_Base` is not meant to be imported or used outside schema.py;
    it only exists as a shared ancestor for the classes below.
    """

    # ConfigDict is a Pydantic-provided config object (not something we wrote).
    # extra="forbid" means: if the input data has a key this model doesn't
    # define, validation FAILS and names the bad key. (Pydantic's default is
    # "ignore" — unknown keys get silently dropped, which would turn a typo
    # like "perferred_roles" into a confusing "missing required field" error
    # instead of pointing at the actual mistake.)
    model_config = ConfigDict(extra="forbid")


class Compensation(_Base):
    """Compensation preferences.

    Attributes:
        minimum_salary: Lowest acceptable annual salary; ``0`` means no floor.
        currency: ISO 4217 currency code (e.g. ``USD``), or empty if unset.
    """

    # must be >= 0; defaults to 0 (no floor)
    minimum_salary: Annotated[int, Field(ge=0)] = 0
    # defaults to empty (unset); validated/normalized below
    currency: str = ""

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        """Normalize and validate the currency code.

        Trims whitespace and uppercases first, so "usd" or " usd " both
        become "USD" before checking. Empty string is allowed (means
        "unset"). Anything non-empty must match the 3-letter ISO 4217
        pattern, or validation fails.
        """
        value = value.strip().upper()
        if value and not _ISO_4217.match(value):
            raise ValueError(
                "must be a 3-letter ISO 4217 code (e.g. USD, INR, GBP) or empty"
            )
        return value


class ReferralContact(_Base):
    """A person the user already knows at a target company.

    Attributes:
        name: Contact's full name.
        company: Company the contact works at.
        email: Contact email, if known.
    """

    name: NonEmptyStr
    company: NonEmptyStr
    email: EmailStr | None = None  # optional — None if the user doesn't have it


class LlmConfig(_Base):
    """LLM provider selection, passed through to the LiteLLM interface (S0-04).

    Attributes:
        provider: Primary provider LiteLLM routes to.
        model: Provider-specific model identifier.
        fallback_provider: Provider used when the primary errors or times out.
        fallback_model: Model used with ``fallback_provider``.
    """

    provider: LlmProvider
    model: NonEmptyStr
    fallback_provider: LlmProvider | None = None
    fallback_model: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _validate_fallback_pair(self) -> LlmConfig:
        """Require fallback_provider and fallback_model to be set together.

        bool(None) is False and bool("anything") is True, so this check is
        effectively XOR: it only fails when exactly ONE of the two fields is
        set and the other is missing. Both set -> passes. Both unset ->
        passes. One set, one missing -> fails. This is the rule enabling the
        fallback in profile.yaml (uncommenting both lines together).
        """
        if bool(self.fallback_provider) != bool(self.fallback_model):
            raise ValueError(
                "fallback_provider and fallback_model must be set together "
                "(both or neither)"
            )
        return self


class FollowUp(_Base):
    """Follow-up nudge timing windows (FR10).

    Attributes:
        outreach_days: Days to wait after outreach before drafting a follow-up.
        application_with_contact_days: Days to wait after applying to a role
            that has a referral contact before drafting a follow-up.
        expiry_weeks: Weeks after which an unresolved tracked role is expired.
    """

    outreach_days: Annotated[int, Field(gt=0)] = 7
    application_with_contact_days: Annotated[int, Field(gt=0)] = 12
    expiry_weeks: Annotated[int, Field(gt=0)] = 4


class Thresholds(_Base):
    """Scoring and follow-up thresholds.

    Attributes:
        tailoring_score_min: Minimum match score (0-1) that triggers resume
            tailoring; self-adjusts over time once outcome data exists (FR6).
        follow_up: Follow-up timing windows.
    """

    tailoring_score_min: Annotated[float, Field(ge=0.0, le=1.0)] = 0.75
    follow_up: FollowUp = Field(default_factory=FollowUp)  # nested model, own defaults


class Sources(_Base):
    """Which listing sources this instance collects from (FR2, FR3).

    Attributes:
        ats: Enabled ATS platforms.
        aggregators: Enabled aggregator APIs.
        custom_career_pages_config: Path to a custom career-pages YAML file,
            or empty if none are configured.
    """

    ats: list[AtsSource] = Field(default_factory=list)
    aggregators: list[AggregatorSource] = Field(default_factory=list)
    custom_career_pages_config: str = ""


class Notifications(_Base):
    """Daily digest email settings (FR7).

    Attributes:
        digest_email_enabled: Whether the daily nudge email is sent.
        send_time_local: Local send time as ``HH:MM`` (24-hour). Required when
            ``digest_email_enabled`` is true.
        timezone: IANA timezone name (e.g. ``Asia/Kolkata``) that
            ``send_time_local`` is expressed in. Required when
            ``digest_email_enabled`` is true.
    """

    digest_email_enabled: bool = False
    send_time_local: str = ""
    timezone: str = ""

    @model_validator(mode="after")
    def _validate_schedule(self) -> Notifications:
        """Enforce send_time_local and timezone only when digest email is on.

        If digest_email_enabled is False, skip all checks below — the two
        time fields are allowed to stay empty. If it's True: send_time_local
        must match HH:MM, timezone can't be blank, and ZoneInfo(tz) actually
        tries constructing a real timezone object (not just checking string
        shape) — so "Asia/Kolkata" passes but a typo like "Asia/Nowhere"
        fails, which a regex alone couldn't catch.
        """
        if not self.digest_email_enabled:
            return self
        if not _TIME_24H.match(self.send_time_local.strip()):
            raise ValueError(
                "send_time_local must be HH:MM (24-hour) when "
                "digest_email_enabled is true"
            )
        tz = self.timezone.strip()
        if not tz:
            raise ValueError("timezone is required when digest_email_enabled is true")
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"'{tz}' is not a valid IANA timezone name") from exc
        return self


class Dashboard(_Base):
    """Dashboard settings (NFR9).

    Attributes:
        access_control: ``restricted`` (default) or ``public``.
    """

    access_control: Literal["restricted", "public"] = "restricted"


class Partner(_Base):
    """A partner instance to share contacts and skill-gap data with (FR16).

    Attributes:
        name: Short identifier for the partner.
        supabase_url: The partner's Supabase project URL.
        readonly_key_env: Name of the ``.env`` variable holding the partner's
            read-only key (e.g. ``PARTNER_ALEX_SUPABASE_READONLY_KEY``). The
            key value itself never appears in ``profile.yaml``.
    """

    name: NonEmptyStr
    supabase_url: NonEmptyStr
    readonly_key_env: NonEmptyStr


class Profile(_Base):
    """The complete validated profile configuration for one instance.

    This is the top-level model that loader.py validates the parsed YAML
    dict against via Profile.model_validate(data). Each attribute below
    corresponds to one section of profile.yaml; most nested sections (like
    Compensation, LlmConfig, Notifications) are their own _Base subclasses
    defined above.

    Attributes:
        resume_path: Path to the master resume (``.pdf`` or ``.docx``).
        preferred_roles: Non-empty list of target role titles.
        locations: Non-empty list of acceptable locations.
        compensation: Compensation preferences.
        dream_companies: Companies that make a role follow-up eligible (FR10).
        referral_contacts: People the user already knows at target companies.
        email: Profile-level contact email.
        llm: LLM provider selection (pass-through to S0-04).
        thresholds: Scoring and follow-up thresholds.
        sources: Enabled listing sources.
        mode: ``single`` (standalone) or ``shared`` (opt-in shared mode).
        partners: Partner instances; required and non-empty when ``mode`` is
            ``shared``, ignored otherwise.
        notifications: Daily digest email settings.
        dashboard: Dashboard settings.
    """

    resume_path: NonEmptyStr
    # preferred_roles and locations must each be a non-empty list.
    preferred_roles: Annotated[list[NonEmptyStr], Field(min_length=1)]
    locations: Annotated[list[NonEmptyStr], Field(min_length=1)]
    compensation: Compensation = Field(default_factory=Compensation)
    dream_companies: list[NonEmptyStr] = Field(default_factory=list)
    referral_contacts: list[ReferralContact] = Field(default_factory=list)
    email: EmailStr
    llm: LlmConfig
    thresholds: Thresholds = Field(default_factory=Thresholds)
    sources: Sources = Field(default_factory=Sources)
    mode: Literal["single", "shared"] = "single"
    partners: list[Partner] = Field(default_factory=list)
    notifications: Notifications = Field(default_factory=Notifications)
    dashboard: Dashboard = Field(default_factory=Dashboard)

    @field_validator("resume_path")
    @classmethod
    def _validate_resume_suffix(cls, value: str) -> str:
        """Require resume_path to end in .pdf or .docx (case-insensitive).

        Lowercases before checking so .PDF or .DOCX still pass. This only
        checks the extension/shape of the string — it does NOT verify the
        file actually exists on disk, since that's a runtime concern, not
        a config-shape concern that belongs in schema validation.
        """
        if not value.lower().endswith(_RESUME_SUFFIXES):
            raise ValueError(f"must point to a {' or '.join(_RESUME_SUFFIXES)} file")
        return value

    @model_validator(mode="after")
    def _validate_shared_mode(self) -> Profile:
        """Require at least one partner when mode is 'shared'.

        Mirrors FR16 — shared mode only makes sense with at least one
        partner instance configured to share contacts/skill-gap data with.
        """
        if self.mode == "shared" and not self.partners:
            raise ValueError("mode 'shared' requires at least one entry in 'partners'")
        return self
