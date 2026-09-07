"""The sensitive-path guard must protect fresh CI checkouts as well as commits."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

GUARD = Path(__file__).resolve().parents[1] / "bin/check-sensitive-files"


class SensitivePathTests(unittest.TestCase):
    def test_all_mode_rejects_existing_tracked_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin").mkdir()
            shutil.copy2(GUARD, root / "bin/check-sensitive-files")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "private").mkdir()
            (root / "private/fixture.txt").write_text("synthetic fixture only\n")
            subprocess.run(["git", "add", "private/fixture.txt"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=CI Fixture", "-c",
                            "user.email=ci@example.invalid", "commit", "-q", "-s",
                            "-m", "test: add synthetic tracked fixture"], cwd=root, check=True)
            subprocess.run(["bash", "bin/check-sensitive-files"], cwd=root, check=True)
            result = subprocess.run(["bash", "bin/check-sensitive-files", "--all"],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("private/fixture.txt", result.stderr)

    def test_template_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin").mkdir()
            shutil.copy2(GUARD, root / "bin/check-sensitive-files")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".env.example").write_text("EXAMPLE=\n")
            subprocess.run(["git", "add", ".env.example"], cwd=root, check=True)
            subprocess.run(["bash", "bin/check-sensitive-files", "--all"], cwd=root, check=True)
