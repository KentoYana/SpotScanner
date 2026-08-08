# SpotScanner

SpotScanner is a command-line tool for quantitative analysis of fungal
spot-test plates. It detects a printed marker, segments the image into a fixed
grid, measures colony growth, and writes CSV data and diagnostic images.

SpotScanner 8.0 is distributed as a standard Python package with a generated
`spotscanner` command. The package version for this release is `8.0.0`.

## Features

- Replicator mode: 8 × 12 matrix
- Pipette mode: 4 × 6 matrix
- Marker-based image alignment and normalization
- `*_converted.png` diagnostic images
- `*_results.csv` measurements
- Printable marker, text manual, and BibTeX citation helpers

The 8.0 migration changes packaging and execution, not the image-analysis
algorithm.

## Requirements

- Python 3.12, 3.13, or 3.14
- NumPy 2.5.1
- OpenCV Python headless 5.0.0.93 (`cv2.__version__` reports `5.0.0`)

Python 3.12 is the minimum because the selected NumPy 2.5.1 release requires
Python 3.12 or newer. NumPy and OpenCV are pinned to the versions used for the
full pipette and replicator regression runs, so ordinary pip installations do
not silently change the numerical runtime. The package metadata installs these
exact dependencies automatically.

## Installation

### From a source checkout

Use a Python interpreter managed by pyenv rather than the system Python. For
example, to use Python 3.14 without changing pyenv's global selection:

```bash
pyenv install -s 3.14.6
PYENV_VERSION=3.14.6 pyenv exec python -m pip install .
PYENV_VERSION=3.14.6 pyenv exec spotscanner --help
```

For development, install in editable mode:

```bash
PYENV_VERSION=3.14.6 pyenv exec python -m pip install -e .
PYENV_VERSION=3.14.6 pyenv exec python -m unittest discover -s tests -v
```

Alternatively, `pyenv local 3.14.6` can select the interpreter for a checkout.
Do not commit a developer-specific `.python-version` change unless the project
intentionally decides to pin that patch release.

The `spotscanner` executable is generated from the Python packaging entry
point. The 7.x shell wrapper is no longer required. The following compatibility
form remains supported:

```bash
python -m spotscanner --help
```

`SPOTSCANNER_ROOT` and the legacy `SPOTSCANNER` variable remain available for
old portable layouts. When unset, 8.x uses marker and template resources shipped
inside the installed Python package.

### Homebrew status

The Homebrew formula is maintained separately in the project tap. After the
formula is added to the tap, the installation commands are:

```bash
brew install KentoYana/tap/spotscanner
```

or:

```bash
brew tap KentoYana/tap
brew install spotscanner
```

The formula should live in the separate `KentoYana/homebrew-tap` repository,
not in this application repository. This keeps Homebrew release metadata and
checksums separate from the platform-neutral Python package.

Before publishing the formula, the project needs a final versioned release
archive, its SHA-256 checksum, and a formula test that runs at least
`spotscanner --version`. The formula should use Homebrew-managed Python and
dependencies in an isolated installation under the formula prefix; it must not
write to or depend on the user's system Python, pyenv, or global pip state.
Requirements for a future `homebrew/core` submission, including stable release
history and checksummed Python resources, should be handled after the tap has
been exercised successfully.

See the
[Homebrew distribution plan](https://github.com/KentoYana/spotscanner/blob/main/docs/homebrew.md)
for the release prerequisites, dependency model, Formula sketch, and
`homebrew/core` path.

## Command-line usage

```text
spotscanner [-v] [-e] [-r]
            [-o {manual,marker-pdf,marker-tex,citation}]
            [-a {pipette,replicator}]
            [-s SINGLE | -m]
            [-t 1..10]
```

General options:

- `-h`, `--help`: show command help.
- `-v`, `--version`: show the version and citation.
- `-e`, `--example`: show short analysis examples.
- `-r`, `--readme`: view the packaged text manual with `less`, falling back to
  standard output when `less` is unavailable.
- `-o manual`: print the text manual.
- `-o marker-pdf`: open the printable marker with the platform file viewer.
- `-o marker-tex`: write `marker.tex` in the current directory.
- `-o citation`: write `spotscanner.bib` in the current directory.

Analysis options:

- `-a pipette`: analyze a 4 × 6 plate.
- `-a replicator`: analyze an 8 × 12 plate.
- `-s IMAGE`: analyze one JPEG image.
- `-m`: analyze all `*.jpg`, `*.JPG`, and `*.jpeg` images in the current
  directory.
- `-t N`: set marker recognition threshold from 1 to 10 (default: 7,
  interpreted as `N / 10`).

### Analyze one image

```bash
spotscanner -a pipette -s plate1.jpg
```

This creates:

- `plate1_converted.png` for visual quality control
- `plate1_results.csv` with `Time, Image, Threshold, row, column, Colony`

Always inspect the converted image to confirm that the intended region was
detected.

### Analyze a directory

```bash
spotscanner -a replicator -m
```

Each JPEG is processed and the outputs are grouped in timestamped directories:

```text
converted_YYYY-MM-DD_HH-MM-SS/
results_YYYY-MM-DD_HH-MM-SS/
```

### Marker and citation resources

```bash
spotscanner -o marker-pdf
spotscanner -o marker-tex
spotscanner -o manual | less
spotscanner -o citation
```

## Testing and CI

Run the local smoke and analysis tests with:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions tests Python 3.12–3.14 on Linux and Python 3.14 on macOS. It
checks package import, both CLI launch paths, packaged resources, help/version,
auxiliary output, and a small synthetic-image analysis. A separate job builds
the wheel and source distribution.

### SpotScanner 7 result regression

The published manuscript resource repository contains original plate images
and their SpotScanner 7.0.0 CSV results. It is intentionally kept outside this
repository because it is large. From a SpotScanner source checkout, rerun every
archived image with the current source and compare all colony values after
two-decimal rounding:

```bash
git clone https://github.com/KentoYana/Resource_Article_DDT_hH3-K4R_01.git
PYENV_VERSION=3.14.6 pyenv exec python tools/compare_v7_results.py \
  /path/to/Resource_Article_DDT_hH3-K4R_01 \
  --report /tmp/spotscanner-v7-regression.json
```

The comparison ignores the run timestamp but requires identical image names,
thresholds, row/column coordinates, and `Colony` values by default. Use
`--limit N` for a quick sample or `--tolerance VALUE` only when an explicitly
documented numerical tolerance has been approved.

The full baselines, dependency-version comparison, and interpretation are
documented in
[SpotScanner 7 numerical regression](docs/v7-regression.md). The observed
cross-generation compatibility envelopes are 0.12 percentage points for the
304-image pipette dataset and 0.17 percentage points for the 42-image
replicator dataset.

## License

SpotScanner is licensed under the MIT License.
