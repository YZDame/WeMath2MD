"""cx_Freeze build config for desktop installers.

Windows: python setup_desktop.py bdist_msi
macOS:   python setup_desktop.py bdist_dmg
"""

from cx_Freeze import Executable, setup

build_exe_options = {
    "packages": ["flask", "requests", "bs4", "dotenv", "tenacity", "tqdm"],
    "include_files": ["templates"],
    "include_msvcr": True,
}

executables = [
    Executable(
        "desktop_client.py",
        target_name="WeMath2MD",
        base="Win32GUI",  # ignored on non-Windows
    )
]

setup(
    name="WeMath2MD",
    version="1.0.0",
    description="WeMath2MD Desktop Client",
    options={"build_exe": build_exe_options},
    executables=executables,
)
