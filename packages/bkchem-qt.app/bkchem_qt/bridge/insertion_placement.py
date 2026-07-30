"""Qt-session capture for plain backend molecule-insertion placement data."""

# local repo modules
import oasa.insertion_geometry
import bkchem_qt.config.geometry_units


DEFAULT_INSERTION_ANCHOR = (2000.0, 1500.0)


#============================================
def capture_insertion_placement(target: object) -> tuple[float, tuple[float, float]]:
	"""Snapshot scene scale and paper center as built-in worker values only."""
	bond_length_pt = bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT
	anchor = DEFAULT_INSERTION_ANCHOR
	scene = getattr(target, "scene", None)
	if scene is not None and hasattr(scene, "grid_spacing_pt"):
		bond_length_pt = float(scene.grid_spacing_pt)
	if scene is not None and hasattr(scene, "paper_rect"):
		center = scene.paper_rect.center()
		anchor = (float(center.x()), float(center.y()))
	return oasa.insertion_geometry.validate_insertion_placement(bond_length_pt, anchor)
