"""Plain release-metadata boundary for the BKChem-Qt frontend.

The Qt application consumes only the display version string and this module's
typed failure.  OASA's shared release registry remains an implementation
detail here, so dialogs, CLI parsing, and QApplication setup have no backend
type dependency.
"""

# Standard Library
import importlib.metadata
import pathlib

# local repo modules
import oasa.version_registry


class ReleaseMetadataError(RuntimeError):
	"""Report missing or invalid frontend release metadata."""


#============================================
def read_source_tree_display_version(version_path: str | pathlib.Path) -> str:
	"""Return one canonical display version from the supplied source registry.

	Args:
		version_path: Explicit root ``VERSION`` file for a recognized checkout.

	Raises:
		ReleaseMetadataError: If the registry cannot provide one valid version.
	"""
	try:
		return oasa.version_registry.read_version_file(str(version_path))
	except (OSError, ValueError) as error:
		raise ReleaseMetadataError(f"Unable to read VERSION file: {error}") from error


#============================================
def installed_display_version(distribution_name: str) -> str:
	"""Return canonical display CalVer from one installed distribution name.

	Args:
		distribution_name: Installed package name resolved through Python metadata.

	Raises:
		ReleaseMetadataError: If metadata is absent or outside BKChem's CalVer
			profile.
	"""
	try:
		installed_version = importlib.metadata.version(distribution_name)
	except importlib.metadata.PackageNotFoundError as error:
		raise ReleaseMetadataError("BKChem-Qt package metadata is unavailable") from error
	try:
		return oasa.version_registry.display_from_distribution(installed_version)
	except oasa.version_registry.ReleaseVersionError as error:
		raise ReleaseMetadataError(
			f"Unsupported installed BKChem-Qt version metadata: {error}"
		) from error
