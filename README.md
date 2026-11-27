# Kannada OCR

Extracts editable Unicode Kannada text from images (JPG, JPEG, PNG, WEBP).
It compares two OCR engines on real Kannada images and serves the better one
through a small FastAPI web service.

## Status

- Done: engine comparison and benchmark, image preprocessing experiments,
  FastAPI backend with 90 automated tests.
- Not built yet: web frontend (Next.js), Docker, deployment.
- Planned later: PDF input (up to 3 pages). PDFs are rejected today.

## Results so far

Character error rate (CER, lower is better) on 10 hand-checked test images.
The engines are Arjuna-OCR 1.3.3 and Tesseract 5 (Kannada plus English).
Tesseract's result depends on its layout mode, so three modes are shown.

| Engine | Average CER |
|---|---|
| Arjuna-OCR 1.3.3 | 0.199 |
| Tesseract, default layout | 0.488 |
| Tesseract, layout mode 4 | 0.379 |
| Tesseract, layout mode 6 | 0.361 |

Without the WhatsApp screenshot (a stress test whose ground truth leaves out
usernames, timestamps and phone numbers) Arjuna averages 0.109.

These are rough numbers: the test set is small, and one person typed the
ground truth. The per-image table and all caveats are in
[docs/baseline.md](docs/baseline.md).

Preprocessing finding: enlarging images and boosting contrast did not help as
defaults for either engine, so the original image is sent to the engine.

## Requirements

- Python 3.12
- The first run downloads the Arjuna models (Arjuna reports about 170 MB).
- Tesseract is needed only for the benchmark scripts, not for the API:

```bash
sudo apt install tesseract-ocr tesseract-ocr-kan tesseract-ocr-eng  # install Tesseract with Kannada and English data (Debian or Ubuntu)
```

## Setup

```bash
python3 -m venv .venv  # create a private Python environment in the folder .venv
source .venv/bin/activate  # switch to that environment
pip install -r backend/requirements-dev.txt  # install the app and the test tools
```

## Run the tests

```bash
pytest backend/tests  # run all automated tests; they use a fake OCR engine, so they take seconds
```

## Run the API

```bash
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000  # start the service on this computer only, on port 8000
```

The OCR models load in the background after the server starts. This took
roughly 90 to 125 seconds in testing. `GET /health` answers at once and
shows `"model_loaded": true` when the models are ready.

### Endpoints

`GET /health` returns `{"status": "ok", "model_loaded": true}`.

`POST /api/ocr` takes one image in the form field `file`:

```bash
curl -F "file=@photo.jpg;type=image/jpeg" http://127.0.0.1:8000/api/ocr  # upload an image and print the JSON answer
```

Example answer (the values are an example, not real output):

```json
{
  "success": true,
  "extracted_text": "ಕರ್ನಾಟಕ",
  "processing_time": 2.5,
  "language": "Kannada"
}
```

If the engine finds no text, `extracted_text` is empty and a `message` field
says so. The service never invents text. Errors look like
`{"success": false, "error": "..."}` with these status codes:

| Code | Meaning |
|---|---|
| 400 | empty file, damaged image, or no file sent |
| 413 | file over the size limit, or too many pixels |
| 415 | not a JPG, PNG or WEBP image (PDFs are rejected) |
| 422 | malformed request |
| 500 | the OCR engine failed |

The file type is decided by looking inside the file, not by its name.

### Configuration

| Environment variable | Meaning | Default |
|---|---|---|
| `MAX_UPLOAD_MB` | largest upload in megabytes | 10 |
| `ALLOWED_ORIGINS` | websites allowed to call the API, comma separated | `http://localhost:3000` |
| `LOG_LEVEL` | log detail | `INFO` |

## Privacy

An uploaded image is written to a private temporary folder, read, and deleted
immediately, also when something fails. Log lines contain only timings and
character counts, never the image or the extracted text (a test checks this).

## Benchmark

The test images and their ground-truth text are not in this repository
(see [dataset/README.md](dataset/README.md)). The scripts in `scripts/` show
how the numbers were produced:

```bash
PYTHONPATH=backend python scripts/evaluate_arjuna.py  # score Arjuna on every image in dataset/sample_images
PYTHONPATH=backend python scripts/evaluate_tesseract.py --lang kan+eng --psm 4  # score Tesseract with Kannada plus English, layout mode 4
PYTHONPATH=backend python scripts/evaluate_preprocessing.py --engine arjuna --factors 1.0  # run the preprocessing experiment for one engine
```

## Known limitations

- Without a GPU, reading one image took about 20 to 90 seconds and varied
  between runs.
- About 3.6 GiB of memory was in use during one read. Larger images were not
  tested.
- The API processes one image at a time.
- Arjuna adds "|" separators to table-like pages and moved two lines out of
  order on the textbook contents page.
- Arjuna was weakest on a stylised font (CER 0.308 on one image).
- Only 10 test images. Tilted and shadowed photos are not covered yet.

## Licenses

See [LICENSE](LICENSE). Arjuna-OCR and Tesseract are separate projects with
their own licenses. Check the Arjuna model card for the license of each model.
