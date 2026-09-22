import tomllib
from pathlib import Path
import src


def test_version_consistency():
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    assert pyproject_path.exists()

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    pkg_version = data["project"]["version"]
    assert src.__version__ == pkg_version
    assert src.__version__ == "1.0.0"


def test_release_author_metadata():
    assert hasattr(src, "__author__")
    assert src.__author__ == "Day Trade AI Team"