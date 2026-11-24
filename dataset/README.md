# Dataset

Test images and their ground-truth text live here **locally**. They are not
committed to Git (see `.gitignore`), because some images are copyrighted
(newspapers) or private (chat screenshots).

## Folder layout

    dataset/
      sample_images/   the images (.jpg, .jpeg, .png, .webp)
      ground_truth/    one .txt file per image, with the correct text

## Naming

An image and its ground-truth file share the same name, for example
`sample_images/test3.jpeg` and `ground_truth/test3.txt`. An image without a
ground-truth file is skipped by the evaluation scripts.

## Rules for writing ground truth

1. Type exactly what the image shows, not what is grammatically correct.
   If an image contains a spelling slip, the ground truth keeps the slip.
2. Keep the same line breaks as the image.
3. Include everything visible in the image, or crop the image so only the
   text you typed remains. Text left out of the file counts as an OCR error.
4. Save as UTF-8. Do not add titles, notes or extra lines.
5. Re-read each file against its image once. A typing mistake in the ground
   truth shows up as a fake OCR error.

## How scores are computed

`backend/app/metrics.py` computes character error rate (CER): the edit
distance between the OCR text and the ground truth, divided by the length of
the ground truth. Lower is better, and 0.0 is perfect. Text is normalised
(Unicode NFC, extra spaces and blank lines removed) before comparing.
A value above 1.0 is possible when the OCR output contains more errors than
the ground truth has characters.

## Running the evaluations

From the project root, with the virtual environment active:

    PYTHONPATH=backend python scripts/evaluate_tesseract.py --lang kan+eng --psm 4
    PYTHONPATH=backend python scripts/evaluate_arjuna.py

Results are recorded in `docs/baseline.md`.

## Image categories

The target categories are newspaper photos, textbook pages, screenshots,
government documents and low-quality photos. The current set is small and is
a rough guide only.
