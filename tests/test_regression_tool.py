from decimal import Decimal
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import venv

from tools import compare_v7_results as regression


class InstalledRuntimeTests(unittest.TestCase):
    def test_installed_cli_and_metadata_use_its_environment(self):
        # A separate install with distinct version strings proves that neither
        # the checkout nor an inherited PYTHONPATH can supply report metadata.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            environment = root / "installed"
            venv.EnvBuilder(with_pip=False).create(environment)
            python = environment / "bin/python"
            site = Path(subprocess.check_output(
                [python, "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
                text=True,
            ).strip())
            for module, version in (("spotscanner", "8.0.1-installed"),
                                    ("numpy", "numpy-installed"),
                                    ("cv2", "opencv-installed")):
                (site / f"{module}.py").write_text(f"__version__ = {version!r}\n")
            executable = environment / "bin/spotscanner"
            executable.write_text(
                f"#!{python}\nimport spotscanner\nprint(spotscanner.__version__)\n"
            )
            executable.chmod(0o755)
            with mock.patch.dict(os.environ, {"PYTHONPATH": str(regression.PROJECT_ROOT),
                                              "PYTHONHOME": "/nonexistent-python-home",
                                              "SPOTSCANNER_ROOT": "/external-resources",
                                              "SPOTSCANNER": "/legacy-resources"}):
                runtime = regression.select_runtime(executable)
            self.assertEqual(runtime.command, (str(executable),))
            self.assertEqual(runtime.python, str(python))
            self.assertEqual(runtime.metadata["execution_mode"], "installed")
            self.assertEqual(runtime.metadata["spotscanner_version"], "8.0.1-installed")
            self.assertEqual(runtime.metadata["numpy_version"], "numpy-installed")
            self.assertEqual(runtime.metadata["opencv_version"], "opencv-installed")
            self.assertTrue(Path(runtime.metadata["spotscanner_module"]).is_relative_to(site))
            self.assertNotIn("PYTHONPATH", runtime.environment)
            self.assertNotIn("PYTHONHOME", runtime.environment)
            self.assertNotIn("SPOTSCANNER_ROOT", runtime.environment)
            self.assertNotIn("SPOTSCANNER", runtime.environment)
            result = subprocess.run(runtime.command, cwd=root, env=runtime.environment,
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), "8.0.1-installed")

    def test_ambiguous_wrapper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "spotscanner"
            script.write_text("#!/usr/bin/env python3\n")
            with self.assertRaisesRegex(ValueError, "absolute Python shebang"):
                regression.select_runtime(script)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.rows = tuple({"Time": "baseline", "Image": "plate", "Threshold": "7",
                           "row": "1", "column": str(column), "Colony": "10.00"}
                          for column in (1, 2))
        self.case = regression.Case(1, Path("plate_results.csv"), Path("plate.jpg"), 7, self.rows)

    def test_envelope_does_not_hide_exact_difference_statistics(self):
        generated = tuple({**row, "Time": "today", "Colony": value}
                          for row, value in zip(self.rows, ("10.03", "10.12")))
        differences = regression.compare_rows(self.case, generated, Decimal("0"))
        runtime = regression.Runtime(("/installed/spotscanner",), "/installed/python", {},
                                     {"execution_mode": "installed", "spotscanner_version": "8.0.1"})
        report = regression.make_report(
            Path("/tmp"), [self.case], [regression.CaseResult(self.case, differences)],
            Decimal("0.12"), "pipette", Path("/tmp"), [], {}, runtime,
            {"verified": [], "errors": []},
        )
        self.assertEqual(report["different_cells"], 0)
        self.assertEqual(report["exact_different_cells"], 2)
        self.assertEqual(report["max_absolute_difference"], 0.12)
        self.assertEqual(report["absolute_difference_counts"], {"0.03": 1, "0.12": 1})
        self.assertEqual(report["mean_absolute_difference"], 0.075)
        self.assertIsNone(report["spotscanner_commit"])

    def test_nonfinite_and_out_of_range_results_fail_even_for_archived_na(self):
        case = regression.Case(1, Path("reference.csv"), Path("image.jpg"), 7,
                               ({**self.rows[0], "Colony": "NA"},))
        for value in ("NaN", "Infinity", "-0.01", "100.01"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                regression.compare_rows(case, ({**self.rows[0], "Colony": value},), Decimal("0"))

    def test_missing_diagnostic_is_reported(self):
        runtime = regression.select_runtime(None)
        with tempfile.TemporaryDirectory() as directory:
            report = regression.validate_diagnostic_images(runtime, [self.case], Path(directory))
        self.assertEqual(report["verified"], [])
        self.assertEqual(len(report["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
