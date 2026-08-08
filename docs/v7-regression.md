# SpotScanner 7 numerical regression

The manuscript resource repository is the external numerical baseline for the
SpotScanner 8 packaging migration:

- Repository: `KentoYana/Resource_Article_DDT_hH3-K4R_01`
- Baseline commit: `b470359d1cc46898509d6cd294457afb6b609844`
- SpotScanner version recorded by the resource README: 7.0.0
- Dataset: 304 pipette-mode JPEG images and 304 result CSV files
- Recorded thresholds: 281 images at 7 and 23 images at 6
- Measurements: 7,296 cells, of which 11 archived values are `NA`

The source repository is never modified. The comparison tool creates a
temporary directory, symlinks one image into an isolated directory for each
case, and runs the current checkout through `python -m spotscanner`. It ignores
the analysis timestamp. Image names, thresholds, and row/column coordinates
must match exactly. Numeric `Colony` values are compared as decimal values;
archived `NA` cells are reported and excluded from the numeric comparison.

## 2026-08-08 baseline results

The full dataset was run from the `dev7to8` working tree with the unchanged 7.x
image-analysis algorithm.

| Runtime | Exact numeric cells | Different numeric cells | Affected images | Maximum absolute difference |
| --- | ---: | ---: | ---: | ---: |
| Python 3.12.12, NumPy 2.2.6, OpenCV 4.12.0 | 7,224 (99.16%) | 61 | 12 | 0.11 |
| Python 3.14.6, NumPy 2.3.5, OpenCV 4.14.0 | 5,642 (77.45%) | 1,643 | 179 | 0.12 |
| Python 3.14.6, NumPy 2.5.1, OpenCV 4.14.0 | 5,642 (77.45%) | 1,643 | 179 | 0.12 |
| Python 3.14.6, NumPy 2.5.1, OpenCV 5.0.0 | 5,642 (77.45%) | 1,643 | 179 | 0.12 |

All runs completed 304 analyses without CLI, image-detection, coordinate, or
metadata errors. OpenCV 4.14 and 5.0 produced identical comparable CSV values
in the Python 3.14 runs. The Python 3.14 differences were distributed as
follows:

| Absolute difference | Cells |
| ---: | ---: |
| 0.01 | 873 |
| 0.02 | 350 |
| 0.03 | 175 |
| 0.04 | 111 |
| 0.05 | 57 |
| 0.06 | 27 |
| 0.07 | 21 |
| 0.08 | 10 |
| 0.09 | 10 |
| 0.10 | 4 |
| 0.11 | 4 |
| 0.12 | 1 |

Across all 7,285 comparable cells, the Python 3.14 mean absolute difference
was 0.00467 percentage points. The archived execution environment was not
version-locked, so the evidence supports a runtime-generation effect but does
not identify a single library release as its sole cause. NumPy versions older
than 2.3 do not provide a Python 3.14 wheel, so pinning the 3.14 installation to
the closer 3.12-era environment is not a practical distribution strategy.

For cross-generation regression, 0.12 percentage points is therefore the
observed compatibility envelope. This tolerance applies only to numeric
`Colony` values: image identity, threshold, coordinates, output shape, and CLI
success remain exact requirements. A change beyond 0.12, or a material change
in the distribution above, requires investigation before release.

## Reproducing the comparison

Use a pyenv-selected interpreter. An exact comparison intentionally exits with
status 1 when any numeric difference is found:

```bash
PYENV_VERSION=3.14.6 pyenv exec python tools/compare_v7_results.py \
  /path/to/Resource_Article_DDT_hH3-K4R_01 \
  --report /tmp/spotscanner-v7-exact.json
```

Use the observed cross-generation compatibility envelope for a release gate:

```bash
PYENV_VERSION=3.14.6 pyenv exec python tools/compare_v7_results.py \
  /path/to/Resource_Article_DDT_hH3-K4R_01 \
  --tolerance 0.12 \
  --report /tmp/spotscanner-v7-compatible.json
```

The JSON report records both repositories' commits and dirty states,
SpotScanner version, Python, NumPy, and OpenCV versions, counts, errors, and
differences beyond the selected tolerance. Use `--limit N` only for a quick
local check.
