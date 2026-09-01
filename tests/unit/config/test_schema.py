"""Unit tests for config/schema.py — the profile configuration schema."""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from config.schema import Profile


def _valid_profile_dict() -> dict:
    """A complete, correct profile as a plain dict (fresh copy each call).

    deepcopy matters here: dicts/lists are mutable, so if every test just
    reused the SAME dict object, one test mutating a nested field (e.g.
    data["compensation"]["currency"] = "dollars") could leak into other
    tests that run after it. Returning a fresh deep copy each call keeps
    every test's edits fully isolated.
    """
    return copy.deepcopy(
        {
            "resume_path": "resume_generation/master_resume.pdf",
            "preferred_roles": ["Senior Software Engineer", "Backend Engineer"],
            "locations": ["Remote", "Bengaluru, India"],
            "compensation": {"minimum_salary": 120000, "currency": "USD"},
            "dream_companies": ["Stripe"],
            "referral_contacts": [
                {"name": "Alex Rivera", "company": "Stripe", "email": "a@example.com"},
                # second contact has no email — the field is optional
                {"name": "Priya Menon", "company": "Linear"},
            ],
            "email": "you@example.com",
            "llm": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
            "thresholds": {
                "tailoring_score_min": 0.8,
                "follow_up": {
                    "outreach_days": 7,
                    "application_with_contact_days": 12,
                    "expiry_weeks": 4,
                },
            },
            "sources": {
                "ats": ["greenhouse", "lever"],
                "aggregators": ["remoteok"],
                "custom_career_pages_config": "config/custom_pages.yaml",
            },
            "mode": "single",
            "partners": [],
            "notifications": {
                "digest_email_enabled": True,
                "send_time_local": "08:00",
                "timezone": "Asia/Kolkata",
            },
            "dashboard": {"access_control": "restricted"},
        }
    )


# --- Happy path -----------------------------------------------------------


def test_profile__complete_correct_config__validates_without_error():
    # Every field populated with valid data should validate cleanly and
    # land on the model exactly as given.
    profile = Profile.model_validate(_valid_profile_dict())

    assert profile.resume_path == "resume_generation/master_resume.pdf"
    assert profile.preferred_roles == ["Senior Software Engineer", "Backend Engineer"]
    assert profile.compensation.currency == "USD"
    assert profile.llm.provider == "anthropic"
    # confirms the optional email field defaults to None
    assert profile.referral_contacts[1].email is None


def test_profile__only_required_fields__fills_defaults():
    # Only the required fields, nothing else — confirms every
    # Field(default_factory=...) / bare default actually applies when
    # the corresponding section is omitted entirely from the input.
    minimal = {
        "resume_path": "cv.docx",
        "preferred_roles": ["Data Engineer"],
        "locations": ["Remote"],
        "email": "me@example.com",
        "llm": {"provider": "ollama", "model": "llama3.1"},
    }

    profile = Profile.model_validate(minimal)

    assert profile.compensation.minimum_salary == 0
    assert profile.thresholds.tailoring_score_min == 0.75
    assert profile.thresholds.follow_up.outreach_days == 7
    assert profile.sources.ats == []
    assert profile.mode == "single"
    assert profile.dashboard.access_control == "restricted"
    assert profile.notifications.digest_email_enabled is False


# --- Missing required fields -------------------------------------------


@pytest.mark.parametrize(
    "field", ["resume_path", "preferred_roles", "locations", "email", "llm"]
)
def test_profile__missing_required_field__error_names_the_field(field):
    # One test function, run 5 times (once per field name) via
    # parametrize — deletes a different required top-level field each run
    # and confirms validation fails AND the error correctly names that
    # exact field. Avoids writing 5 near-identical test functions.
    data = _valid_profile_dict()
    del data[field]

    with pytest.raises(ValidationError) as excinfo:
        Profile.model_validate(data)

    errors = excinfo.value.errors()
    assert any(err["loc"] == (field,) for err in errors)
    assert field in str(excinfo.value)


