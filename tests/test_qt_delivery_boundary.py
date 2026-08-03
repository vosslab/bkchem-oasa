"""Static delivery-boundary checks for the supported BKChem application."""

# Standard Library
import pathlib
import tomllib


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


#============================================
def _project_metadata(package_directory: str) -> dict[str, object]:
	"""Read one package's declared distribution metadata."""
	metadata_path = REPO_ROOT / "packages" / package_directory / "pyproject.toml"
	return tomllib.loads(metadata_path.read_text(encoding="utf-8"))["project"]


#============================================
def test_only_qt_distribution_declares_a_bkchem_application_command() -> None:
	"""Installed metadata exposes the supported Qt command and retires Tk's one."""
	distribution_scripts = {
		package_directory: _project_metadata(package_directory).get("scripts", {})
		for package_directory in ("bkchem-app", "bkchem-qt.app", "oasa")
	}
	qt_scripts = distribution_scripts["bkchem-qt.app"]
	declared_command_names = {
		command_name
		for scripts in distribution_scripts.values()
		for command_name in scripts
	}
	qt_command_providers = {
		package_directory
		for package_directory, scripts in distribution_scripts.items()
		if "bkchem-qt" in scripts
	}

	assert (qt_scripts["bkchem-qt"], qt_command_providers) == (
		"bkchem_qt.cli:main", {"bkchem-qt.app"},
	)
	assert not {"bkchem", "bkchem-tk"} & declared_command_names
