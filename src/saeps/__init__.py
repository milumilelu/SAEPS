"""SAEPS validation infrastructure."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("saeps-validation")
except PackageNotFoundError:  # pragma: no cover - source tree without install
    __version__ = "0+unknown"

__all__ = ["__version__"]

