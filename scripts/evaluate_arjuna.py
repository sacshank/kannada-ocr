"""Run Arjuna-OCR on every sample image and score it against the ground truth.

Usage (from the project root, with the virtual environment active):
    PYTHONPATH=backend python scripts/evaluate_arjuna.py
"""

import time  # used to measure how long loading and reading take
from pathlib import Path  # makes working with file paths simple and safe

from app.metrics import character_error_rate  # your CER function from backend/app/metrics.py

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}  # only these file types count as images
DATASET = Path("dataset")  # the dataset folder, relative to the project root


def main() -> None:  # the main function; it runs the whole evaluation
    from kanen_infer import KanEnOCR  # import name of the Arjuna engine (from its model card)

    images = sorted(  # sorted() gives the images in alphabetical order every time
        p for p in (DATASET / "sample_images").iterdir()  # go through every file in the images folder
        if p.suffix.lower() in IMAGE_EXTENSIONS  # keep only image files (.lower() ignores capital letters)
    )
    if not images:  # if the list is empty, there is nothing to evaluate
        print("No images found in dataset/sample_images")  # tell the user what is wrong
        return  # stop the function here

    start = time.perf_counter()  # note the current time before loading the models
    ocr = KanEnOCR()  # load the Arjuna models into memory (this is the slow part)
    print(f"Model load time: {time.perf_counter() - start:.1f}s\n")  # show how many seconds loading took

    scores = []  # an empty list that will collect the CER score of each image
    for image in images:  # repeat the steps below for every image
        truth_file = DATASET / "ground_truth" / f"{image.stem}.txt"  # the matching text file (same name, .txt)
        if not truth_file.exists():  # if there is no ground-truth file for this image
            print(f"{image.name}: SKIPPED (no ground truth file {truth_file})")  # say it was skipped and why
            continue  # jump to the next image

        start = time.perf_counter()  # note the time before reading this image
        doc = ocr.page(str(image))  # run Arjuna on the image; it returns a structured result
        ocr_text = doc.get("text") if isinstance(doc, dict) else None  # take the plain text from the result
        if ocr_text is None:  # if the result had no "text" entry
            ocr_text = ocr.render(doc, "txt")  # ask Arjuna to turn the result into plain text instead
        seconds = time.perf_counter() - start  # how many seconds this image took

        truth_text = truth_file.read_text(encoding="utf-8")  # read the correct text (UTF-8 keeps Kannada intact)
        cer = character_error_rate(ocr_text, truth_text)  # compare OCR text with the truth: 0.0 is perfect
        scores.append(cer)  # remember this score for the average
        print(f"{image.name}: CER = {cer:.3f} ({seconds:.1f}s)")  # show the score and time for this image

    if scores:  # only print an average if at least one image was scored
        print(f"\nAverage CER over {len(scores)} image(s): {sum(scores) / len(scores):.3f}")  # total divided by count


if __name__ == "__main__":  # true only when you run this file directly, not when it is imported
    main()  # start the evaluation