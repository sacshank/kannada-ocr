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

# Corrected results on 5 images (2026-11-24)

The ground truth for test3 and test4 contained typing mistakes that were fixed
after comparing both engines against the images. This table replaces the
test3 and test4 values in the earlier tables. Rule used: the ground truth
records exactly what the image shows, not what is grammatically correct.

Metric: character error rate (lower is better). Tesseract used kan+eng.

| Image | Tesseract default | Tesseract psm 4 | Tesseract psm 6 | Arjuna-OCR 1.3.3 |
|---|---|---|---|---|
| test1 | 0.122 | 0.122 | 0.102 | 0.051 |
| test2 | 0.357 | 0.357 | 0.857 | 0.119 |
| test3 (blurred newspaper photo, very small text) | 1.000 | 0.209 | 0.135 | 0.020 |
| test4 (WhatsApp group chat screenshot) | 0.878 | 0.878 | 0.908 | 1.010 |
| test5 | 0.010 | 0.010 | 0.010 | 0.030 |
| Average | 0.473 | 0.315 | 0.402 | 0.246 |
| Average without test4 | 0.372 | 0.175 | 0.276 | 0.055 |

Observations:

- Arjuna had the lowest error on test1, test2 and test3. Tesseract had the
  lowest on test5, where both engines scored very low.
- test4 is a stress test: its ground truth has only the Kannada message
  lines, while both engines also read usernames, timestamps and phone
  numbers. Arjuna read every Kannada line but swapped the order of two.
- The two engines agreed on a last line of test4 that looks like a spelling
  slip, which is how the ground-truth mistake was found.
- Per-image Arjuna time on the development laptop varied from 38 to 81 s.
- Only 5 images, so these numbers are a rough guide, not a conclusion.

# Results on 10 images (2026-11-24)

Metric: character error rate (lower is better). Tesseract used kan+eng;
psm is Tesseract's page segmentation (layout) mode.

| Image | Type | Tesseract default | Tesseract psm 4 | Tesseract psm 6 | Arjuna-OCR 1.3.3 |
|---|---|---|---|---|---|
| test1 | quote image | 0.122 | 0.122 | 0.102 | 0.051 |
| test2 | quote image | 0.357 | 0.357 | 0.857 | 0.119 |
| test3 | blurred newspaper photo, very small text | 1.000 | 0.209 | 0.135 | 0.020 |
| test4 | WhatsApp group chat screenshot | 0.878 | 0.878 | 0.908 | 1.010 |
| test5 | old textbook paragraph, 2 lines | 0.010 | 0.010 | 0.010 | 0.030 |
| test6 | government document | 0.041 | 0.041 | 0.041 | 0.045 |
| test7 | textbook | 0.867 | 0.891 | 0.331 | 0.247 |
| test8 | newspaper paragraph | 0.801 | 0.472 | 0.010 | 0.044 |
| test9 | Kannada and English mixed | 0.212 | 0.220 | 0.552 | 0.124 |
| test10 | Kannada text in a different font | 0.590 | 0.590 | 0.667 | 0.308 |
| Average | | 0.488 | 0.379 | 0.361 | 0.200 |
| Average without test4 | | 0.444 | 0.324 | 0.301 | 0.110 |

Tesseract with Kannada only (kan, default layout mode) averaged 0.516.
Adding English helped on test9 (0.560 to 0.212) and hurt on test10
(0.436 to 0.590).

Observations:

- Arjuna had the lowest average error. Tesseract's results depend strongly
  on the layout mode (for example test8 ranges from 0.010 to 0.801), and the
  best mode changed when the test set grew from 5 to 10 images.
- Comparing Arjuna with the best Tesseract setting on each image, Arjuna was
  lower on 6 of 10 images (test1, 2, 3, 7, 9, 10). Tesseract was lower or
  equal on test4, 5, 6 and 8. This per-image best-of comparison favours
  Tesseract, because a user cannot know which setting to choose.
