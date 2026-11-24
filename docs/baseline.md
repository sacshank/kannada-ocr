# Baseline: Tesseract on the local sample set

Metric: character error rate (CER). 0.0 is perfect; higher is worse.

Sample set: 2 images (small, so treat the numbers as rough hints).

| Language setting | test1 | test2 | Average |
|---|---|---|---|
| kan | 0.133 | 0.405 | 0.269 |
| kan+eng | 0.122 | 0.357 | 0.240 |

Observations:
- Tesseract with `kan` alone forces English text into Kannada letters.
- `kan+eng` improved both images slightly, but mixed Kannada/English lines are still misread.
- Next: add more test images before drawing conclusions.

# Baseline: Arjuna-OCR on the local sample set

Same 2 images, same metric (character error rate, lower is better).
Engine: Arjuna-OCR 1.3.3 on CPU (WSL, 4 cores, about 4 GB RAM).

| Engine | test1 | test2 | Average |
|---|---|---|---|
| Tesseract `kan` | 0.133 | 0.405 | 0.269 |
| Tesseract `kan+eng` | 0.122 | 0.357 | 0.240 |
| Arjuna-OCR 1.3.3 | 0.051 | 0.119 | 0.085 |

Speed on the development laptop (Intel Core i3-5005U, 2 cores):

- Arjuna model load: 123.8 s on this run.
- Arjuna per image: 30.6 s (test1) and 25.5 s (test2).
- Tesseract timings were not recorded.

Observations:

- Arjuna had a lower CER than Tesseract on both images.
- With only 2 images this is a rough hint, not a conclusion.
- Speed and load time need re-measuring on the hosting target.
- Next: add more test images across categories before drawing conclusions.

Reproduce with:

    PYTHONPATH=backend python scripts/evaluate_arjuna.py

# Baseline: Tesseract and Arjuna-OCR on 5 images

Metric: character error rate (lower is better). Tesseract used the kan+eng
language setting; psm is Tesseract's page segmentation (layout) mode.

| Image | Tesseract default | Tesseract psm 4 | Tesseract psm 6 | Arjuna-OCR 1.3.3 |
|---|---|---|---|---|
| test1 | 0.122 | 0.122 | 0.102 | 0.051 |
| test2 | 0.357 | 0.357 | 0.857 | 0.119 |
| test3 (blurred newspaper photo, very small text) | 1.000 | 0.216 | 0.128 | 0.027 |
| test4 (WhatsApp group chat screenshot) | 0.918 | 0.918 | 0.948 | 1.052 |
| test5 | 0.010 | 0.010 | 0.010 | 0.030 |
| Average | 0.481 | 0.325 | 0.409 | 0.256 |

Observations:

- Arjuna had the lowest error on test1, test2 and test3. Tesseract had the
  lowest on test5, where both engines scored very low.
- Tesseract's default layout mode found no text in test3. Modes 4 and 6 read
  it, but mode 6 made test2 much worse, so no single mode wins everywhere.
- test4 is a stress test. Its ground truth contains only the Kannada message
  lines. Both engines also read usernames, timestamps and phone numbers,
  which count as errors. Arjuna read all the Kannada lines but swapped the
  order of two of them, so line ordering needs attention.
- Arjuna CER above 1.0 on test4 means it produced more edits than the ground
  truth has characters.
- Tesseract output contained invisible ZWNJ characters that are not in the
  hand-typed ground truth; the strict metric counts them as errors.
- Only 5 images, so these numbers are a rough guide, not a conclusion.

Speed on the development laptop (Intel Core i3-5005U, WSL with 4.8 GB RAM):

- Arjuna model load: 91.7 s on this run.
- Arjuna per image: 36 to 46 s. An earlier run measured 26 to 31 s, so
  timings vary between runs.
- With the WSL default of 3.8 GB RAM, Arjuna was killed by the system while
  reading these 5 images. Raising WSL memory to 5 GB fixed it.
- Tesseract timings were not recorded.

Reproduce with:

    PYTHONPATH=backend python scripts/evaluate_tesseract.py --lang kan+eng --psm 4
    PYTHONPATH=backend python scripts/evaluate_arjuna.py
