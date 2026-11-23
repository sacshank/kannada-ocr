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
