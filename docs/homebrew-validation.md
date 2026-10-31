# Homebrew runtime validation — 2026-10-31

This record describes the original 8.0.1_1 repair and its validation. The
versions and results below are historical evidence, not a relabeling of those
runs as 8.0.2. For the current release procedure, see
[Homebrew distribution and release maintenance](homebrew.md).

## Cause and distribution policy

The installed `opencv` 5.0.0_12 supplies its Python bindings for Python 3.15.
The original SpotScanner 8.0.1 Formula declared and created a Python 3.14
virtual environment. `--version` does not import the analysis dependencies,
so it succeeded while analysis failed with `ModuleNotFoundError: cv2`.
The current [Homebrew OpenCV metadata](https://formulae.brew.sh/api/formula/opencv.json)
was fetched directly on the validation date and also declared `python@3.15`
(core commit `e9e970a6894f23a16eaea5b7132dfd0627c870c1`).

The corrected Formula declares Python 3.15 and uses it to create the venv.
Revision 1 makes the same 8.0.1 release upgradeable as `8.0.1_1`. The source
archive URL and SHA-256 remain unchanged:
`14a38895dd6451a573dcbb74090edf18a944b4ab46d523dc6684832d58204fde`.
An installation-time import checks the shared NumPy/OpenCV environment.

| Distribution tested | Python | NumPy | OpenCV |
| --- | --- | --- | --- |
| Isolated pip venv | 3.14.10 | 2.5.1 | `opencv-python-headless` 5.0.0.93 (`cv2` 5.0.0) |
| Homebrew 8.0.1_1 | 3.15.2 | 2.5.4 | `opencv` 5.0.0_12 (`cv2` 5.0.0) |

The pip pins and their exact version assertions remain unchanged. They preserve
the previously validated numerical environment. The Formula deliberately uses
Homebrew-managed native libraries via `--system-site-packages` and `--no-deps`;
it is not a second pip installation of those pins. Compatibility therefore
requires importing and analyzing data with the actual installed runtime.

`pip check` passes in the isolated pip environment. In the Homebrew venv it
reports the expected differences: NumPy 2.5.4 does not satisfy the upstream
2.5.1 pin, and Homebrew's `opencv` is not the `opencv-python-headless` pip
distribution. This packaging metadata difference remains explicit; assertions
and pins were not weakened to hide it. All 27 application/resource files in the
two installed packages have identical SHA-256 hashes (excluding bytecode).
No analysis algorithm, CLI default, CSV schema, or existing pip CI was changed.

## Installation and synthetic checks

The unmodified installed 8.0.1 venv reproduced `ModuleNotFoundError: cv2`.
A dry run with the corrected Formula selected only SpotScanner for upgrade.
The actual release archive was then installed with:

```bash
HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 \
HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1 \
brew install --build-from-source KentoYana/tap/spotscanner
brew test --verbose KentoYana/tap/spotscanner
```

Homebrew requires a registered tap rather than an arbitrary Formula path.
For this local verification, the corrected Formula was copied into a temporary
branch of the already-installed tap after confirming that checkout was clean.
That installed-tap checkout was restored to its clean original `main` after
validation so normal Homebrew updates remain possible. The corrected installed
keg is retained; the development tap remains the reviewable source of changes.

The installation upgraded 8.0.1 to 8.0.1_1. No other formula was upgraded and
no package cleanup/uninstall was performed. The old SpotScanner keg was retained.
`brew test` passed with both modes and checked:

- Python 3.15 and imports from the actual Homebrew NumPy/OpenCV directories.
- Packaged marker detection and successful installed CLI analysis.
- CSV headers, default threshold 7, complete ordered coordinates, and finite
  0–100 values: 25 pipette / 97 replicator CSV lines including the header.
- Exact reference values for every one of the 24 / 96 synthetic cells,
  independently cross-checked with the pinned pip environment.
- Successful PNG decoding and dimensions 574 × 774 pixels.

Homebrew style checks passed. The pip environment passed all 17 tests
(12 existing tests plus 5 regression-tool tests) and `pip check`.

## Real-image regression

Both installed distributions analyzed all available compatible cases, using
the originally recorded thresholds. Results below apply to both runtimes:

| Mode | Images | Cells | Archived numeric comparisons | Exact differences from v7 | Maximum difference from v7 | Existing envelope | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pipette | 304 | 7,296 | 7,285 | 1,643 | 0.12 | 0.12 | 0 |
| replicator | 42 | 4,032 | 4,032 | 1,353 | 0.17 | 0.17 | 0 |

Differences/envelopes are absolute percentage points on the 0–100 output scale.
Mean absolute differences were 0.0046698696 for pipette and 0.0063293651 for
replicator. These counts and distributions match the previously documented
pip runtime results; no tolerance was increased for this fix. All 346
diagnostic PNGs passed decoding, binary-content, and dimension checks in both
environments. One real output from each mode was also visually inspected.

Direct current-pip versus current-Homebrew comparison was stricter: all
**11,328 numerical values**, image identities, thresholds, row/column metadata,
and **346 decoded PNGs** matched exactly. Only analysis timestamps were ignored.
This includes the 11 cells whose archived pipette references were `NA`.

Fixture provenance and exclusions:

- Pipette: `KentoYana/Resource_Article_DDT_hH3-K4R_01` at clean commit
  `baf742c9541196105e3336a93ff10ec6cf13faf2`. The analyzed images and result
  CSVs are unchanged from the documented baseline commit
  `b470359d1cc46898509d6cd294457afb6b609844`. Eleven archived `NA` values were
  excluded only from the historical numeric comparison.
- Replicator: the existing extracted `Stamp-data` collection, with the four
  documented image aliases. The 102 old binary-schema CSVs remain explicitly
  excluded because they do not measure the same quantity. The original ZIP's
  checksum was not reverified because only the extracted collection was found.
- Original image and baseline repositories were not modified. Work directories
  contain image symlinks and newly generated results.

The compact [validation record](validation/homebrew-2026-10-31.json) preserves
runtime details, counts, complete difference histograms, and report hashes.
The full reports and per-image outputs remain under
`/tmp/spotscanner-validation/`. To repeat a Homebrew run with fresh output
directories, use the installed-command procedure in
[the regression guide](v7-regression.md), including the replicator aliases and
the unchanged 0.12/0.17 historical envelopes. A pip baseline can be run with
the same command by pointing `--executable` to an isolated pinned venv's
`bin/spotscanner`; it must not share Homebrew site packages.

## Continuous detection and remaining limits

The tap workflow runs on macOS for Formula/workflow changes, every January 1
and July 1 at 03:23 UTC (12:23 JST), and on manual dispatch. It refreshes
Homebrew metadata, registers the checked-out tap commit and verifies its identity, compares the
Python dependencies of SpotScanner and OpenCV, installs current dependencies
and the Formula, then imports the installed runtime and runs both-mode
`brew test`. Environment details and logs are retained as Actions artifacts.
It performs no global Homebrew upgrade or cleanup.

The workflow YAML and shell blocks were checked locally, and the Python
compatibility guard was checked against both matching and mismatching metadata.
GitHub-hosted validation subsequently passed on 2026-10-31:

- [Application PR CI](https://github.com/KentoYana/SpotScanner/actions/runs/41175030183)
  at `ab6c9d045eaffd1e4a9ea1281960576d89f50138`: all five jobs passed
  (Linux Python 3.12/3.13/3.14, macOS Python 3.14, wheel/sdist build).
  The corresponding [push run](https://github.com/KentoYana/SpotScanner/actions/runs/41174960107)
  also passed.
- [Homebrew PR CI](https://github.com/KentoYana/homebrew-tap/actions/runs/41175213028)
  at `362c35667e2f8885e85b15bb5d90326b75b0ab8c`: the exact-checkout guard,
  Python dependency guard, installation, runtime imports, both-mode `brew test`,
  and artifact upload passed on arm64 macOS 26.6.2. The installed runtime was
  Python 3.15.2, NumPy 2.5.4, and OpenCV 5.0.0. The corresponding
  [push run](https://github.com/KentoYana/homebrew-tap/actions/runs/41175212766)
  also passed. No CI failure required a code change or rerun.

Scheduled runs use the default branch. The scheduled synthetic gate detects
import/ABI failures and drift on its fixture; it does not run the external
real-image collections. Future dependency changes still require investigation
and a real-image regression before accepting changed reference values.

Full real-image validation was on arm64 macOS 26.7.2; the hosted Homebrew
synthetic tests additionally passed on arm64 macOS 26.6.2. This does not establish compatibility
for every CPU/OS, image collection, or future dependency release. The pip
version assertions remain a pip-specific gate; use the Formula tests for the
Homebrew distribution.

After the change is published to the tap's default branch, existing users run:

```bash
brew update
brew upgrade KentoYana/tap/spotscanner
brew test KentoYana/tap/spotscanner
```

`spotscanner --version` continues to report 8.0.1;
`brew list --versions spotscanner` includes 8.0.1_1. Local validation logs and retained per-image
outputs are under `/tmp/spotscanner-validation/` on the validation machine.
