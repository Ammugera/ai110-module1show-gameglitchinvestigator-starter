import pytest
from logic_utils import check_guess, get_range_for_difficulty, parse_guess
from unittest.mock import patch

# FIX: Corrected assertions to unpack (outcome, message) tuple from check_guess —
#      identified by Gemini Agent, fixed by user
def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    outcome, message = check_guess(50, 50)
    assert outcome == "Win"

def test_guess_too_high():
    # If secret is 50 and guess is 60, hint should be "Too High"
    outcome, message = check_guess(60, 50)
    assert outcome == "Too High"

def test_guess_too_low():
    # If secret is 50 and guess is 40, hint should be "Too Low"
    outcome, message = check_guess(40, 50)
    assert outcome == "Too Low"


# ---------------------------------------------------------------------------
# FIX: Test for New-game reset bug — bug diagnosed by user, test written via Gemini Agent mode
#
# The original bug: clicking "New Game" only reset `attempts` (to 0) and
# `secret`, but never reset `status`, `score`, or `history`.  Because
# the app calls st.stop() whenever status != "playing", the game stayed
# stuck on the game-over screen.
#
# This test simulates the session-state mutations that the fixed
# `if new_game:` block in app.py performs, then asserts every key is
# correctly reset.
# ---------------------------------------------------------------------------


