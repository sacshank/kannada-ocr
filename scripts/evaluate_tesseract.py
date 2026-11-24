"""Run Tesseract on every sample image and score it against the ground truth.

Usage (from the project root):
    PYTHONPATH=backend python scripts/evaluate_tesseract.py --lang kan
    PYTHONPATH=backend python scripts/evaluate_tesseract.py --lang kan+eng
    PYTHONPATH=backend python scripts/evaluate_tesseract.py --lang kan+eng --psm 6
"""

import argparse  # reads the options typed after the script name (--lang, --psm)
import subprocess  # lets Python run the tesseract program
from pathlib import Path  # makes working with file paths simple and safe

from app.metrics import character_error_rate  # your CER function from backend/app/metrics.py

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}  # only these file types count as images
DATASET = Path("dataset")  # the dataset folder, relative to the project root


def run_tesseract(image_path: Path, lang: str, psm: str | None) -> str:  # psm is optional (None = Tesseract's default)
    """Run the tesseract command and return the text it read."""
    command = ["tesseract", str(image_path), "stdout", "-l", lang]  # basic command: read the image, print text, use the language
    if psm is not None:  # only when the user asked for a specific layout mode
        command += ["--psm", psm]  # add the page segmentation mode to the command
    result = subprocess.run(  # run the command and wait for it to finish
        command,  # the command built above
        capture_output=True,  # catch the output instead of printing it to the screen
        text=True,  # give us the output as text, not raw bytes
        encoding="utf-8",  # read the text as UTF-8 so Kannada characters stay intact
        check=True,  # raise an error if tesseract fails
    )
    return result.stdout  # return only the text Tesseract found


def main() -> None:  # the main function; it runs the whole evaluation
    parser = argparse.ArgumentParser(description="Score Tesseract against ground truth.")  # sets up the option reader
    parser.add_argument("--lang", default="kan", help="Tesseract language, e.g. kan or kan+eng")  # language option, default Kannada
    parser.add_argument("--psm", default=None, help="Tesseract page segmentation mode, e.g. 3, 4 or 6")  # layout option, default none
    args = parser.parse_args()  # read what the user typed

    images = sorted(  # sorted() gives the images in alphabetical order every time
        p for p in (DATASET / "sample_images").iterdir()  # go through every file in the images folder
        if p.suffix.lower() in IMAGE_EXTENSIONS  # keep only image files (.lower() ignores capital letters)
    )
    if not images:  # if the list is empty, there is nothing to evaluate
        print("No images found in dataset/sample_images")  # tell the user what is wrong
        return  # stop the function here

    scores = []  # an empty list that will collect the CER score of each image
    print(f"Language setting: {args.lang}")  # show which language setting is used
    print(f"Page segmentation mode: {args.psm or 'default'}\n")  # show the layout mode, or 'default' if none was given
    for image in images:  # repeat the steps below for every image
        truth_file = DATASET / "ground_truth" / f"{image.stem}.txt"  # the matching text file (same name, .txt)
        if not truth_file.exists():  # if there is no ground-truth file for this image
            print(f"{image.name}: SKIPPED (no ground truth file {truth_file})")  # say it was skipped and why
            continue  # jump to the next image
        ocr_text = run_tesseract(image, args.lang, args.psm)  # let Tesseract read the image
        truth_text = truth_file.read_text(encoding="utf-8")  # read the correct text (UTF-8 keeps Kannada intact)
        cer = character_error_rate(ocr_text, truth_text)  # compare OCR text with the truth: 0.0 is perfect
        scores.append(cer)  # remember this score for the average
        print(f"{image.name}: CER = {cer:.3f}")  # show the score for this image

    if scores:  # only print an average if at least one image was scored
        print(f"\nAverage CER over {len(scores)} image(s): {sum(scores) / len(scores):.3f}")  # total divided by count


if __name__ == "__main__":  # true only when you run this file directly, not when it is imported
    main()  # start the evaluation