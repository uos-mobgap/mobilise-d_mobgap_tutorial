"""Configure the uv venv for Jupyter and editable mobgap imports."""

from __future__ import annotations

import site
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    cache_dir = project_root / ".numba_cache"
    cache_dir.mkdir(exist_ok=True)

    site_packages = Path(site.getsitepackages()[0])
    env_module = site_packages / "mobgap_tutorial_env.py"
    env_module.write_text(
        "\n".join(
            [
                "import os",
                "from pathlib import Path",
                "",
                f'_cache_dir = Path("{cache_dir}")',
                "_cache_dir.mkdir(exist_ok=True)",
                'os.environ.setdefault("NUMBA_CACHE_DIR", str(_cache_dir))',
                "",
            ]
        )
    )

    pth_file = site_packages / "mobgap_tutorial.pth"
    pth_file.write_text("import mobgap_tutorial_env\n")

    print(f"Wrote {env_module}")
    print(f"Wrote {pth_file}")
    print(f"NUMBA_CACHE_DIR={cache_dir}")
    print(f"Python {sys.version.split()[0]} at {sys.executable}")


if __name__ == "__main__":
    main()
