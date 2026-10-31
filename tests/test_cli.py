import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import spotscanner
from spotscanner import cli


PACKAGE_ROOT = Path(spotscanner.__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
RESOURCE_ROOT = PACKAGE_ROOT / "resources"
REGRESSION_TOOL = PROJECT_ROOT / "tools" / "compare_v7_results.py"


def run_module(*arguments, cwd=None):
    environment = os.environ.copy()
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    if existing_pythonpath:
        environment["PYTHONPATH"] += os.pathsep + existing_pythonpath
    return subprocess.run(
        [sys.executable, "-m", "spotscanner", *arguments],
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


class PackageTests(unittest.TestCase):
    def test_package_import_and_release_version(self):
        self.assertEqual(spotscanner.__version__, "8.0.2")

    def test_packaged_resources_exist(self):
        self.assertTrue((RESOURCE_ROOT / "marker" / "Marker16.png").is_file())
        self.assertTrue((RESOURCE_ROOT / "template" / "marker.pdf").is_file())
        self.assertTrue((RESOURCE_ROOT / "template" / "spotscanner.1").is_file())

    def test_analysis_dependency_versions(self):
        import cv2
        import numpy as np

        self.assertEqual(np.__version__, "2.5.1")
        self.assertEqual(cv2.__version__, "5.0.0")

    def test_v7_regression_tool_help(self):
        result = subprocess.run(
            [sys.executable, REGRESSION_TOOL, "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Resource_Article_DDT_hH3-K4R_01", result.stdout)
        self.assertIn("--mode {pipette,replicator}", result.stdout)
        self.assertIn("--image-alias", result.stdout)


class CliTests(unittest.TestCase):
    def test_help(self):
        result = run_module("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: spotscanner", result.stdout)

    def test_version(self):
        result = run_module("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SpotScanner v8.0.2", result.stdout)

    def test_console_script(self):
        executable = Path(sys.executable).with_name("spotscanner")
        if not executable.is_file():
            self.skipTest("console script is only present after package installation")
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SpotScanner v8.0.2", result.stdout)

    def test_manual_output_uses_packaged_resource(self):
        result = run_module("--output", "manual")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SPOTSCANNER(1)", result.stdout)

    def test_marker_pdf_uses_macos_open(self):
        expected_pdf = RESOURCE_ROOT / "template" / "marker.pdf"
        with mock.patch.object(cli.sys, "platform", "darwin"):
            with mock.patch.object(cli.subprocess, "run") as run:
                with self.assertRaises(SystemExit) as exit_context:
                    cli.main(["--output", "marker-pdf"])
        self.assertIsNone(exit_context.exception.code)
        run.assert_called_once_with(["open", str(expected_pdf)], check=False)

    def test_citation_output(self):
        with tempfile.TemporaryDirectory() as workdir:
            result = run_module("--output", "citation", cwd=workdir)
            self.assertEqual(result.returncode, 0, result.stderr)
            citation = Path(workdir, "spotscanner.bib").read_text(encoding="utf-8")
            self.assertIn("version 8.0.2", citation)


class AnalysisSmokeTests(unittest.TestCase):
    def test_pipette_single_image(self):
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            self.skipTest(f"analysis dependencies are unavailable: {error}")

        marker = cv2.imread(str(RESOURCE_ROOT / "marker" / "Marker16.png"))
        self.assertIsNotNone(marker)

        canvas = np.full((800, 1000, 3), 255, dtype=np.uint8)
        canvas[50:210, 50:210] = marker
        canvas[600:760, 800:960] = marker
        cv2.circle(canvas, (350, 350), 60, (0, 0, 0), -1)

        with tempfile.TemporaryDirectory() as workdir:
            image_path = Path(workdir, "plate.jpg")
            self.assertTrue(cv2.imwrite(str(image_path), canvas))

            result = run_module(
                "--analyze",
                "pipette",
                "--single",
                image_path.name,
                cwd=workdir,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Marker16 Match!!!", result.stdout)

            converted_path = Path(workdir, "plate_converted.png")
            csv_path = Path(workdir, "plate_results.csv")
            self.assertTrue(converted_path.is_file())
            self.assertTrue(csv_path.is_file())

            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))
            self.assertEqual(
                rows[0],
                ["Time", "Image", "Threshold", "row", "column", "Colony"],
            )
            self.assertEqual(len(rows), 25)
            self.assertEqual({row[2] for row in rows[1:]}, {"7"})
            self.assertEqual({row[3] for row in rows[1:]}, {"1", "2", "3", "4"})

    def test_replicator_single_image(self):
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            self.skipTest(f"analysis dependencies are unavailable: {error}")

        marker = cv2.imread(str(RESOURCE_ROOT / "marker" / "Marker16.png"))
        self.assertIsNotNone(marker)

        canvas = np.full((800, 1000, 3), 255, dtype=np.uint8)
        canvas[50:210, 50:210] = marker
        canvas[600:760, 800:960] = marker
        cv2.circle(canvas, (350, 350), 60, (0, 0, 0), -1)

        with tempfile.TemporaryDirectory() as workdir:
            image_path = Path(workdir, "replicator.jpg")
            self.assertTrue(cv2.imwrite(str(image_path), canvas))

            result = run_module(
                "--analyze",
                "replicator",
                "--single",
                image_path.name,
                cwd=workdir,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Marker16 Match!!!", result.stdout)

            csv_path = Path(workdir, "replicator_results.csv")
            self.assertTrue(csv_path.is_file())
            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))
            self.assertEqual(len(rows), 97)
            self.assertEqual({row[3] for row in rows[1:]}, set(map(str, range(1, 9))))
            self.assertEqual({row[4] for row in rows[1:]}, set(map(str, range(1, 13))))


if __name__ == "__main__":
    unittest.main()
