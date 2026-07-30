"""Resolve package-owned BKChem-Qt runtime resources."""

# Standard Library
import pathlib


# The Qt frontend owns the files it opens at runtime.  Keeping these resources
# inside the Python package makes wheels independent of the source-tree link
# to the legacy frontend's bkchem_data directory.
RESOURCE_DIR = pathlib.Path(__file__).resolve().parent / "resources"


#============================================
def get_resource_path(*parts: str) -> pathlib.Path:
	"""Return a path inside the packaged Qt resource directory.

	Args:
		*parts: Relative resource path components.

	Returns:
		Path to the requested package-owned resource.
	"""
	resource_path = RESOURCE_DIR.joinpath(*parts)
	return resource_path
