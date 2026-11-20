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
