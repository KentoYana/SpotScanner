# Homebrew distribution plan

SpotScanner's Formula should be maintained in the separate
`KentoYana/homebrew-tap` repository. The application repository should contain
portable Python packaging, tests, and release archives, but not a second copy of
the live Formula.

## Release prerequisites

Before publishing a Formula:

1. Finish validation while the Python version is `8.0.0.dev0`.
2. Change the package version to `8.0.0` only when the release is ready.
3. Build and test both the wheel and source distribution.
4. Create the signed or annotated `v8.0.0` tag only after release approval.
5. Publish a stable GitHub release archive and record its SHA-256 checksum.
6. Add `Formula/spotscanner.rb` to `KentoYana/homebrew-tap`.
7. Run `brew audit --strict --online KentoYana/tap/spotscanner`,
   `brew install --build-from-source KentoYana/tap/spotscanner`, and
   `brew test KentoYana/tap/spotscanner` on a clean macOS system.

No tag or Formula is created by the 8.0 development branch itself.

## Dependency model

The Formula should declare Homebrew dependencies rather than use the user's
Python, pyenv, or pip environment. The selected SpotScanner 8 runtime is:

- `python@3.14` (3.14.6 when this plan was validated)
- `numpy` 2.5.1
- `opencv` 5.0.0
- `python-setuptools` 83.0.0 as a build dependency

These Homebrew versions currently match the runtime used for the full pipette
and replicator regressions. The Formula should declare `numpy` directly because
SpotScanner imports it directly, even though `opencv` also depends on it. Since
Homebrew dependencies can advance independently, every Formula revision must
rerun the numerical release gates and update this plan if the resolved runtime
no longer matches.

Install SpotScanner below the Formula's `libexec` prefix with access to the
declared Homebrew Python site packages, then link only the generated
`spotscanner` command into `bin`. Installation must use `--no-deps` and must not
download anything during the Formula build.

The exact technique must be retested against the Homebrew version used when the
Formula is published. Homebrew currently documents
`virtualenv_install_with_resources` as private to Homebrew's own repository, so
a third-party tap should not assume that helper is a stable API. An explicit
`python@3.14 -m venv --system-site-packages` under `libexec`, followed by a
local, dependency-free pip install, is the leading tap implementation.

## Draft Formula shape

This is a planning sketch, not an installable Formula. The URL and checksum are
intentionally absent until a final release exists.

```ruby
class Spotscanner < Formula
  desc "Quantitative analysis of fungal spot-test plates"
  homepage "https://github.com/KentoYana/spotscanner"
  url "RELEASE_ARCHIVE_URL"
  sha256 "RELEASE_ARCHIVE_SHA256"
  license "MIT"

  depends_on "python-setuptools" => :build
  depends_on "numpy"
  depends_on "opencv"
  depends_on "python@3.14"

  def install
    python = Formula["python@3.14"].opt_bin/"python3.14"
    system python, "-m", "venv", "--system-site-packages", libexec
    system libexec/"bin/python", "-m", "pip", "install",
           "--no-deps", "--no-build-isolation", "."
    bin.install_symlink libexec/"bin/spotscanner"
  end

  test do
    assert_match "SpotScanner v#{version}", shell_output("#{bin}/spotscanner --version")
    assert_match "usage: spotscanner", shell_output("#{bin}/spotscanner --help")
  end
end
```

Validate the final syntax against the current
[Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook) and
[Python virtualenv API documentation](https://docs.brew.sh/rubydoc/Language/Python/Virtualenv.html).

## Tap installation commands

The unambiguous installation command is intended to be:

```bash
brew install KentoYana/tap/spotscanner
```

Current Homebrew releases apply an explicit trust model to taps. If a short
Formula name is desired after tapping, follow the then-current
[tap trust instructions](https://docs.brew.sh/Taps); fully qualified Formula
installation avoids ambiguity with `homebrew/core`.

## Path toward homebrew/core

After the tap has a stable release history:

- keep release URLs and checksums immutable;
- demonstrate usage beyond the repository author;
- use only declared Homebrew dependencies and supported platform facilities;
- ensure Formula tests exercise real installed behavior;
- follow the current
  [acceptable formula requirements](https://docs.brew.sh/Acceptable-Formulae);
- submit the Formula to `homebrew/core` separately from SpotScanner source
  changes.
