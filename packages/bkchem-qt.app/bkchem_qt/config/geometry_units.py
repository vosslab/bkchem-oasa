"""Geometry unit helpers for BKChem-Qt scene-space values."""

# local repo modules
import bkchem_qt.bridge.display_geometry
import bkchem_qt.config.preferences


DEFAULT_BOND_LENGTH_PT = 40.0


#============================================
def cm_to_pt(cm: float) -> float:
	"""Convert centimeters to scene points."""
	return bkchem_qt.bridge.display_geometry.cm_to_points(cm)


#============================================
def pt_to_cm(pt: float) -> float:
	"""Convert scene points to centimeters."""
	return bkchem_qt.bridge.display_geometry.points_to_cm(pt)


#============================================
def resolve_bond_length_pt(
	prefs: bkchem_qt.config.preferences.Preferences,
) -> float:
	"""Return the canonical bond length in scene points.

	Reads only the hard-cut canonical key ``drawing/bond_length_pt``.
	Legacy ``drawing/bond_length`` is intentionally ignored.
	"""
	raw = prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_BOND_LENGTH_PT,
		DEFAULT_BOND_LENGTH_PT,
	)
	try:
		value = float(raw)
	except (TypeError, ValueError):
		return DEFAULT_BOND_LENGTH_PT
	if value <= 0.0:
		return DEFAULT_BOND_LENGTH_PT
	return value
