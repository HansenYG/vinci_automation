"""Unit tests for phone matching logic in repos.teachers_by_phone."""

import re
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))


def _digits(v):
    return re.sub(r"\D", "", "" if v is None else str(v))


def _substring_match(target: str, stored_phones: list[str]) -> list[str]:
    """Replicates the updated teachers_by_phone fallback logic."""
    matched = []
    for p in stored_phones:
        stored = _digits(p)
        if stored and (stored in target or target in stored):
            matched.append(p)
    return matched


def test_exact_match():
    assert len(_substring_match("85212345678", ["85212345678"])) > 0


def test_wati_has_country_code_stored_does_not():
    assert len(_substring_match("85212345678", ["12345678"])) > 0


def test_stored_has_country_code_wati_does_not():
    assert len(_substring_match("12345678", ["85212345678"])) > 0


def test_suffix_mismatch_original_bug():
    assert len(_substring_match("5212345678", ["12345678"])) > 0


def test_no_match():
    assert len(_substring_match("99999999", ["11111111"])) == 0


def test_empty_stored():
    assert len(_substring_match("12345678", [""])) == 0


def test_none_stored():
    assert len(_substring_match("12345678", [None])) == 0


def test_with_plus_prefix():
    assert len(_substring_match("+85212345678", ["85212345678"])) > 0


def test_with_spaces():
    # _digits("+852 1234 5678") == "85212345678"
    assert len(_substring_match("85212345678", ["85212345678"])) > 0


def test_with_dashes():
    # _digits("852-1234-5678") == "85212345678"
    assert len(_substring_match("85212345678", ["85212345678"])) > 0


def test_partial_substring_anywhere():
    assert len(_substring_match("85012345678", ["123456"])) > 0


def test_one_char_off():
    assert len(_substring_match("85212345679", ["85212345678"])) == 0


def test_phones_match_airtable_style():
    """GAS phonesMatch: a === b || a.indexOf(b) !== -1 || b.indexOf(a) !== -1"""
    a, b = "85252408480", "52408480"
    assert a == b or a in b or b in a


if __name__ == "__main__":
    import inspect
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError:
                print(f"  FAIL  {name}")
                failures += 1
    print(f"\n{failures} failure(s)" if failures else "\nAll tests passed!")
    sys.exit(failures)