def test_profile__missing_nested_required_field__error_names_the_path():
    # Same idea as above, but one level deeper — confirms the dotted
    # loc path (e.g. ("llm", "model")) still resolves correctly for a
    # field nested inside a sub-model, not just top-level fields.
    data = _valid_profile_dict()
    del data["llm"]["model"]

    with pytest.raises(ValidationError) as excinfo:
        Profile.model_validate(data)

    assert any(err["loc"] == ("llm", "model") for err in excinfo.value.errors())


# --- Type / value rejection -------------------------------------------
# Each test below checks ONE field's own constraint in isolation — these
# are NOT cross-field rules (see the cross-field section further down).


def test_profile__empty_preferred_roles__rejected():
    # preferred_roles requires Field(min_length=1) — an empty list must fail.
    data = _valid_profile_dict()
    data["preferred_roles"] = []

    with pytest.raises(ValidationError, match="preferred_roles"):
        Profile.model_validate(data)


def test_profile__blank_role_string__rejected():
    # NonEmptyStr requires at least one non-whitespace character — a
    # string that's only spaces must still fail even though it's non-empty
    # in the literal sense.
    data = _valid_profile_dict()
    data["preferred_roles"] = ["Backend Engineer", "   "]

    with pytest.raises(ValidationError):
        Profile.model_validate(data)


def test_profile__resume_path_wrong_extension__rejected():
    # Exercises _validate_resume_suffix — only .pdf/.docx are allowed.
    data = _valid_profile_dict()
    data["resume_path"] = "resume.txt"

    with pytest.raises(ValidationError, match="pdf or .docx"):
        Profile.model_validate(data)


def test_profile__non_iso_currency__rejected():
    # Exercises _validate_currency's reject path — must match the
    # 3-letter ISO 4217 pattern.
    data = _valid_profile_dict()
    data["compensation"]["currency"] = "dollars"

    with pytest.raises(ValidationError, match="ISO 4217"):
        Profile.model_validate(data)


def test_profile__blank_currency__accepted():
    # Exercises _validate_currency's ACCEPT path — empty string means
    # "unset" and is explicitly allowed, not just "not yet rejected".
    data = _valid_profile_dict()
    data["compensation"]["currency"] = ""

    assert Profile.model_validate(data).compensation.currency == ""


def test_profile__negative_minimum_salary__rejected():
    # minimum_salary requires Field(ge=0) — negative values must fail.
    data = _valid_profile_dict()
    data["compensation"]["minimum_salary"] = -1

    with pytest.raises(ValidationError):
        Profile.model_validate(data)


def test_profile__unknown_llm_provider__rejected():
    # provider is a Literal["anthropic", "openai", "ollama"] — anything
    # outside that exact set must fail, proving the enum restriction works.
    data = _valid_profile_dict()
    data["llm"]["provider"] = "cohere"

    with pytest.raises(ValidationError, match="provider"):
        Profile.model_validate(data)


def test_profile__invalid_ats_source__rejected():
    # ats is list[AtsSource], AtsSource being a Literal of exactly three
    # names — "workday" isn't one of them (it's an autofill-only platform
    # per FR9, not a listing source), so it must be rejected.
    data = _valid_profile_dict()
    data["sources"]["ats"] = ["greenhouse", "workday"]

    with pytest.raises(ValidationError):
        Profile.model_validate(data)


def test_profile__tailoring_score_out_of_range__rejected():
    # tailoring_score_min requires Field(ge=0.0, le=1.0) — 1.5 is out of range.
    data = _valid_profile_dict()
    data["thresholds"]["tailoring_score_min"] = 1.5

    with pytest.raises(ValidationError):
        Profile.model_validate(data)


def test_profile__zero_follow_up_window__rejected():
    # expiry_weeks requires Field(gt=0) — zero must fail (gt, not ge).
    data = _valid_profile_dict()
    data["thresholds"]["follow_up"]["expiry_weeks"] = 0

    with pytest.raises(ValidationError):
        Profile.model_validate(data)


