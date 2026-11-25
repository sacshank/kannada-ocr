"""Compare OCR error at different image sizes (Phase 4 experiment).

Usage (from the project root, with the virtual environment active):
    PYTHONPATH=backend python scripts/evaluate_preprocessing.py --engine tesseract --factors 1.0
    PYTHONPATH=backend python scripts/evaluate_preprocessing.py --engine tesseract --factors 0.5 1.0 1.5 2.0
    PYTHONPATH=backend python scripts/evaluate_preprocessing.py --engine arjuna --factors 1.0 2.0 --only test3 test5
"""

import argparse  # reads the options typed after the script name
import subprocess  # lets Python run the tesseract program
import tempfile  # makes a temporary folder that is deleted automatically
import time  # used to measure how long each image takes
from pathlib import Path  # makes working with file paths simple and safe

from app.image_processor import load_image, read_dpi, resize_image, save_image  # our own image functions from Phase 4
from app.metrics import character_error_rate  # your CER function from backend/app/metrics.py

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}  # only these file types count as images
DATASET = Path("dataset")  # the dataset folder, relative to the project root


def read_with_tesseract(image_path: Path, lang: str, psm: str | None) -> str:  # run Tesseract on one image file
    """Run the tesseract command on an image file and return the text it read."""
    command = ["tesseract", str(image_path), "stdout", "-l", lang]  # basic command: read the image, print text, use the language
    if psm is not None:  # only when a specific layout mode was requested
        command += ["--psm", psm]  # add the page segmentation mode to the command
    result = subprocess.run(  # run the command and wait for it to finish
        command,  # the command built above
        capture_output=True,  # catch the output instead of printing it to the screen
        text=True,  # give us the output as text, not raw bytes
        encoding="utf-8",  # read the text as UTF-8 so Kannada characters stay intact
        check=True,  # raise an error if tesseract fails
    )
    return result.stdout  # return only the text Tesseract found


def read_with_arjuna(ocr, image_path: Path) -> str:  # run Arjuna on one image file
    """Run an already loaded Arjuna engine on an image file and return the text it read."""
    doc = ocr.page(str(image_path))  # let Arjuna read the image; it returns a structured result
    text = doc.get("text") if isinstance(doc, dict) else None  # take the plain text from the result
    if text is None:  # if the result had no "text" entry
        text = ocr.render(doc, "txt")  # ask Arjuna to turn the result into plain text instead
    return text  # return the text Arjuna found


def main() -> None:  # the main function; it runs the whole experiment
    parser = argparse.ArgumentParser(description="Score OCR at different image sizes.")  # sets up the option reader
    parser.add_argument("--engine", choices=["tesseract", "arjuna"], required=True)  # which engine to test (required)
    parser.add_argument("--factors", nargs="+", type=float, default=[1.0])  # one or more scale factors; 1.0 means unchanged
    parser.add_argument("--only", nargs="*", default=None, help="image names without extension, e.g. test3 test5")  # optional: test only these images
    parser.add_argument("--lang", default="kan+eng", help="Tesseract language, e.g. kan or kan+eng")  # Tesseract language setting
    parser.add_argument("--psm", default=None, help="Tesseract page segmentation mode, e.g. 4 or 6")  # Tesseract layout mode, default none
    args = parser.parse_args()  # read what the user typed

    images = sorted(  # sorted() gives the images in alphabetical order every time
        p for p in (DATASET / "sample_images").iterdir()  # go through every file in the images folder
        if p.suffix.lower() in IMAGE_EXTENSIONS  # keep only image files (.lower() ignores capital letters)
    )
    if args.only:  # if the user named specific images
        images = [p for p in images if p.stem in args.only]  # keep only those images
    if not images:  # if the list is empty, there is nothing to evaluate
        print("No images to evaluate")  # tell the user what is wrong
        return  # stop the function here

    ocr = None  # Arjuna is only loaded when it is needed
    if args.engine == "arjuna":  # only for the Arjuna engine
        from kanen_infer import KanEnOCR  # import name of the Arjuna engine (from its model card)
        start = time.perf_counter()  # note the time before loading the models
        ocr = KanEnOCR()  # load the Arjuna models into memory (the slow part, done once)
        print(f"Model load time: {time.perf_counter() - start:.1f}s\n")  # show how long loading took

    scores: dict[str, dict[float, float | None]] = {}  # image name -> {factor: CER score, or None if it failed}
    with tempfile.TemporaryDirectory() as tmp:  # a temporary folder, deleted when this block ends
        for image in images:  # repeat the steps below for every image
            truth_file = DATASET / "ground_truth" / f"{image.stem}.txt"  # the matching text file (same name, .txt)
            if not truth_file.exists():  # if there is no ground-truth file for this image
                print(f"{image.name}: SKIPPED (no ground truth file)")  # say it was skipped
                continue  # jump to the next image
            truth_text = truth_file.read_text(encoding="utf-8")  # read the correct text (UTF-8 keeps Kannada intact)
            original = load_image(image)  # open the image and fix its rotation
            original_dpi = read_dpi(image)  # the DPI stored in the original file, or None if it has none
            scores[image.stem] = {}  # start an empty score record for this image
            for factor in args.factors:  # try each requested scale factor
                try:  # a failure on one version must not stop the whole run
                    version = original if factor == 1.0 else resize_image(original, factor)  # unchanged, or resized copy
                    version_dpi = None if original_dpi is None else (original_dpi[0] * factor, original_dpi[1] * factor)  # DPI scales with the size (our assumption)
                    temp_path = Path(tmp) / f"{image.stem}_{factor}.png"  # where this version is saved for a moment
                    save_image(version, temp_path, dpi=version_dpi)  # save it as PNG, keeping the DPI if the original had one
                    start = time.perf_counter()  # note the time before reading
                    if args.engine == "tesseract":  # use Tesseract
                        text = read_with_tesseract(temp_path, args.lang, args.psm)  # let Tesseract read this version
                    else:  # otherwise use Arjuna
                        text = read_with_arjuna(ocr, temp_path)  # let Arjuna read this version
                    seconds = time.perf_counter() - start  # how many seconds this version took
                    cer = character_error_rate(text, truth_text)  # compare OCR text with the truth: 0.0 is perfect
                    scores[image.stem][factor] = cer  # remember the score
                    print(f"{image.name} x{factor}: CER = {cer:.3f} ({seconds:.1f}s)")  # show the score and time
                    temp_path.unlink()  # delete the temporary image right away
                except Exception as error:  # anything that went wrong with this version
                    scores[image.stem][factor] = None  # record that it failed
                    print(f"{image.name} x{factor}: ERROR {type(error).__name__}: {error}")  # show what went wrong

    print("\nSummary (CER, lower is better)")  # heading for the final table
    print(f"{'image':12}" + "".join(f"{'x' + str(f):>9}" for f in args.factors))  # header row: one column per factor
    for name, row in scores.items():  # one table row per image
        cells = "".join(f"{row[f]:>9.3f}" if row.get(f) is not None else f"{'fail':>9}" for f in args.factors)  # a score, or 'fail'
        print(f"{name:12}{cells}")  # print the row
    averages = []  # will hold one average per factor
    for f in args.factors:  # go through each factor
        values = [row[f] for row in scores.values() if row.get(f) is not None]  # all scores that exist for this factor
        averages.append(f"{sum(values) / len(values):>9.3f}" if values else f"{'n/a':>9}")  # their average, or n/a
    print(f"{'average':12}" + "".join(averages))  # print the average row


if __name__ == "__main__":  # true only when you run this file directly, not when it is imported
    main()  # start the experiment