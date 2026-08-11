"""Behavior tests for personal drawing styles and clean blank documents."""

# local repo modules
import bkchem_qt.config.drawing_standard_preferences
import bkchem_qt.config.preferences
import oasa.cdml_standard


_VALUES = (
	("line_width", 2.0), ("font_size", 18), ("font_family", "Courier"),
	("line_color", "#246"), ("area_color", "#ffffff"),
	("bond_width", 8.0), ("wedge_width", 7.0), ("double_ratio", 0.5),
	("show_hydrogens", True),
)


#============================================
class _Preferences:
	"""Small in-memory preferences seam with the production public methods."""

	def __init__(self) -> None:
		self.values: dict[str, object] = {}

	def value(self, key: str, default: object = None) -> object:
		"""Return stored state or one caller fallback."""
		return self.values.get(key, default)

	def set_value(self, key: str, value: object) -> None:
		"""Store one value."""
		self.values[key] = value

	def remove_value(self, key: str) -> None:
		"""Remove one value when present."""
		self.values.pop(key, None)


#============================================
def test_personal_standard_round_trip_is_complete_and_normalized() -> None:
	"""Settings retain validated plain values without storing CDML or Qt state."""
	prefs = _Preferences()
	saved = bkchem_qt.config.drawing_standard_preferences.save_personal_drawing_standard(
		prefs, _VALUES,
	)
	loaded = bkchem_qt.config.drawing_standard_preferences.load_personal_drawing_standard(
		prefs,
	)

	assert loaded == saved
	assert dict(loaded)["line_color"] == "#224466"
	assert bkchem_qt.config.drawing_standard_preferences.has_personal_drawing_standard(
		prefs,
	)


#============================================
def test_malformed_or_incomplete_personal_standard_is_ignored() -> None:
	"""Corrupt application settings cannot prevent a user from opening BKChem."""
	prefs = _Preferences()
	key = bkchem_qt.config.preferences.Preferences.KEY_PERSONAL_DRAWING_STANDARD
	for malformed in ("not-json", '{"version":1,"values":{"font_size":18}}'):
		prefs.values[key] = malformed
		assert (
			bkchem_qt.config.drawing_standard_preferences.load_personal_drawing_standard(
				prefs,
			) == ()
		)


#============================================
def test_personal_standard_seeds_one_clean_authoritative_blank_document() -> None:
	"""New documents start clean while OASA owns their persisted standard."""
	prefs = _Preferences()
	bkchem_qt.config.drawing_standard_preferences.save_personal_drawing_standard(
		prefs, _VALUES,
	)
	session = bkchem_qt.config.drawing_standard_preferences.blank_backend_session(prefs)
	snapshot = session.snapshot()
	standard = session.drawing_standard(
		oasa.cdml_standard.CDMLDrawingStandardQuery(snapshot.revision),
	)

	assert not snapshot.is_dirty
	assert (standard.font_size, standard.font_family, standard.line_color) == (
		18, "Courier", "#224466",
	)
	assert "<standard" in snapshot.cdml


#============================================
def test_remove_personal_standard_restores_factory_blank_behavior() -> None:
	"""Removing the preference does not invent a standard in later blank files."""
	prefs = _Preferences()
	bkchem_qt.config.drawing_standard_preferences.save_personal_drawing_standard(
		prefs, _VALUES,
	)
	bkchem_qt.config.drawing_standard_preferences.remove_personal_drawing_standard(prefs)
	session = bkchem_qt.config.drawing_standard_preferences.blank_backend_session(prefs)
	standard = session.drawing_standard(
		oasa.cdml_standard.CDMLDrawingStandardQuery(session.revision),
	)

	assert not standard.present
	assert not session.snapshot().is_dirty
