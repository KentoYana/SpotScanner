# Release and Homebrew maintenance

SpotScanner's live [Formula](https://github.com/KentoYana/homebrew-tap/blob/main/Formula/spotscanner.rb)
and [Homebrew workflow](https://github.com/KentoYana/homebrew-tap/blob/main/.github/workflows/spotscanner.yml)
belong to `KentoYana/homebrew-tap`. This repository owns the Python package,
tests, regression tool, documentation, and release archives. Maintain the live
Formula in the tap; do not copy its implementation into this guide.

This guide covers preparation of 8.0.2 and subsequent releases. Completing a
checklist or changing a version string is not evidence that the new artifacts
have passed validation. The [2026-10-31 validation report](homebrew-validation.md)
and [machine-readable record](validation/homebrew-2026-10-31.json) describe
**8.0.1_1**, including its exact comparison with the pinned pip installation.
They are historical evidence, not an 8.0.2 test result.

## Two dependency policies

The pip package retains the exact dependencies in `pyproject.toml`:

- `numpy==2.5.1`
- `opencv-python-headless==5.0.0.93` (`cv2.__version__` reports `5.0.0`)

These pins preserve the validated numerical runtime. The application's pip CI
and exact dependency-version assertions remain in place. A dependency change
requires its own compatibility evidence; do not widen pins or assertions just
to make the Homebrew environment pass pip-specific checks.

Homebrew instead supplies `numpy`, `opencv`, and a matching versioned Python,
with `python-setuptools` available for the build. The current Formula selects
**Python 3.15**, matching Homebrew OpenCV's Python bindings. Its dependency
declaration, venv interpreter, and runtime assertions must agree. Recheck the
current OpenCV dependency metadata before every Formula update, and use the
declared interpreter's matching site packages for Homebrew's compiled OpenCV
bindings.

The Formula creates its `libexec` venv with `--system-site-packages`, verifies
NumPy/OpenCV imports during installation, and installs the source with
`--no-deps --no-build-isolation`. It exposes the installed console command in
`bin`. Do not install replacement pip libraries into that venv. Homebrew's
versions may differ from the pip pins, and native OpenCV is not the
`opencv-python-headless` pip distribution. Consequently `pip check` in this
shared environment is not the Homebrew compatibility gate; actual imports,
both-mode Formula tests, and numerical regression provide that evidence.

## Prepare and validate release artifacts

1. Start from a work branch with existing changes accounted for. Update the
   application version, current-release documentation, and version assertions
   together. Keep historical validation records labeled with their tested
   versions. Do not change algorithms, defaults, CSV schemas, or numerical
   reference values as part of a packaging release.
2. Run the complete pip test suite in an isolated environment with the declared
   dependencies. Run `python -m pip check` there. Preserve the existing Linux
   and macOS pip CI matrix.
3. Build both artifacts into a fresh output directory with `python -m build`.
   Inspect the wheel's `METADATA`, entry point, version, Python requirement,
   and dependency pins. Inspect the sdist's `PKG-INFO` and build configuration
   for the same values. Verify that both contain all packaged markers and
   templates. The sdist must also include `tools/compare_v7_results.py`, the
   Markdown guides, and `docs/validation/*.json`; inspect archive members rather
   than assuming that a successful build included them.
4. Install the wheel and the sdist separately into fresh pip venvs. From outside
   the checkout, use each installed command to check imports, help/version,
   packaged resources, and synthetic pipette and replicator analyses. Check
   diagnostic PNG decoding/dimensions and CSV headers, ordered coordinates,
   row counts, and all expected numerical values. `--version` alone does not
   load the analysis libraries.
5. For numerical validation, use the installed-command mode described in
   [the regression guide](v7-regression.md):

   ```bash
   python tools/compare_v7_results.py /path/to/Resource_Article_DDT_hH3-K4R_01 \
     --executable /path/to/release-venv/bin/spotscanner \
     --tolerance 0.12 --report /tmp/spotscanner-release-pipette.json
   ```

   Run replicator cases with the documented aliases and existing 0.17 envelope
   as well. Retain runtime provenance and full difference statistics. Keep
   synthetic success separate from real-image evidence, and record unavailable
   fixtures, archived `NA` cells, and incompatible legacy schemas explicitly.
   For unchanged analysis code, compare current pip and Homebrew outputs
   directly, ignoring only timestamps, including decoded diagnostic pixels.
6. Obtain fresh successful application PR CI for the release changes and verify
   the resulting default-branch CI after merge. Record the tested commits and
   artifact checksums. Earlier 8.0.1 CI does not validate an 8.0.2 artifact.

## Publish an immutable release and update the tap

After release authorization and the required checks pass, create an annotated
tag such as `v8.0.2` at the intended release commit. Verify that the tag, source
archive, wheel, and recorded version describe the same source. Publish the
tested wheel and sdist as GitHub release assets, record their SHA-256 checksums,
and verify the uploaded assets against those checksums. Do not replace an
already published archive under the same release URL; publish a new version
when the archive's contents must change.

In the tap's work branch, update the Formula's release-asset URL and SHA-256 to
the verified sdist. Remove the previous `revision` when advancing the upstream
version: `8.0.1_1` becomes `8.0.2`, not `8.0.2_1`. A packaging-only correction
that retains the same upstream version instead increments `revision`, allowing
existing users to receive it through `brew upgrade`.

Register the checked-out tap commit on a clean macOS test machine and verify
that Homebrew is reading that Formula, rather than an older installed tap
checkout. Refresh dependency metadata, then run:

```bash
brew audit --strict --online KentoYana/tap/spotscanner
brew install --build-from-source KentoYana/tap/spotscanner
brew test --verbose KentoYana/tap/spotscanner
```

Use a fresh installation or explicitly verify the upgrade/reinstallation path
when a prior keg is present. Record the actual installed Python, NumPy, OpenCV,
package paths, and Formula version. Run the installed release against the
available real-image baselines and pinned pip reference. Investigate numerical
drift before changing any reference or tolerance. Limit dependency changes to
those needed by the Formula; a global Homebrew upgrade or package cleanup is
not part of release verification.

Require fresh tap PR CI for the new URL/checksum and verify the corresponding
default-branch run after merge. The application and tap checks cover separate
distribution paths; success in one does not substitute for success in the
other. Record release-specific results only after those runs finish.

## Continuous dependency checks

The tap workflow installs the checked-out Formula on macOS, checks that its
Python dependency matches current OpenCV metadata, records actual runtime
imports, and runs both-mode `brew test`. Logs are uploaded as Actions artifacts.
It runs for Formula/workflow changes on pushes and pull requests, supports
manual `workflow_dispatch`, and runs **twice yearly: January 1 and July 1 at
03:23 UTC (12:23 JST)**. Its cron expression is `23 3 1 1,7 *`; this is a
semiannual schedule, not a weekly check. Scheduled runs use the default branch.

Use manual dispatch after a relevant Homebrew dependency update or before a
release. The hosted gate detects import failures and numerical drift on its
synthetic fixture; it does not include the external real-image collections.
Reproduce and investigate failures using the recorded runtime versions, then
repeat the real-image regression before accepting changed dependencies.

## User installation and updates

```bash
brew install KentoYana/tap/spotscanner
```

After the updated Formula reaches the tap's default branch, existing users run:

```bash
brew update
brew upgrade KentoYana/tap/spotscanner
brew test KentoYana/tap/spotscanner
```

`spotscanner --version` reports the upstream application version;
`brew list --versions spotscanner` additionally shows any Formula revision.
