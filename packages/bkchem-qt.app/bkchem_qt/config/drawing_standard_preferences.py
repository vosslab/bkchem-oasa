"""Personal drawing-standard persistence and clean blank-session seeding."""

# Standard Library
import json

# local repo modules
import bkchem_qt.config.preferences
import oasa.cdml_document
import oasa.cdml_standard
import oasa.cdml_writer


_BLANK_CDML = '<cdml xmlns="%s" version="%s"></cdml>' % (
	oasa.cdml_writer.CDML_NAMESPACE, oasa.cdml_writer.DEFAULT_CDML_VERSION,
)


#============================================
def _normalized_complete_values(values: object) -> tuple[tuple[str, object], ...]:
	"""Return a validated, contract-ordered complete personal style."""
	if type(values) is not tuple:
		raise ValueError("Personal drawing style values must be an immutable tuple")
	normalized = oasa.cdml_standard.validate_patch(
		oasa.cdml_standard.CDMLDrawingStandardPatch(0, values),
	)
	by_name = dict(normalized)
	if set(by_name) != set(oasa.cdml_standard.DRAWING_STANDARD_FIELDS):
		raise ValueError("Personal drawing style must contain every standard field")
	return tuple(
		(name, by_name[name]) for name in oasa.cdml_standard.DRAWING_STANDARD_FIELDS
	)


#============================================
def load_personal_drawing_standard(prefs: object) -> tuple[tuple[str, object], ...]:
	"""Return one valid saved complete style, or no style for malformed settings."""
	raw = prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_PERSONAL_DRAWING_STANDARD,
		None,
	)
	if type(raw) is not str or not raw:
		return ()
	try:
		payload = json.loads(raw)
		if type(payload) is not dict or set(payload) != {"version", "values"}:
			return ()
		if payload["version"] != 1 or type(payload["values"]) is not dict:
			return ()
		values = tuple(payload["values"].items())
		return _normalized_complete_values(values)
	except (TypeError, ValueError, json.JSONDecodeError):
		return ()


#============================================
def has_personal_drawing_standard(prefs: object) -> bool:
	"""Return whether settings contain one usable complete personal style."""
	return bool(load_personal_drawing_standard(prefs))


#============================================
def save_personal_drawing_standard(
		prefs: object, values: tuple[tuple[str, object], ...],
		) -> tuple[tuple[str, object], ...]:
	"""Validate and persist one complete style as frontend application state."""
	normalized = _normalized_complete_values(values)
	payload = json.dumps(
		{"version": 1, "values": dict(normalized)},
		separators=(",", ":"), sort_keys=True,
	)
	prefs.set_value(
		bkchem_qt.config.preferences.Preferences.KEY_PERSONAL_DRAWING_STANDARD,
		payload,
	)
	return normalized


#============================================
def remove_personal_drawing_standard(prefs: object) -> None:
	"""Remove the personal style while leaving every document untouched."""
	prefs.remove_value(
		bkchem_qt.config.preferences.Preferences.KEY_PERSONAL_DRAWING_STANDARD,
	)


#============================================
def blank_backend_session(prefs: object) -> oasa.cdml_document.CDMLDocumentSession:
	"""Create a clean backend blank document seeded from valid personal values."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_BLANK_CDML)
	changes = load_personal_drawing_standard(prefs)
	if not changes:
		return session
	commit = session.patch_drawing_standard(
		oasa.cdml_standard.CDMLDrawingStandardPatch(session.revision, changes),
	)
	session.mark_saved(expected_revision=commit.snapshot.revision)
	return session
