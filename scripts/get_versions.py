# /// script
# requires-python = ">=3.11"
# ///
from urllib.request import urlopen
import tomllib
from sys import argv


def get_ruff_versions(ruff_vscode_version=None):
    ref = f"tags/{ruff_vscode_version}" if ruff_vscode_version else "heads/main"
    with urlopen(
        f"https://raw.githubusercontent.com/astral-sh/ruff-vscode/refs/{ref}/pyproject.toml"
    ) as r:
        project = tomllib.load(r)["project"]
        ruff_vscode_version = project["version"]
        ruff_version = next(
            d.split("==")[-1] for d in project["dependencies"] if d.startswith("ruff==")
        )
        return ruff_version, ruff_vscode_version


if __name__ == "__main__":
    print(" ".join(get_ruff_versions(argv[1] if len(argv) > 1 else None)))
