"""Unit tests for config/loader.py — reading and validating profile.yaml."""

from __future__ import annotations

from pathlib import Path

# dedent strips common leading whitespace from triple-quoted YAML strings.
from textwrap import dedent

import pytest

from config.loader import (
    ProfileNotFoundError,
    ProfileParseError,
    ProfileValidationError,
    load_profile,
)
from config.schema import Profile

# Walk up from this test file's location to the repo root, so we can point
# at the REAL shipped profile.example.yaml (not just synthetic test strings).
REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PATH = REPO_ROOT / "config" / "profile.example.yaml"

# Minimal valid profile (only required fields) — the happy-path baseline
# reused across several tests below.
_VALID_YAML = dedent(
    """
    resume_path: "cv.pdf"
    preferred_roles:
      - "Backend Engineer"
    locations:
      - "Remote"
    email: "me@example.com"
    llm:
      provider: "ollama"
      model: "llama3.1"
    """
).strip()


def _write(tmp_path: Path, text: str) -> Path:
    """Write `text` to a profile.yaml inside pytest's per-test tmp_path.

    tmp_path is a built-in pytest fixture giving each test its own throwaway
    directory, so tests never touch real files or leave artifacts behind.
    """
    path = tmp_path / "profile.yaml"
    path.write_text(text, encoding="utf-8")
    return path


# --- Happy path -----------------------------------------------------------


def test_load_profile__valid_file__returns_validated_profile(tmp_path):
    # Loading a minimal valid file should return a real Profile instance,
    # not a raw dict, with the fields correctly populated.
    path = _write(tmp_path, _VALID_YAML)

    profile = load_profile(path)

    assert isinstance(profile, Profile)
    assert profile.preferred_roles == ["Backend Engineer"]
    assert profile.llm.provider == "ollama"


def test_load_profile__accepts_str_path(tmp_path):
    # load_profile's signature is `str | Path` — confirm a plain string
    # path works too, not just a Path object.
    path = _write(tmp_path, _VALID_YAML)

    assert isinstance(load_profile(str(path)), Profile)


def test_load_profile__example_file_parses_and_validates():
    # The actual shipped profile.example.yaml must pass validation as-is —
    # this is the file new users copy to get started (per SETUP.md).
    profile = load_profile(EXAMPLE_PATH)

    assert isinstance(profile, Profile)
    assert profile.mode == "single"
    assert profile.llm.provider == "anthropic"


# --- Missing file -------------------------------------------------------


def test_load_profile__missing_file__raises_not_found_with_hint(tmp_path):
    # No file written here on purpose — path doesn't exist.
    with pytest.raises(ProfileNotFoundError) as excinfo:
        load_profile(tmp_path / "nope.yaml")

    message = str(excinfo.value)
    assert "profile.example.yaml" in message  # the copy-the-example hint text
    assert "Traceback" not in message  # confirms this is OUR clean message,
    # not a leaked raw Python traceback


# --- Malformed YAML ----------------------------------------------------


def test_load_profile__malformed_yaml__raises_clear_parse_error(tmp_path):
    # Deliberately broken YAML syntax (unclosed bracket).
    path = _write(tmp_path, "preferred_roles: [unclosed\nlocations: ]")

    with pytest.raises(ProfileParseError) as excinfo:
        load_profile(path)

    message = str(excinfo.value)
    assert "is not valid YAML" in message
    assert "line" in message  # proves _yaml_reason's line/column extraction worked
    # Not a raw parser dump.
    assert "\n" not in message.split(": ", 1)[1] or "Traceback" not in message


def test_load_profile__tab_indented_yaml__raises_parse_error(tmp_path):
    # YAML forbids tabs for indentation — a classic gotcha, worth its own
    # dedicated test per TESTING.md's "each edge case is its own test" rule.
    path = _write(tmp_path, "llm:\n\tprovider: ollama\n")

    with pytest.raises(ProfileParseError):
        load_profile(path)


# --- Empty / wrong-shape content -------------------------------------


def test_load_profile__empty_file__raises_validation_error(tmp_path):
    # yaml.safe_load("") returns None — this is the exact case loader.py's
    # `if data is None:` check is meant to catch.
    path = _write(tmp_path, "")

    with pytest.raises(ProfileValidationError, match="empty"):
        load_profile(path)


def test_load_profile__yaml_list_not_mapping__raises_validation_error(tmp_path):
    # Valid YAML, but it parses to a list, not a dict — hits loader.py's
    # `if not isinstance(data, dict):` branch. Covers the OTHER half of the
    # shape check, kept as its own test rather than folded into the one above.
    path = _write(tmp_path, "- one\n- two\n")

    with pytest.raises(ProfileValidationError, match="must be a mapping"):
        load_profile(path)


# --- Schema violations surfaced through the loader -------------------


def test_load_profile__missing_required_field__error_names_field(tmp_path):
    # Valid YAML, valid shape, but missing the required `email` field —
    # tests the full chain: model_validate() fails -> caught by loader.py
    # -> formatted by _format_validation_error() -> names the field and
    # gets singular grammar right ("1 error", not "1 errors").
    path = _write(
        tmp_path,
        dedent(
            """
            resume_path: "cv.pdf"
            preferred_roles:
              - "Backend Engineer"
            locations:
              - "Remote"
            llm:
              provider: "ollama"
              model: "llama3.1"
            """
        ).strip(),
    )

    with pytest.raises(ProfileValidationError) as excinfo:
        load_profile(path)

    message = str(excinfo.value)
    assert "email" in message
    assert "is invalid (1 error)" in message


def test_load_profile__multiple_errors__all_reported(tmp_path):
    # Two separate bad fields at once: wrong resume extension (fails
    # _validate_resume_suffix) AND an empty preferred_roles list (fails
    # min_length=1). Confirms _format_validation_error() reports ALL
    # errors, not just the first one Pydantic happens to hit.
    path = _write(
        tmp_path,
        dedent(
            """
            resume_path: "cv.txt"
            preferred_roles: []
            locations:
              - "Remote"
            email: "me@example.com"
            llm:
              provider: "ollama"
              model: "llama3.1"
            """
        ).strip(),
    )

    with pytest.raises(ProfileValidationError) as excinfo:
        load_profile(path)

    message = str(excinfo.value)
    assert "resume_path" in message
    assert "preferred_roles" in message
    assert "2 errors" in message  # plural grammar, correctly counted
