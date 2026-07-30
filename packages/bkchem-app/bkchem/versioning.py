"""Resolve BKChem's release version in source and installed layouts."""

# Standard Library
import importlib.metadata
import os

# local repo modules
import oasa.version_registry


#============================================
def _source_tree_version() -> str | None:
	"""Return the checked-out registry version only from the known source layout."""
	package_dir = os.path.dirname(__file__)
	package_root = os.path.dirname(package_dir)
	packages_dir = os.path.dirname(package_root)
	if (
		os.path.basename(package_root) != "bkchem-app"
		or os.path.basename(packages_dir) != "packages"
	):
		return None

	version_path = os.path.join(os.path.dirname(packages_dir), "VERSION")
	try:
		version = oasa.version_registry.read_version_file(version_path)
	except (OSError, ValueError) as error:
		raise RuntimeError(f"Unable to read VERSION file: {error}")
	return version


#============================================
def application_version() -> str:
	"""Return source registry data or installed BKChem package metadata."""
	source_version = _source_tree_version()
	if source_version is not None:
		return source_version
	try:
		installed_version = importlib.metadata.version("bkchem")
	except importlib.metadata.PackageNotFoundError:
		raise RuntimeError("BKChem package metadata is unavailable")
	return installed_version
