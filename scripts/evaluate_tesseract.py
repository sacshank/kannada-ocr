"""Run Tesseract on every sample image and score it against the ground truth.

Usage (from the project root):
    PYTHONPATH=backend python scripts/evaluate_tesseract.py --lang kan
    PYTHONPATH=backend python scripts/evaluate_tesseract.py --lang kan+eng
"""

import argparse
import subprocess
from pathlib import Path

from app.metrics import character_error_rate

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DATASET = Path("dataset")


def run_tesseract(image_path: Path, lang: str) -> str:
    """Run the tesseract command and return the text it read."""
    result = subprocess.run(
        ["tesseract", str(image_path), "stdout", "-l", lang],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Tesseract against ground truth.")
    parser.add_argument("--lang", default="kan", help="Tesseract language, e.g. kan or kan+eng")
    args = parser.parse_args()

    images = sorted(
        p for p in (DATASET / "sample_images").iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        print("No images found in dataset/sample_images")
        return

    scores = []
    print(f"Language setting: {args.lang}\n")
    for image in images:
        truth_file = DATASET / "ground_truth" / f"{image.stem}.txt"
        if not truth_file.exists():
            print(f"{image.name}: SKIPPED (no ground truth file {truth_file})")
            continue
        ocr_text = run_tesseract(image, args.lang)
        truth_text = truth_file.read_text(encoding="utf-8")
        cer = character_error_rate(ocr_text, truth_text)
        scores.append(cer)
        print(f"{image.name}: CER = {cer:.3f}")

    if scores:
        print(f"\nAverage CER over {len(scores)} image(s): {sum(scores) / len(scores):.3f}")


if __name__ == "__main__":
    main()
