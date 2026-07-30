"""Release-version consistency and runtime-resolution coverage."""

# Standard Library
import pathlib
import sys
import tomllib

# PIP3 modules
import pytest

# local repo modules
import bkchem.versioning
import bkchem_qt.cli
import bkchem_qt.versioning
import oasa.version_registry


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "devel"))
import version_registry

PROJECT_FILES = sorted(REPO_ROOT.glob("packages/*/pyproject.toml"))
VERSION_MODULES = ((bkchem.versioning, "bkchem"),)


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
def test_source_tree_runtime_versions_match_release_registry() -> None:
	"""Both frontends report the registry version when run from this checkout."""
	runtime_versions = (
		bkchem.versioning.application_version(),
		bkchem_qt.versioning.application_version(),
	)

	assert runtime_versions == (_registry_version(), _registry_version())


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


#============================================
@pytest.mark.parametrize("version_module, distribution_name", VERSION_MODULES)
def test_installed_runtime_version_uses_package_metadata(
		monkeypatch: pytest.MonkeyPatch,
		version_module: object,
		distribution_name: str,
		) -> None:
	"""An installed package obtains its version from installed metadata."""
	monkeypatch.setattr(version_module, "_source_tree_version", lambda: None)
	monkeypatch.setattr(
		version_module.importlib.metadata,
		"version",
		lambda name: f"{name}-metadata",
	)

	assert version_module.application_version() == f"{distribution_name}-metadata"


#============================================
def test_installed_qt_runtime_reconstructs_display_from_normalized_metadata(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The installed Qt CLI restores display CalVer rather than exposing wheel text."""
	monkeypatch.setattr(bkchem_qt.versioning, "_source_tree_version", lambda: None)
	monkeypatch.setattr(
		bkchem_qt.versioning.importlib.metadata,
		"version",
		lambda _name: "26.2a1",
	)

	assert bkchem_qt.versioning.application_version() == "26.02a1"


#============================================
def test_installed_qt_cli_reports_display_form_from_normalized_metadata(
		monkeypatch: pytest.MonkeyPatch,
		capsys: pytest.CaptureFixture[str],
		) -> None:
	"""The public version flag retains display CalVer without importing Qt startup."""
	monkeypatch.setattr(bkchem_qt.versioning, "_source_tree_version", lambda: None)
	monkeypatch.setattr(
		bkchem_qt.versioning.importlib.metadata,
		"version",
		lambda _name: "26.2a1",
	)
	monkeypatch.setattr(sys, "argv", ["bkchem-qt", "--version"])
	monkeypatch.delitem(sys.modules, "bkchem_qt.app", raising=False)

	with pytest.raises(SystemExit):
		bkchem_qt.cli.parse_args()

	assert (capsys.readouterr().out.strip(), "bkchem_qt.app" in sys.modules) == (
		"BKChem-Qt 26.02a1", False,
	)


#============================================
def test_installed_qt_runtime_rejects_non_bkchem_distribution_metadata(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Installed Qt runtime exposes a typed failure instead of guessing a label."""
	monkeypatch.setattr(bkchem_qt.versioning, "_source_tree_version", lambda: None)
	monkeypatch.setattr(
		bkchem_qt.versioning.importlib.metadata,
		"version",
		lambda _name: "unrelated-version",
	)

	with pytest.raises(RuntimeError, match="Unsupported installed BKChem-Qt version metadata"):
		bkchem_qt.versioning.application_version()


#============================================
def test_version_flag_does_not_import_qt_application(
		monkeypatch: pytest.MonkeyPatch,
		capsys: pytest.CaptureFixture[str],
		) -> None:
	"""The version flag remains usable before PySide6 startup imports."""
	monkeypatch.setattr(sys, "argv", ["bkchem-qt", "--version"])
	monkeypatch.setattr(
		bkchem_qt.versioning,
		"application_version",
		lambda: "test-version",
	)
	monkeypatch.delitem(sys.modules, "bkchem_qt.app", raising=False)
	with pytest.raises(SystemExit):
		bkchem_qt.cli.parse_args()
	result = capsys.readouterr()

	assert (result.out.strip(), "bkchem_qt.app" in sys.modules) == (
		"BKChem-Qt test-version", False,
	)