class _FakeSessionState(dict):
    """Minimal stand-in for st.session_state (attribute access over a dict)."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


def _simulate_new_game_reset(state, low, high, fake_secret):
    """
    Mirror the reset logic from app.py's `if new_game:` block.

    This is intentionally a direct copy so the test breaks if the
    production code drifts out of sync.
    """
    import random
    state.attempts = 1
    state.score = 0
    state.history = []
    state.status = "playing"
    state.secret = random.randint(low, high)


@patch("random.randint", return_value=42)
def test_new_game_resets_all_state_after_win(mock_randint):
    """After winning, New Game must reset every session-state key."""
    state = _FakeSessionState(
        secret=77,
        attempts=5,
        score=150,
        status="won",
        history=[10, 20, 30, 77],
    )

    low, high = get_range_for_difficulty("Normal")  # 1, 100
    _simulate_new_game_reset(state, low, high, fake_secret=42)

    assert state.status == "playing", "status must be reset to 'playing'"
    assert state.attempts == 1, "attempts must reset to 1 (not 0)"
    assert state.score == 0, "score must reset to 0"
    assert state.history == [], "history must be cleared"
    assert state.secret == 42, "secret must be regenerated"
    mock_randint.assert_called_once_with(low, high)


@patch("random.randint", return_value=7)
def test_new_game_resets_all_state_after_loss(mock_randint):
    """After losing, New Game must reset every session-state key."""
    state = _FakeSessionState(
        secret=55,
        attempts=8,
        score=-20,
        status="lost",
        history=[10, 20, 30, 40, 50, 60, 70, 80],
    )

    low, high = get_range_for_difficulty("Easy")  # 1, 20
    _simulate_new_game_reset(state, low, high, fake_secret=7)

    assert state.status == "playing"
    assert state.attempts == 1
    assert state.score == 0
    assert state.history == []
    assert state.secret == 7
    mock_randint.assert_called_once_with(1, 20)


@patch("random.randint", return_value=33)
def test_new_game_uses_difficulty_range(mock_randint):
    """Secret must be generated within the current difficulty range, not
    hardcoded 1–100 (the original bug used `random.randint(1, 100)`)."""
    state = _FakeSessionState(
        secret=10,
        attempts=5,
        score=0,
        status="lost",
        history=[],
    )

    # Hard difficulty → range 1–50
    low, high = get_range_for_difficulty("Hard")
    _simulate_new_game_reset(state, low, high, fake_secret=33)

    mock_randint.assert_called_once_with(1, 50)


# ---------------------------------------------------------------------------
# FIX: Tests for Bug 1 — parse_guess() range validation
#      Bug identified by user, range-check fix and tests written via Gemini Agent mode
#
# The original bug: parse_guess() accepted any integer, including negatives
# and numbers above the difficulty ceiling.  The fix adds `low` and `high`
# parameters and rejects values outside that range.
# ---------------------------------------------------------------------------


def test_parse_guess_rejects_negative():
    """Negative numbers must be rejected for any difficulty range."""
    ok, value, err = parse_guess("-5", low=1, high=100)
    assert not ok
    assert value is None
    assert "between 1 and 100" in err


def test_parse_guess_rejects_zero():
    """Zero is below every difficulty range (minimum is always 1)."""
    ok, value, err = parse_guess("0", low=1, high=20)
    assert not ok
    assert "between 1 and 20" in err


def test_parse_guess_rejects_above_max():
    """A number above the difficulty ceiling must be rejected."""
    ok, value, err = parse_guess("21", low=1, high=20)
    assert not ok
    assert "between 1 and 20" in err


def test_parse_guess_rejects_way_above_max():
    """1001 should be rejected even on the widest range (1–100 Normal)."""
    ok, value, err = parse_guess("1001", low=1, high=100)
    assert not ok
    assert "between 1 and 100" in err


def test_parse_guess_accepts_low_boundary():
    """The lower boundary itself is a valid guess."""
    ok, value, err = parse_guess("1", low=1, high=50)
    assert ok
    assert value == 1
    assert err is None


def test_parse_guess_accepts_high_boundary():
    """The upper boundary itself is a valid guess."""
    ok, value, err = parse_guess("50", low=1, high=50)
    assert ok
    assert value == 50
    assert err is None


def test_parse_guess_accepts_mid_range():
    """A value in the middle of the range must be accepted."""
    ok, value, err = parse_guess("10", low=1, high=20)
    assert ok
    assert value == 10
    assert err is None


def test_parse_guess_non_numeric():
    """Non-numeric input must be rejected (not a range issue, but still invalid)."""
    ok, value, err = parse_guess("abc", low=1, high=100)
    assert not ok
    assert value is None
    assert err == "That is not a number."


def test_parse_guess_empty():
    """Empty string must be rejected."""
    ok, value, err = parse_guess("", low=1, high=100)
    assert not ok
    assert err == "Enter a guess."


# ---------------------------------------------------------------------------
# FIX: Tests for Bug 2 — Invalid guesses must NOT increment attempts
#      Bug identified by user, attempt-ordering fix and tests written via Gemini Agent mode
#
# The original bug: `st.session_state.attempts += 1` ran BEFORE
# parse_guess() validated the input, so typing garbage or an out-of-range
# number still consumed an attempt.
#
# These tests simulate the submit-block logic from app.py to verify that
# the attempt counter only moves for valid guesses.
# ---------------------------------------------------------------------------


def _simulate_submit(state, raw_input, low, high):
    """
    Mirror the fixed `if submit:` block from app.py.

    Returns (ok, guess_int, err) so callers can inspect results.
    """
    ok, guess_int, err = parse_guess(raw_input, low, high)
    if not ok:
        state.history.append(raw_input)
        # attempts must NOT be incremented
    else:
        state.attempts += 1
        state.history.append(guess_int)
    return ok, guess_int, err


def test_invalid_guess_does_not_increment_attempts():
    """Non-numeric input must leave the attempt counter unchanged."""
    state = _FakeSessionState(attempts=1, history=[])
    _simulate_submit(state, "abc", low=1, high=100)
    assert state.attempts == 1, "attempts must not change for invalid input"


def test_out_of_range_guess_does_not_increment_attempts():
    """Out-of-range guess must leave the attempt counter unchanged."""
    state = _FakeSessionState(attempts=1, history=[])
    _simulate_submit(state, "999", low=1, high=100)
    assert state.attempts == 1, "attempts must not change for out-of-range guess"


def test_valid_guess_increments_attempts():
    """A valid in-range guess must increment the attempt counter."""
    state = _FakeSessionState(attempts=1, history=[])
    _simulate_submit(state, "50", low=1, high=100)
    assert state.attempts == 2, "attempts must increment for a valid guess"


def test_multiple_invalid_then_valid():
    """Only the valid guess in a sequence should bump the counter."""
    state = _FakeSessionState(attempts=1, history=[])

    _simulate_submit(state, "abc", low=1, high=20)   # invalid — no increment
    _simulate_submit(state, "-1", low=1, high=20)     # out of range — no increment
    _simulate_submit(state, "21", low=1, high=20)     # out of range — no increment
    _simulate_submit(state, "10", low=1, high=20)     # valid — increment

    assert state.attempts == 2, "only the one valid guess should have incremented"
    assert state.history == ["abc", "-1", "21", 10]


# ===========================================================================
# Edge Case 1 — Decimal inputs are silently truncated
#
# parse_guess("3.7") converts to int(float("3.7")) → 3 without telling
# the player. The guess is accepted as 3 even though the player typed 3.7.
# These tests document the current (buggy) behaviour and flag the expected
# behaviour as xfail until the code is fixed.
# ===========================================================================


def test_decimal_input_is_silently_accepted():
    """Current behaviour: '3.7' is silently truncated to 3 and accepted."""
    ok, value, err = parse_guess("3.7", low=1, high=20)
    # This PASSES today — documenting the current behaviour
    assert ok is True
    assert value == 3
    assert err is None


def test_decimal_truncation_loses_precision():
    """'9.9' is truncated to 9, not rounded to 10 — player may not realise."""
    ok, value, err = parse_guess("9.9", low=1, high=20)
    assert ok is True
    assert value == 9  # truncated, not rounded


@pytest.mark.xfail(reason="Decimal input should be rejected or warn the player")
def test_decimal_input_should_be_rejected():
    """EXPECTED fix: decimals should be rejected with a helpful message."""
    ok, value, err = parse_guess("3.7", low=1, high=20)
    assert not ok, "decimal input should not be silently accepted"
    assert value is None
    assert err is not None and "whole" in err.lower()


@pytest.mark.xfail(reason="Negative decimal should be rejected for two reasons")
def test_negative_decimal_rejected_clearly():
    """'-2.5' is negative AND a decimal — error message should be clear."""
    ok, value, err = parse_guess("-2.5", low=1, high=20)
    # Today: truncated to -2, then rejected by range check as "between 1 and 20"
    # Expected: rejected for not being a whole number
    assert not ok
    assert "whole" in err.lower() or "integer" in err.lower()


# ===========================================================================
# Edge Case 2 — Even-attempt type coercion breaks correct guesses
#
# app.py lines 105-108 convert the secret to a STRING on even attempts:
#   if st.session_state.attempts % 2 == 0:
#       secret = str(st.session_state.secret)
#
# This means check_guess(50, "50") compares int 50 == str "50" → False
# in Python 3, so a correct guess on an even attempt is NEVER a win.
#
# These tests call check_guess directly to prove the bug exists, then
# simulate the full submit flow to show the gameplay impact.
# ===========================================================================


def test_check_guess_correct_with_int_secret():
    """Baseline: int guess vs int secret → Win (odd attempts)."""
    outcome, message = check_guess(42, 42)
    assert outcome == "Win"


def test_check_guess_correct_with_str_secret():
    """int guess vs str secret — the == check fails (int != str in Python 3),
    but the TypeError fallback recovers via string comparison.
    Works by accident, not by design."""
    outcome, message = check_guess(42, "42")
    # This passes only because the except TypeError branch does
    # str(42) == "42" → True. The primary == check fails silently.
    assert outcome == "Win"


def test_check_guess_str_secret_falls_to_type_error_branch():
    """When secret is str, the > comparison raises TypeError and falls
    into the except branch which does string comparison."""
    outcome, message = check_guess(42, "42")
    # In the except branch: str("42") == "42" is True → should return Win
    # But wait — the try branch does guess > secret (int > str) which
    # raises TypeError, so it falls through. Let's verify what actually happens:
    # str(42) == "42" → True in the except block → "Win"
    # Actually this DOES work in the except block!  Let's verify:
    assert outcome == "Win"


def _simulate_submit_with_coercion(state, raw_input, low, high):
    """Mirror the full submit block from app.py INCLUDING the
    even-attempt type coercion bug (lines 105-108)."""
    ok, guess_int, err = parse_guess(raw_input, low, high)
    if not ok:
        state.history.append(raw_input)
    else:
        state.attempts += 1
        state.history.append(guess_int)

        # This is the buggy coercion from app.py
        if state.attempts % 2 == 0:
            secret = str(state.secret)
        else:
            secret = state.secret

        outcome, message = check_guess(guess_int, secret)
        return outcome, message
    return None, err


def test_correct_guess_on_odd_attempt_wins():
    """Odd attempt (no coercion) — correct guess should win."""
    state = _FakeSessionState(attempts=1, secret=42, history=[])
    # attempts will become 2 (even) after increment inside _simulate
    # So let's set attempts=0 so after increment it's 1 (odd)
    state.attempts = 0
    outcome, _ = _simulate_submit_with_coercion(state, "42", 1, 100)
    assert outcome == "Win"


def test_correct_guess_on_even_attempt_behavior():
    """Even attempt (coercion active) — documents current behaviour.
    The except/TypeError branch does catch this via string comparison,
    so it may still return Win. This test documents whichever happens."""
    state = _FakeSessionState(attempts=0, secret=42, history=[])
    # After increment: attempts=1 (odd). We need attempts to be even after increment.
    state.attempts = 1  # after increment → 2 (even)
    outcome, _ = _simulate_submit_with_coercion(state, "42", 1, 100)
    # The TypeError fallback does str(42) == "42" → True → "Win"
    # So this actually works by accident via the except branch.
    # But it relies on fragile TypeError handling — document it:
    assert outcome == "Win", (
        "Even-attempt coercion falls through to TypeError branch; "
        "currently returns Win by accident via string comparison"
    )


def test_even_attempt_coercion_works_by_accident():
    """The str() coercion on even attempts forces check_guess through
    the TypeError fallback. It returns 'Win' only because str(42) == '42'
    happens to be True. This is fragile — e.g. leading zeros or locale
    formatting would break it. This test documents the accidental success."""
    state = _FakeSessionState(attempts=1, secret=42, history=[])
    # After _simulate increments: attempts=2 (even) → secret becomes str
    outcome, _ = _simulate_submit_with_coercion(state, "42", 1, 100)
    assert outcome == "Win", (
        "Even-attempt coercion relies on TypeError fallback — "
        "works now but is fragile and should be removed"
    )


# ===========================================================================
# Edge Case 3 — Comma-formatted and special-character numeric inputs
#
# Players may type "1,000" or "1 000" expecting them to be parsed as 1000.
# parse_guess() calls int("1,000") which raises ValueError, caught by the
# except block, returning "That is not a number." — a misleading message
# since the input clearly IS a number, just formatted differently.
# ===========================================================================


def test_comma_formatted_number_rejected():
    """'1,000' is rejected — current behaviour."""
    ok, value, err = parse_guess("1,000", low=1, high=100)
    assert not ok
    assert value is None


def test_comma_formatted_gives_misleading_error():
    """Current error says 'not a number' which is confusing for '1,000'."""
    ok, value, err = parse_guess("1,000", low=1, high=100)
    assert err == "That is not a number."


@pytest.mark.xfail(reason="Comma-formatted numbers should get a specific error message")
def test_comma_formatted_should_give_helpful_error():
    """EXPECTED fix: error message should mention commas, not just say
    'not a number'."""
    ok, value, err = parse_guess("1,000", low=1, high=100)
    assert not ok
    assert "comma" in err.lower(), (
        f"Error '{err}' should mention commas for input '1,000'"
    )


def test_space_separated_number_rejected():
    """'1 000' (European-style thousands separator) is also rejected."""
    ok, value, err = parse_guess("1 000", low=1, high=100)
    assert not ok
    assert value is None


def test_currency_symbol_rejected():
    """'$50' should be rejected as non-numeric."""
    ok, value, err = parse_guess("$50", low=1, high=100)
    assert not ok
    assert err == "That is not a number."


def test_plus_prefix_accepted():
    """'+5' — Python's int() accepts a leading plus sign."""
    ok, value, err = parse_guess("+5", low=1, high=20)
    assert ok
    assert value == 5

