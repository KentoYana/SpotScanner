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
case, and by default runs the current checkout through `python -m spotscanner`. It ignores
the analysis timestamp. Image names, thresholds, and row/column coordinates
must match exactly. Numeric `Colony` values are compared as decimal values;
archived `NA` cells are reported and excluded from the numeric comparison.
Generated diagnostic PNGs must decode as nonempty binary images with dimensions
no larger than the input. Generated numeric values must be finite and in 0–100,
including cells whose archived reference was `NA`.

## Pipette-mode baseline results

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

## Replicator-mode baseline results

The user-provided `Stamp.zip` archive extends the regression coverage to the
8 × 12 replicator grid. Its SHA-256 is
`131c9198f2e747568df8b2a60c6622f5ff4bd52d442e91ce7b682f2d7a56d37d`.
Directories without result files are ignored by discovery.

The archive contains 144 per-image `*_results.csv` files. Of these, 42 use the
current 0–100 cover-rate schema with 96 rows. Another 102 use an older
`Position` schema whose `Colony` values are binary 0/1 measurements; they are
not numerically comparable and are reported as skipped. One additional wide
aggregate results CSV and four metadata CSVs do not match the per-image result
pattern and are not regression inputs.

Four source images had been renamed after analysis. Comparing all four
re-analyses against all four archived vectors gave one unambiguous mapping:

| Archived result stem | Source image stem | Correct-pair mean absolute difference | Next-best mean absolute difference |
| --- | --- | ---: | ---: |
| `P6153542` | `Control` | 0.00750 | 3.25938 |
| `P6153543` | `His` | 0.00594 | 3.26260 |
| `P6153544` | `Hyg` | 0.00490 | 7.27469 |
| `P6153545` | `BA` | 0.01458 | 10.36938 |

With those aliases, all 42 compatible images and 4,032 cells were analyzed
using Python 3.14.6, NumPy 2.5.1, and OpenCV 5.0.0. There were no CLI,
marker-detection, threshold, coordinate, shape, or metadata errors.

- Exact cells: 2,679 (66.44%)
- Cells differing after two-decimal output: 1,353
- Mean absolute difference across all cells: 0.00633 percentage points
- Maximum absolute difference: 0.17 percentage points
- Recorded thresholds: 11 images at 6, 13 at 7, and 18 at 8

The 38 directly basename-matched images produced the same comparison values
under NumPy 2.3.5/OpenCV 4.14.0 and NumPy 2.5.1/OpenCV 5.0.0. The observed
cross-generation compatibility envelope for replicator mode is therefore 0.17
percentage points. As with pipette mode, this is an absolute difference on the
0–100 output scale, not a 17% relative error.

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

To validate an installed distribution instead of the checkout, specify its
console script explicitly:

```bash
python tools/compare_v7_results.py \
  /path/to/Resource_Article_DDT_hH3-K4R_01 \
  --executable "$(brew --prefix spotscanner)/bin/spotscanner" \
  --tolerance 0.12 \
  --work-dir /tmp/spotscanner-brew-pipette \
  --report /tmp/spotscanner-brew-pipette.json
```

Use a fresh `--work-dir` for each run. The installed mode requires an absolute
Python shebang (as generated by pip and the Formula), probes that interpreter,
and removes `PYTHONPATH`, `PYTHONHOME`, `SPOTSCANNER_ROOT`, and `SPOTSCANNER`
overrides so that local source and legacy resource paths cannot mask packaging
problems. The report records the actual command, installed module paths, and
runtime versions; the checkout commit is labeled as the regression tool's
commit rather than attributed to the installed package.

`different_cells` counts failures beyond the selected tolerance;
`exact_different_cells`, the difference histogram, maximum, and mean describe
all comparable cells regardless of tolerance. Thus an accepted historical
envelope does not hide numerical drift. Retained outputs also allow direct
comparison of current pip and Homebrew results, ignoring only timestamps.

For the replicator archive, extract `Stamp.zip`, then run:

```bash
PYENV_VERSION=3.14.6 pyenv exec python tools/compare_v7_results.py \
  /path/to/Stamp \
  --mode replicator \
  --skip-incompatible-results \
  --image-alias P6153542=Control \
  --image-alias P6153543=His \
  --image-alias P6153544=Hyg \
  --image-alias P6153545=BA \
  --tolerance 0.17 \
  --report /tmp/spotscanner-replicator-compatible.json
```

Unsupported legacy results are listed in the JSON report rather than silently
treated as current cover-rate measurements.
