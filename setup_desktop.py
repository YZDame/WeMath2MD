"""cx_Freeze build config for desktop installers.

Windows: python setup_desktop.py bdist_msi
macOS:   python setup_desktop.py bdist_dmg
"""

from __future__ import annotations

import os
import re
import sys

from cx_Freeze import Executable, setup


def _version() -> str:
    raw_version = os.environ.get("WEMATH2MD_VERSION", "1.0.0").strip()
    version = raw_version[1:] if raw_version.startswith("v") else raw_version
    if not re.fullmatch(r"\d+(?:\.\d+)*(?:[a-zA-Z0-9_.+-]*)?", version):
        raise ValueError(f"Invalid WEMATH2MD_VERSION: {raw_version!r}")
    return version


def _executable_base() -> str | None:
    if sys.platform == "win32":
        return "Win32GUI"
    return None


build_exe_options = {
    "packages": ["flask", "requests", "bs4", "dotenv", "tenacity", "tqdm"],
    "include_files": [("templates", "templates")],
}

if sys.platform == "win32":
    build_exe_options["include_msvcr"] = True

executables = [
    Executable(
        "desktop_client.py",
        target_name="WeMath2MD",
        base=_executable_base(),
    )
]

setup(
    name="WeMath2MD",
    version=_version(),
    description="WeMath2MD Desktop Client",
    options={"build_exe": build_exe_options},
    executables=executables,
)
