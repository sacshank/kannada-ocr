"""Run Arjuna-OCR on every sample image and score it against the ground truth.

Usage (from the project root, with the virtual environment active):
    PYTHONPATH=backend python scripts/evaluate_arjuna.py
"""

import time
from pathlib import Path

from app.metrics import character_error_rate

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DATASET = Path("dataset")


def main() -> None:
    from kanen_infer import KanEnOCR  # import name from the Arjuna model card

    images = sorted(
        p for p in (DATASET / "sample_images").iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        print("No images found in dataset/sample_images")
        return

    start = time.perf_counter()
    ocr = KanEnOCR()
    print(f"Model load time: {time.perf_counter() - start:.1f}s\n")

    scores = []
    for image in images:
        truth_file = DATASET / "ground_truth" / f"{image.stem}.txt"
        if not truth_file.exists():
            print(f"{image.name}: SKIPPED (no ground truth file {truth_file})")
            continue

        start = time.perf_counter()
        doc = ocr.page(str(image))
        ocr_text = doc.get("text") if isinstance(doc, dict) else None
        if ocr_text is None:
            ocr_text = ocr.render(doc, "txt")
        seconds = time.perf_counter() - start

        truth_text = truth_file.read_text(encoding="utf-8")
        cer = character_error_rate(ocr_text, truth_text)
        scores.append(cer)
        print(f"{image.name}: CER = {cer:.3f} ({seconds:.1f}s)")

    if scores:
        print(f"\nAverage CER over {len(scores)} image(s): {sum(scores) / len(scores):.3f}")


if __name__ == "__main__":
    main()