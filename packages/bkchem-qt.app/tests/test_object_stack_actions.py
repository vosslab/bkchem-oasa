"""Live backend-authority checks for Object presentation-stack actions."""

# Standard Library
import pathlib

# PIP3 modules
import pytest
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import oasa.cdml_document


_STACK_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'version="26.07">'
	'<!--header--><info/><paper type="A4"/><viewport><transform/></viewport>'
	'<molecule id="mol-1"><atom id="atom-1" name="C"><point x="1cm" y="1cm"/>'
	'</atom></molecule><arrow id="arrow-1"><point x="2cm" y="1cm"/>'
	'<point x="3cm" y="1cm"/></arrow><text id="text-1"><point x="4cm" y="1cm"/>'
	'<font/><ftext>note</ftext></text><plus id="plus-1"><point x="5cm" y="1cm"/>'
	'</plus><plus><point x="6cm" y="1cm"/></plus><external-data><foreign keep="yes"/>'
	'</external-data>'
	'</cdml>'
)


#============================================
def _install_stack_document(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> object:
	"""Open one complete authoritative snapshot through the normal tab path."""
	source = tmp_path / "presentation-stack.cdml"
	source.write_text(_STACK_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	return main_window._active_session


#============================================
def _root_ids(cdml_text: str) -> tuple[str | None, ...]:
	"""Read direct-root identity in authoritative source order."""
	document = oasa.cdml_document.CDMLDocument.parse(cdml_text)
	return tuple(record.identifier for record in document.objects())


#============================================
def _item_for(session: object, identifier: str) -> PySide6.QtWidgets.QGraphicsItem:
	"""Return one normally projected durable presentation item."""
	return next(
		item for item in session.scene.items()
		if getattr(getattr(item, "document_object_model", None), "object_id", None) == identifier
	)


#============================================
def test_bring_to_front_uses_backend_history_and_canonical_reprojection(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""One real Object action changes only authoritative presentation order."""
	session = _install_stack_document(main_window, tmp_path)
	before = session.backend_snapshot
	previous_document = session.document
	_item_for(session, "arrow-1").setSelected(True)
	_item_for(session, "text-1").setSelected(True)
	main_window._registry.get("object.bring_to_front").handler()
	after = session.backend_snapshot

	assert after.revision == before.revision + 1 and session.document is not previous_document
	assert _root_ids(after.cdml) == (
		None, None, None, "mol-1", "plus-1", None, None, "arrow-1", "text-1",
	)
	assert "id=\"mol-1\"" in after.cdml and "<external-data>" in after.cdml
	assert main_window.can_save_authoritatively() and session.document.undo_stack.count() == 0
	assert session.undo_backend().status == "accepted"
	assert session.backend_snapshot.cdml == before.cdml
	assert session.redo_backend().status == "accepted" and session.backend_snapshot.cdml == after.cdml


#============================================
@pytest.mark.parametrize("invalid_kind", ("mixed", "child", "idless", "forged"))
def test_invalid_or_forged_stack_selection_is_inert(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		invalid_kind: str,
		) -> None:
	"""Each unsupported selected graphics route leaves backend state untouched."""
	session = _install_stack_document(main_window, tmp_path)
	before = session.backend_snapshot
	projection = session.document
	arrow = _item_for(session, "arrow-1")
	if invalid_kind == "mixed":
		invalid = next(item for item in session.scene.items() if getattr(item, "atom_model", None))
	elif invalid_kind == "child":
		invalid = PySide6.QtWidgets.QGraphicsRectItem(arrow)
		invalid.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
	elif invalid_kind == "idless":
		invalid = next(
			item for item in session.scene.items()
			if getattr(getattr(item, "document_object_model", None), "object_id", None) is None
		)
	else:
		invalid = PySide6.QtWidgets.QGraphicsRectItem()
		invalid.document_object_model = arrow.document_object_model
		invalid.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
		session.scene.addItem(invalid)
	arrow.setSelected(True)
	invalid.setSelected(True)
	main_window._registry.get("object.send_back").handler()

	assert session.backend_snapshot == before and session.document is projection
	assert not session.can_undo_backend and session.document.undo_stack.count() == 0


#============================================
def test_stale_and_already_front_stack_requests_are_atomic_noops(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Revision conflicts and semantic no-ops retain installed state and history."""
	session = _install_stack_document(main_window, tmp_path)
	before = session.backend_snapshot
	stale = bkchem_qt.models.document_session.build_presentation_stack_request(
		before.revision, "send-back", ("arrow-1",),
	)
	_item_for(session, "arrow-1").setSelected(True)
	main_window._registry.get("object.send_back").handler()
	changed = session.backend_snapshot
	projection = session.document
	stale_outcome = session.submit_persistent_operation(stale)
	_item_for(session, "arrow-1").setSelected(True)
	main_window._registry.get("object.send_back").handler()

	assert stale_outcome.status == "rejected" and session.backend_snapshot == changed
	assert session.document is projection and session.document.undo_stack.count() == 0
