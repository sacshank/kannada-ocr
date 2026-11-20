"""Accuracy metrics for comparing OCR output with ground truth."""

import unicodedata


def normalize_text(text: str) -> str:
    """Make two texts comparable: fix Unicode form, drop blank lines and extra spaces."""
    text = unicodedata.normalize("NFC", text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def edit_distance(a: str, b: str) -> int:
    """Minimum number of single-character edits needed to turn a into b."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            cost = 0 if char_a == char_b else 1
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            )
        previous = current
    return previous[-1]


def character_error_rate(ocr_text: str, truth_text: str) -> float:
    """Edit distance divided by the ground truth length (0.0 means perfect)."""
    ocr = normalize_text(ocr_text)
    truth = normalize_text(truth_text)
    if not truth:
        return 0.0 if not ocr else 1.0
    return edit_distance(ocr, truth) / len(truth)
