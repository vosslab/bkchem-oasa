"""Frontend interaction for backend-owned molecular identifier exports."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.bridge.oasa_bridge
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _active_identifier_document_session(app: object) -> object | None:
	"""Return the live registered session that owns the active projection."""
	session = getattr(app, "_active_session", None)
	document = getattr(app, "document", None)
	scene = getattr(app, "scene", None)
	view = getattr(app, "view", None)
	sessions = getattr(app, "sessions", ())
	if session is None or document is None or scene is None or view is None:
		return None
	if session.is_disposed or session not in sessions:
		return None
	if session.document is not document or session.scene is not scene or session.view is not view:
		return None
	return session


#============================================
def _selected_molecule_context(app: object, format_name: str) -> tuple[object, str] | None:
	"""Resolve one exact authoritative molecule or show an actionable warning."""
	session = _active_identifier_document_session(app)
	if session is None:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Export %s" % format_name,
			"%s export requires an active synchronized document session." % format_name,
		)
		return None
	if not session.can_write_authoritative_snapshot:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Export %s" % format_name,
			"%s export is unavailable until the document projection recovers."
			% format_name,
		)
		return None
	molecule_ids = session.document.selected_direct_root_molecule_ids
	if len(molecule_ids) != 1:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Export %s" % format_name,
			"Please select exactly one molecule and no presentation objects.",
		)
		return None
	return session, molecule_ids[0]


#============================================
def _show_query_failure(app: object, format_name: str, failure: object) -> None:
	"""Translate one typed backend observation failure into useful UI text."""
	if failure.kind == "projection-unavailable":
		title = "Export %s" % format_name
		message = "%s export is unavailable until the document projection recovers." % format_name
	elif failure.kind == "revision-conflict":
		title = "Export %s" % format_name
		message = "%s export used an older document revision. Please try again:\n%s" % (
			format_name, failure.message,
		)
	elif failure.kind == "unavailable":
		title = "Export %s" % format_name
		message = "%s export is unavailable for this molecule:\n%s" % (
			format_name, failure.message,
		)
	else:
		title = "%s Export Error" % format_name
		message = "Failed to generate %s:\n%s" % (format_name, failure.message)
	PySide6.QtWidgets.QMessageBox.warning(app, title, message)


#============================================
def _gen_smiles(app: object) -> None:
	"""Copy canonical SMILES observed from one authoritative molecule."""
	context = _selected_molecule_context(app, "SMILES")
	if context is None:
		return
	session, molecule_id = context
	response = bkchem_qt.bridge.oasa_bridge.query_molecule_smiles(
		session, session.backend_snapshot.revision, molecule_id,
	)
	if response.failure is not None:
		_show_query_failure(app, "SMILES", response.failure)
		return
	result = response.value
	if result is None:
		return
	PySide6.QtWidgets.QApplication.clipboard().setText(result.smiles)
	PySide6.QtWidgets.QMessageBox.information(
		app, "Export SMILES",
		"SMILES (copied to clipboard):\n\n%s" % result.smiles,
	)


#============================================
def _gen_inchi(app: object) -> None:
	"""Copy standard InChI and InChIKey derived by OASA from backend CDML."""
	context = _selected_molecule_context(app, "InChI")
	if context is None:
		return
	session, molecule_id = context
	response = bkchem_qt.bridge.oasa_bridge.query_molecule_identifiers(
		session, session.backend_snapshot.revision, molecule_id,
	)
	if response.failure is not None:
		_show_query_failure(app, "InChI", response.failure)
		return
	result = response.value
	if result is None:
		return
	text = "%s\nInChIKey=%s" % (result.inchi, result.inchikey)
	PySide6.QtWidgets.QApplication.clipboard().setText(text)
	PySide6.QtWidgets.QMessageBox.information(
		app, "Export InChI",
		"InChI and InChIKey (copied to clipboard):\n\n%s" % text,
	)


#============================================
def register_identifier_actions(registry: object, app: object) -> None:
	"""Register authoritative standard molecular identifier exports."""
	def one_synchronized_direct_root_molecule_selected() -> bool:
		"""Return whether one durable molecule is ready for an observation."""
		session = _active_identifier_document_session(app)
		return bool(
			session is not None
			and session.can_write_authoritative_snapshot
			and len(session.document.selected_direct_root_molecule_ids) == 1
		)

	registry.register(MenuAction(
		id="chemistry.gen_smiles",
		label_key="Export SMILES",
		help_key="Export SMILES for the selected structure",
		accelerator=None,
		handler=lambda: _gen_smiles(app),
		enabled_when=one_synchronized_direct_root_molecule_selected,
	))
	registry.register(MenuAction(
		id="chemistry.gen_inchi",
		label_key="Export InChI",
		help_key="Export standard InChI and InChIKey for the selected structure",
		accelerator=None,
		handler=lambda: _gen_inchi(app),
		enabled_when=one_synchronized_direct_root_molecule_selected,
	))
