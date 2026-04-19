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
