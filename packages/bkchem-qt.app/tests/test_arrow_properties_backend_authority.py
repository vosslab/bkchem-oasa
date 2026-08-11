"""Qt behavior for backend-authoritative direct-root Arrow Configure."""

# Standard Library
import pathlib

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.actions.object_actions
import bkchem_qt.canvas.items.arrow_item
import bkchem_qt.dialogs.arrow_dialog
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import oasa.cdml_document


_CDML = (
	'<cdml version="26.07"><arrow id="arrow1" type="normal" start="no" end="yes" '
	'spline="no" width="1.5" color="#112233" length="2cm" shape="(8,10,3)">'
	'<point x="1cm" y="1cm"/><point x="2cm" y="2cm"/>'
	'<point x="3cm" y="1cm"/></arrow></cdml>'
)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one projected native-CDML session with a durable Arrow."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native Arrow CDML projection is unavailable")
	return registered


#============================================
def _arrow_item(session: object) -> object:
	"""Return the current durable Arrow graphics projection."""
	for item in session.scene.items():
		model = getattr(item, "document_object_model", None)
		if (
			isinstance(item, bkchem_qt.canvas.items.arrow_item.ArrowItem)
			and getattr(model, "object_id", None) == "arrow1"
		):
			return item
	raise AssertionError("Projected CDML did not produce the durable Arrow item")


#============================================
def _arrow_attributes(cdml: str) -> dict[str, str]:
	"""Read current Arrow attributes through the frontend-neutral observation."""
	backend = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	description = backend.presentation_description(
		oasa.cdml_document.CDMLPresentationDescriptionQuery(backend.revision),
	)
	record = next(record for record in description.records if record.identifier == "arrow1")
	return dict(record.attributes)


#============================================
def test_arrow_dialog_initializes_spline_and_returns_changed_intent(qapp: object) -> None:
	"""The detached dialog must not silently reset an authored spline."""
	dialog = bkchem_qt.dialogs.arrow_dialog.ArrowDialog(
		start_head=True, end_head=False, line_width=2.5,
		spline=True, color="#112233",
	)
	try:
		assert dialog.get_values() == {
			"start_head": True, "end_head": False, "line_width": 2.5,
			"spline": True, "color": "#112233",
		}
		assert dialog.changes() == ()
		dialog._spline_check.setChecked(False)
		assert dialog.changes() == (("spline", False),)
	finally:
		dialog.deleteLater()


#============================================
def test_configure_undo_redo_save_and_reopen_use_one_backend_history(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
		) -> None:
	"""The complete user path changes authority, recovers, saves, and reopens."""
	session = _install_native_session(main_window)
	observed = {}
	try:
		old_document = session.document
		old_item = _arrow_item(session)
		old_item.setSelected(True)
		def accept(dialog: object) -> int:
			"""Observe the projected values supplied to the modal editor."""
			observed.update(dialog.get_values())
			return PySide6.QtWidgets.QDialog.DialogCode.Accepted

		monkeypatch.setattr(bkchem_qt.dialogs.arrow_dialog.ArrowDialog, "exec", accept)
		monkeypatch.setattr(
			bkchem_qt.dialogs.arrow_dialog.ArrowDialog, "changes",
			lambda _dialog: (
				("start_head", True), ("end_head", False), ("spline", True),
				("line_width", 2.5), ("color", "#AABBCC"),
			),
		)
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		item = _arrow_item(session)
		attributes = _arrow_attributes(session.backend_snapshot.cdml)

		assert observed == {
			"start_head": False, "end_head": True, "line_width": 1.5,
			"spline": False, "color": "#112233",
		}
		assert tuple(attributes[name] for name in ("start", "end", "spline", "width", "color")) == (
			"yes", "no", "yes", "2.5", "#aabbcc",
		)
		assert (
			session.document is not old_document and item is not old_item
			and item.start_head and not item.end_head and item.spline
			and item.line_width == 2.5 and item.color == "#aabbcc"
			and item.isSelected() and session.can_undo_backend
			and not session.document.undo_stack.canUndo()
		)

		undo = session.undo_backend()
		assert undo.status == "accepted"
		assert _arrow_attributes(session.backend_snapshot.cdml)["width"] == "1.5"
		redo = session.redo_backend()
		assert redo.status == "accepted"
		assert _arrow_attributes(session.backend_snapshot.cdml)["width"] == "2.5"

		path = tmp_path / "arrow-properties.cdml"
		saved = session.write_backend_snapshot(str(path))
		reopened = oasa.cdml_document.CDMLDocumentSession.load(path.read_text())
		assert not saved.is_dirty and not session.backend_snapshot.is_dirty
		assert _arrow_attributes(reopened.snapshot().cdml)["color"] == "#aabbcc"
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_modal_arrow_configure_remains_bound_to_its_origin_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Tab activation during the dialog cannot redirect accepted Arrow intent."""
	origin = _install_native_session(main_window)
	other = None
	try:
		_arrow_item(origin).setSelected(True)
		def activate_other(_dialog: object) -> int:
			"""Activate an independent document before returning accepted intent."""
			main_window.on_new()
			return PySide6.QtWidgets.QDialog.DialogCode.Accepted

		monkeypatch.setattr(
			bkchem_qt.dialogs.arrow_dialog.ArrowDialog, "exec", activate_other,
		)
		monkeypatch.setattr(
			bkchem_qt.dialogs.arrow_dialog.ArrowDialog, "changes",
			lambda _dialog: (("line_width", 3.0),),
		)
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		other = next(session for session in main_window.sessions if session is not origin)

		assert _arrow_attributes(origin.backend_snapshot.cdml)["width"] == "3"
		assert "arrow1" not in other.backend_snapshot.cdml
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)
