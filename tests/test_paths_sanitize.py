"""Project slugs must match Cursor's folder names and stay off other drives."""

import unittest
from pathlib import PureWindowsPath

from cursor_saves.paths import sanitize_project_path


class SanitizeProjectPathTests(unittest.TestCase):
    def test_unix_path(self):
        self.assertEqual(
            sanitize_project_path("/Users/callum/Desktop/Projects/myrepo"),
            "Users-callum-Desktop-Projects-myrepo",
        )

    def test_windows_drive_colon_is_removed(self):
        self.assertEqual(
            sanitize_project_path(r"c:\Programacao\cursaves"),
            "c-Programacao-cursaves",
        )

    def test_workspace_file_on_another_drive(self):
        slug = sanitize_project_path(
            r"W:\home\thiago\dev\analisefacildev\workspace.code-workspace"
        )
        self.assertEqual(
            slug,
            "W-home-thiago-dev-analisefacildev-workspace-code-workspace",
        )
        parent = PureWindowsPath(r"C:\Users\thiago\.cursor\projects")
        joined = parent / slug / "agent-transcripts"
        self.assertEqual(joined.drive, "C:")
        self.assertEqual(joined, parent / slug / "agent-transcripts")

    def test_unc_and_wsl_paths(self):
        self.assertEqual(
            sanitize_project_path(r"\\1.1.1.100\services\oinvestidor"),
            "1-1-1-100-services-oinvestidor",
        )
        self.assertEqual(
            sanitize_project_path(r"\\wsl$\Ubuntu\home\thiago\dev\metadminjs"),
            "wsl-Ubuntu-home-thiago-dev-metadminjs",
        )


if __name__ == "__main__":
    unittest.main()
