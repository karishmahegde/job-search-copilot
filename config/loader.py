"""Read `config/profile.yaml` from disk and return a validated `Profile`.

Turns the three failure modes a clone will actually hit — missing file,
malformed YAML, schema-invalid content — into clear, actionable errors
instead of raw tracebacks.
"""

# Lets `str | Path` union syntax work safely across Python versions.
from __future__ import annotations

from pathlib import Path

# yaml parses YAML text into Python dicts/lists/etc.
import yaml

# ValidationError is raised when data doesn't match a Pydantic model's schema.
from pydantic import ValidationError

# Profile is our own Pydantic model defining the full profile.yaml shape.
from config.schema import Profile

DEFAULT_PROFILE_PATH = Path("config/profile.yaml")


class ProfileError(Exception):
    """Base class for any failure loading the profile configuration.

    Umbrella type — lets calling code catch "any profile load failure" in a
    single ``except`` clause.
    """


class ProfileNotFoundError(ProfileError):
    """Raised when the profile file does not exist."""


class ProfileParseError(ProfileError):
    """Raised when the profile file is not well-formed YAML."""


class ProfileValidationError(ProfileError):
    """Raised when the profile parses as YAML but violates the schema."""


def load_profile(path: str | Path = DEFAULT_PROFILE_PATH) -> Profile:
    """Load and validate a profile configuration file.

    Args:
        path: Path to the profile YAML file. Defaults to
            ``config/profile.yaml``.

    Returns:
        The validated :class:`~config.schema.Profile`.

    Raises:
        ProfileNotFoundError: If no file exists at ``path``.
        ProfileParseError: If the file is not valid YAML.
        ProfileValidationError: If the file is empty, is not a mapping, or
            fails schema validation. The message names each offending field.
    """
    # Normalize str input to a Path object either way.
    profile_path = Path(path)

    # --- Step 1: does the file exist and can we read it? ---
    try:
        raw = profile_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        # `from exc` preserves the original traceback as the cause.
        raise ProfileNotFoundError(
            f"Profile config not found at '{profile_path}'. Copy "
            "'config/profile.example.yaml' to that path and fill it in."
        ) from exc

    # --- Step 2: is the file valid YAML syntax? ---
    try:
        # safe_load refuses to construct arbitrary objects embedded in YAML.
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ProfileParseError(
            f"Profile config at '{profile_path}' is not valid YAML: {_yaml_reason(exc)}"
        ) from exc

    # --- Step 3: is the parsed result the right basic shape? ---
    if data is None:
        raise ProfileValidationError(f"Profile config at '{profile_path}' is empty.")
    if not isinstance(data, dict):
        raise ProfileValidationError(
            f"Profile config at '{profile_path}' must be a mapping of fields, "
            f"got {type(data).__name__}."
        )

    # --- Step 4: does the content match the Profile schema? ---
    try:
        # Returns a real typed Profile object, not a raw dict.
        return Profile.model_validate(data)
    except ValidationError as exc:
        raise ProfileValidationError(
            _format_validation_error(profile_path, exc)
        ) from exc


def _yaml_reason(exc: yaml.YAMLError) -> str:
    """Render a PyYAML error as a one-line, human-readable reason."""
    # PyYAML errors sometimes carry these two extra attributes with precise
    # location info; getattr falls back to None for exception types without them.
    mark = getattr(exc, "problem_mark", None)
    problem = getattr(exc, "problem", None)

    if problem and mark is not None:
        # Best case: a precise one-liner. +1 because PyYAML's line/column are
        # 0-indexed but humans count from 1.
        return f"{problem} (line {mark.line + 1}, column {mark.column + 1})"

    # Fallback: PyYAML's default str(exc) is often multi-line — collapse all
    # whitespace (newlines included) to single spaces so it prints as one line.
    return " ".join(str(exc).split())


def _format_validation_error(path: Path, exc: ValidationError) -> str:
    """Render a Pydantic ValidationError as a field-by-field message."""
    # A single ValidationError can hold multiple problems at once.
    errors = exc.errors()

    # err['loc'] is a tuple like ("compensation", "currency") giving the field
    # path; join with dots, or fall back to "(root)" when the error has no path.
    lines = [
        f"  - {'.'.join(str(part) for part in err['loc']) or '(root)'}: {err['msg']}"
        for err in errors
    ]

    count = len(errors)
    # Correct singular/plural grammar in the header.
    header = (
        f"Profile config at '{path}' is invalid "
        f"({count} error{'' if count == 1 else 's'}):"
    )

    # Header first, then every error line — the user sees ALL problems in one
    # pass, not just the first one Pydantic happened to hit.
    return "\n".join([header, *lines])