def test_profile__referral_contact_bad_email__rejected():
    # email uses Pydantic's built-in EmailStr type — confirms it actually
    # rejects a string that isn't email-shaped.
    data = _valid_profile_dict()
    data["referral_contacts"][0]["email"] = "not-an-email"

    with pytest.raises(ValidationError, match="email"):
        Profile.model_validate(data)


def test_profile__unknown_top_level_key__rejected():
    # Proves extra="forbid" (set once on _Base, inherited everywhere)
    # actually fires — an unrecognized key must be rejected and named.
    data = _valid_profile_dict()
    data["favourite_colour"] = "blue"

    with pytest.raises(ValidationError, match="favourite_colour"):
        Profile.model_validate(data)


# --- Cross-field rules ------------------------------------------------
# Each test below depends on TWO fields together — neither field's own
# type/constraint alone can express the rule; it only exists in the
# relationship between them. These exercise the three @model_validator
# methods (_validate_fallback_pair, _validate_schedule, _validate_shared_mode).


def test_profile__fallback_provider_without_model__rejected():
    # _validate_fallback_pair: fallback_provider and fallback_model must be
    # set together — one without the other is invalid regardless of the
    # value itself.
    data = _valid_profile_dict()
    data["llm"]["fallback_provider"] = "ollama"

    with pytest.raises(ValidationError, match="set together"):
        Profile.model_validate(data)


def test_profile__both_fallback_fields__accepted():
    # The accept side of the same fallback-pair rule: both set together
    # should validate fine.
    data = _valid_profile_dict()
    data["llm"]["fallback_provider"] = "ollama"
    data["llm"]["fallback_model"] = "llama3.1"

    profile = Profile.model_validate(data)
    assert profile.llm.fallback_provider == "ollama"


def test_profile__digest_enabled_without_send_time__rejected():
    # send_time_local being empty is only a problem BECAUSE
    # digest_email_enabled is True elsewhere in the same object.
    data = _valid_profile_dict()
    data["notifications"]["send_time_local"] = ""

    with pytest.raises(ValidationError, match="send_time_local"):
        Profile.model_validate(data)


def test_profile__digest_enabled_bad_send_time__rejected():
    # Malformed time string (25:00 isn't a valid 24-hour time) — only
    # checked at all because digest_email_enabled is True.
    data = _valid_profile_dict()
    data["notifications"]["send_time_local"] = "25:00"

    with pytest.raises(ValidationError, match="HH:MM"):
        Profile.model_validate(data)


def test_profile__digest_enabled_bad_timezone__rejected():
    # Not a real IANA timezone name — proves ZoneInfo() is actually being
    # used to validate (not just a regex/string-shape check).
    data = _valid_profile_dict()
    data["notifications"]["timezone"] = "Mars/Olympus_Mons"

    with pytest.raises(ValidationError, match="IANA timezone"):
        Profile.model_validate(data)


def test_profile__digest_disabled__schedule_fields_optional():
    # The other side of the same rule: when digest_email_enabled is
    # False, send_time_local/timezone are allowed to be missing/empty —
    # confirms the "if not enabled, skip checks" branch in _validate_schedule.
    data = _valid_profile_dict()
    data["notifications"] = {"digest_email_enabled": False}

    profile = Profile.model_validate(data)
    assert profile.notifications.send_time_local == ""


def test_profile__shared_mode_without_partners__rejected():
    # partners being empty is only a problem BECAUSE mode == "shared".
    # The same empty list would be fine under mode == "single".
    data = _valid_profile_dict()
    data["mode"] = "shared"
    data["partners"] = []

    with pytest.raises(ValidationError, match="partners"):
        Profile.model_validate(data)


def test_profile__shared_mode_with_partner__accepted():
    # The accept side: mode == "shared" WITH at least one partner
    # configured should validate fine.
    data = _valid_profile_dict()
    data["mode"] = "shared"
    data["partners"] = [
        {
            "name": "alex",
            "supabase_url": "https://alex.supabase.co",
            "readonly_key_env": "PARTNER_ALEX_SUPABASE_READONLY_KEY",
        }
    ]

    profile = Profile.model_validate(data)
    assert profile.partners[0].name == "alex"
