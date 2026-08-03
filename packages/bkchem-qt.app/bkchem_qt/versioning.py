"""Resolve BKChem-Qt's release version in source and installed layouts."""

# Standard Library
import os

# local repo modules
import bkchem_qt.bridge.release_metadata


#============================================
def _source_tree_version() -> str | None:
	"""Return the checked-out registry version only from the known source layout."""
	package_dir = os.path.dirname(__file__)
	package_root = os.path.dirname(package_dir)
	packages_dir = os.path.dirname(package_root)
	if (
		os.path.basename(package_root) != "bkchem-qt.app"
		or os.path.basename(packages_dir) != "packages"
	):
		return None

	version_path = os.path.join(os.path.dirname(packages_dir), "VERSION")
	return bkchem_qt.bridge.release_metadata.read_source_tree_display_version(version_path)


#============================================
def application_version() -> str:
	"""Return the exact BKChem CalVer display label in every supported layout."""
	source_version = _source_tree_version()
	if source_version is not None:
		return source_version
	return bkchem_qt.bridge.release_metadata.installed_display_version("bkchem-qt")