- test4 is a stress test with interface clutter that the ground truth does
  not contain.
- Arjuna's weakest images are test10 (0.308) and test7 (0.247); the cause has
  not been investigated yet.
- Arjuna time on the development laptop: 36 to 47 s per image after an
  88.9 s model load. Tesseract timings were not recorded.
- Ground truth for test6 to test10 has not been double-checked against the
  images yet. Only 10 images, so these numbers are a rough guide.

# Final results on 10 images (2026-11-24)

These results replace the earlier 10-image table. The only change is the
test7 ground truth: five typing mistakes were corrected after comparing the
file with the image word by word (the corrections were typed from the image,
not copied from either engine). All other scores are unchanged from the
previous run.

Metric: character error rate (lower is better). Tesseract used kan+eng;
psm is Tesseract's page segmentation (layout) mode.

| Image | Type | Tesseract default | Tesseract psm 4 | Tesseract psm 6 | Arjuna-OCR 1.3.3 |
|---|---|---|---|---|---|
| test1 | quote image | 0.122 | 0.122 | 0.102 | 0.051 |
| test2 | quote image | 0.357 | 0.357 | 0.857 | 0.119 |
| test3 | blurred newspaper photo, very small text | 1.000 | 0.209 | 0.135 | 0.020 |
| test4 | WhatsApp group chat screenshot | 0.878 | 0.878 | 0.908 | 1.010 |
| test5 | old textbook paragraph, 2 lines | 0.010 | 0.010 | 0.010 | 0.030 |
| test6 | government document | 0.041 | 0.041 | 0.041 | 0.045 |
| test7 | textbook contents page | 0.869 | 0.893 | 0.331 | 0.238 |
| test8 | newspaper paragraph | 0.801 | 0.472 | 0.010 | 0.044 |
| test9 | Kannada and English mixed | 0.212 | 0.220 | 0.552 | 0.124 |
| test10 | Kannada text in a different font | 0.590 | 0.590 | 0.667 | 0.308 |
| Average | | 0.488 | 0.379 | 0.361 | 0.199 |
| Average without test4 | | 0.445 | 0.324 | 0.301 | 0.109 |

Tesseract with Kannada only (kan, default layout mode) averaged 0.516.

Observations:

- Arjuna had the lowest average error and needs no layout tuning. Tesseract
  results depend strongly on the layout mode and on the language setting.
- Compared with the best Tesseract setting on each image, Arjuna was lower on
  test1, 2, 3, 7, 9 and 10. Tesseract was lower on test4, 5, 6 and 8, where
  the differences on test5 and test6 are very small.
- test7 (a table-like contents page): Arjuna inserted "|" separators between
  columns, moved two lines to the end of the output, misread some digits,
  and misread letters in two words (items 4 and 11). It read the unusual
  spelling in item 6 correctly.
- test10 is the weakest image for Arjuna: nearly every word has a wrong
  letter in this font.
- test4 is a stress test: both engines also read usernames, timestamps and
  phone numbers that the ground truth does not contain, and Arjuna swapped
  the order of two lines.
- Arjuna time on the development laptop: 34 to 90 s per image, after a model
  load of about 90 s. Timings varied between runs. Tesseract timings were
  not recorded.
- Only 10 images, so these numbers are a rough guide, not a conclusion.

# Phase 4 experiment: image enlargement (2026-11-25)

Script: scripts/evaluate_preprocessing.py. Each image is re-saved as PNG
at a scale factor (1.0 = unchanged) and scored with the same CER metric.
The stored DPI of the original file is scaled with the image.

## Arjuna-OCR (3 images; x1.0 matches the earlier Phase 3 scores)

| Image | x1.0 | x2.0 |
|---|---|---|
| test10 | 0.308 | 0.282 |
| test3 | 0.020 | 0.101 |
| test7 | 0.238 | 0.310 |
| Average | 0.189 | 0.231 |

