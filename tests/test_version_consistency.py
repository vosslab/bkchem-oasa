"""Release-version consistency and runtime-resolution coverage."""

# Standard Library
import pathlib
import sys
import tomllib

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.versioning
import oasa.version_registry


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "devel"))
import version_registry

PROJECT_FILES = sorted(REPO_ROOT.glob("packages/*/pyproject.toml"))


#============================================
def _registry_version() -> str:
	"""Read the canonical release version from the root registry."""
	version = version_registry.read_version_file(str(REPO_ROOT / "VERSION"))
	return version


#============================================
@pytest.mark.parametrize("project_path", PROJECT_FILES, ids=lambda path: path.parent.name)
def test_package_metadata_matches_release_registry(project_path: pathlib.Path) -> None:
	"""Each distributable package advertises the canonical release version."""
	project_data = tomllib.loads(project_path.read_text(encoding="utf-8"))
	registry_version = _registry_version()

	assert project_data["project"]["version"] == registry_version
	if project_data["project"]["name"] != "oasa":
		assert f"oasa>={registry_version}" in project_data["project"]["dependencies"]


#============================================
def test_source_tree_qt_runtime_version_matches_release_registry() -> None:
	"""The supported frontend reports the registry label from this checkout."""
	assert bkchem_qt.versioning.application_version() == _registry_version()


#============================================
def test_source_tree_registry_parser_drops_comment_suffix() -> None:
	"""Source-mode version readers obtain the value without registry comments."""
	text = "# release registry\nversion = 26.02a1 # alpha\n"

	assert oasa.version_registry.parse_version_text(text) == "26.02a1"


#============================================
def test_source_tree_registry_rejects_leading_v_prefix() -> None:
	"""The stored registry keeps one canonical PEP 440 subset spelling."""
	with pytest.raises(ValueError):
		oasa.version_registry.parse_version_text("version = v26.02a1\n")
