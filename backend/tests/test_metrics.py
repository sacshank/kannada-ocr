from app.metrics import character_error_rate, edit_distance, normalize_text


def test_edit_distance_identical():
    assert edit_distance("abc", "abc") == 0


def test_edit_distance_one_substitution():
    assert edit_distance("cat", "cut") == 1


def test_edit_distance_insert_and_delete():
    assert edit_distance("abc", "abcd") == 1
    assert edit_distance("abcd", "abc") == 1


def test_normalize_ignores_blank_lines_and_extra_spaces():
    assert normalize_text("a  b\n\n  c  \n") == "a b\nc"


def test_cer_perfect_match_is_zero():
    assert character_error_rate("ಕನಕದಾಸ", "ಕನಕದಾಸ") == 0.0


def test_cer_counts_errors():
    # 1 wrong character out of 4 -> 0.25
    assert character_error_rate("abXd", "abcd") == 0.25


def test_cer_empty_truth():
    assert character_error_rate("", "") == 0.0
    assert character_error_rate("x", "") == 1.0