Enlarging 2x did not help Arjuna on average: two of three images got worse.
Not tested: whether Arjuna's 2x results depend on the stored DPI.

## Tesseract (kan+eng, default layout mode, all 10 images)

| Image | x1.0 | x1.5 | x2.0 |
|---|---|---|---|
| test1 | 0.122 | 0.194 | 0.388 |
| test10 | 0.590 | 0.436 | 0.487 |
| test2 | 0.357 | 0.048 | 0.048 |
| test3 | 1.000 | 1.000 | 1.000 |
| test4 | 0.878 | 0.949 | 0.918 |
| test5 | 0.010 | 0.020 | 0.020 |
| test6 | 0.164 | 0.296 | 0.428 |
| test7 | 0.869 | 0.669 | 0.380 |
| test8 | 0.878 | 0.829 | 0.909 |
| test9 | 0.207 | 0.187 | 0.178 |
| Average | 0.508 | 0.463 | 0.476 |

Findings about Tesseract:

- Re-saving an image changes Tesseract's result. test10 scored 0.590 on the
  original file but 0.667 on a re-saved PNG without DPI; storing 96 DPI in
  the PNG restored 0.590.
- test6 scored 0.041 on the original JPEG file but 0.164 on a re-saved PNG
  with identical pixels (Pillow and OpenCV decode it identically). Giving
  the exact DPI on the command line did not change this. The cause is not
  known.
- Scaling the DPI with the enlargement changed results strongly for images
  that have a stored DPI. At x2.0, with DPI dropped (first run): test3 0.223,
  test6 0.039, test10 0.846. With DPI scaled (this run): test3 1.000,
  test6 0.428, test10 0.487.
- Images without a stored DPI (test1, test2, test7) behave the same either
  way. On those, enlarging helped test2 and test7 and hurt test1.
- Because of this metadata sensitivity, the Tesseract averages above are not
  a clean measure of the effect of enlarging.

Conclusion so far: blanket enlargement is not a good default for either
engine. Each preprocessing step must be measured per engine.

# Phase 4 experiment: contrast enhancement (2026-11-25)

Contrast enhancement: CLAHE on the lightness channel (clip limit 2.0,
8x8 tiles), applied before the engine reads the image. Script:
scripts/evaluate_preprocessing.py --contrast. The comparison column is the
same pipeline without contrast (x1.0); for the three Arjuna images these
values match the Phase 3 scores.

## Arjuna-OCR (3 images)

| Image | Without contrast | With contrast |
|---|---|---|
| test10 | 0.308 | 0.333 |
| test3 | 0.020 | 0.041 |
| test7 | 0.238 | 0.663 |
| Average | 0.189 | 0.346 |

## Tesseract (kan+eng, default layout mode, all 10 images)

| Image | Without contrast | With contrast |
|---|---|---|
| test1 | 0.122 | 1.000 |
| test10 | 0.590 | 1.000 |
| test2 | 0.357 | 0.452 |
| test3 | 1.000 | 0.676 |
| test4 | 0.878 | 0.898 |
| test5 | 0.010 | 0.030 |
| test6 | 0.164 | 0.775 |
| test7 | 0.869 | 0.798 |
| test8 | 0.878 | 0.016 |
| test9 | 0.207 | 0.253 |
| Average | 0.508 | 0.590 |

Findings:

- Contrast enhancement made Arjuna worse on all three images tested, most
  strongly on test7 (0.238 to 0.663). The cause is not known.
- For Tesseract it helped three images (test3, test7, test8) and hurt seven.
  A CER of 1.000 means empty output scores; the output was not inspected.
- Neither enlargement nor contrast enhancement is a safe default for either
  engine. The original image remains the default input.
- Only one parameter setting was tried, on a small and varied test set.
- Not tested: tilted or shadowed photographs (the test set has none),
  deskewing, denoising, thresholding, sharpening.
