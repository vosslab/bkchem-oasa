"""Focused Qt behavior for backend-authoritative plain Plus Configure."""

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml

import bkchem_qt.actions.object_actions
import bkchem_qt.canvas.items.text_item
import bkchem_qt.dialogs.plus_dialog
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle


_CDML = (
	'<cdml version="26.07"><molecule id="m1"><atom id="a1" name="C">'
	'<point x="1cm" y="1cm"/></atom></molecule><plus id="plus1" font_size="13" '
	'color="#112233" keep="yes"><point x="3cm" y="4cm" keep="point"/>'
	'<font family="Courier" keep="font"/></plus></cdml>'
)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one projected native-CDML session with a durable plain Plus."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native Plus CDML projection is unavailable")
	return registered


#============================================
def _plus_item(session: object) -> object:
	"""Return the current durable Plus graphics projection."""
	for item in session.scene.items():
		model = getattr(item, "document_object_model", None)
		if (
			isinstance(item, bkchem_qt.canvas.items.text_item.TextItem)
			and getattr(model, "kind", None) == "plus"
			and getattr(model, "object_id", None) == "plus1"
		):
			return item
	raise AssertionError("Projected CDML did not produce the durable Plus item")


#============================================
def _plus_facts(cdml_text: str) -> tuple[str, str, str, str]:
	"""Read root Plus fields and preserved values through hardened XML helpers."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="compat")
	document = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for element in document.documentElement.childNodes:
		if (
			element.nodeType == element.ELEMENT_NODE
			and (element.localName or element.tagName) == "plus"
			and element.getAttribute("id") == "plus1"
		):
			font = next(
				child for child in element.childNodes
				if child.nodeType == child.ELEMENT_NODE
				and (child.localName or child.tagName) == "font"
			)
			return (
				element.getAttribute("font_size"), element.getAttribute("color"),
				element.getAttribute("keep"), font.getAttribute("keep"),
			)
	raise AssertionError("Accepted CDML has no durable Plus target")


#============================================
def _selected_plus_ids(session: object) -> set[str]:
	"""Return durable IDs from selected current Plus wrappers."""
	return {
		item.document_object_model.object_id
		for item in session.scene.selectedItems()
		if getattr(getattr(item, "document_object_model", None), "kind", None) == "plus"
	}


#============================================
def _accept_plus_changes(
		monkeypatch: pytest.MonkeyPatch,
		changes: tuple[tuple[str, object], ...],
		observed: dict[str, object] | None = None,
		activate: object | None = None,
		) -> None:
	"""Make PlusDialog expose public values and one immutable accepted intent."""
	def accept(dialog: object) -> int:
		"""Observe initialized values and optionally activate another tab."""
		if observed is not None:
			observed["font_size"] = dialog.get_font_size()
			observed["color"] = dialog.get_color()
		if callable(activate):
			activate()
		return PySide6.QtWidgets.QDialog.DialogCode.Accepted

	def returned_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
		"""Return caller-owned plain Plus intent."""
		return changes

	monkeypatch.setattr(bkchem_qt.dialogs.plus_dialog.PlusDialog, "exec", accept)
	monkeypatch.setattr(bkchem_qt.dialogs.plus_dialog.PlusDialog, "changes", returned_changes)


#============================================
def test_object_configure_uses_backend_history_and_restores_plus_selection(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Real Configure patches authority without Qt undo and selects the fresh Plus."""
	session = _install_native_session(main_window)
	observed = {}
	try:
		old_document = session.document
		old_item = _plus_item(session)
		old_item.setSelected(True)
		_accept_plus_changes(
			monkeypatch, (("font_size", 20), ("color", "#AABBCC")), observed,
		)
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		persistent_facts = {
			"dialog": observed,
			"backend": _plus_facts(session.backend_snapshot.cdml),
			"backend_undo": session.can_undo_backend,
		}
		projection_facts = {
			"replaced": session.document is not old_document and _plus_item(session) is not old_item,
			"selection": _selected_plus_ids(session),
			"qt_undo": session.document.undo_stack.canUndo(),
		}

		assert persistent_facts == {
			"dialog": {"font_size": 13, "color": "#112233"},
			"backend": ("20", "#aabbcc", "yes", "font"),
			"backend_undo": True,
		}
		assert projection_facts == {
			"replaced": True, "selection": {"plus1"}, "qt_undo": False,
		}
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_modal_plus_configure_remains_bound_to_origin_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Tab activation during the modal dialog cannot redirect accepted intent."""
	origin = _install_native_session(main_window)
	other = None
	other_before = {}
	try:
		_plus_item(origin).setSelected(True)
		def activate_other() -> None:
			"""Open and activate one independent public tab during the dialog."""
			main_window.on_new()
			active = next(session for session in main_window.sessions if session is not origin)
			other_before["snapshot"] = active.backend_snapshot

		_accept_plus_changes(monkeypatch, (("font_size", 21),), activate=activate_other)
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		other = next(session for session in main_window.sessions if session is not origin)

		assert _plus_facts(origin.backend_snapshot.cdml)[0] == "21"
		assert other.backend_snapshot == other_before["snapshot"]
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)


#============================================
def test_captured_plus_action_is_typed_unavailable_after_close(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained origin capability cannot mutate another tab after close."""
	origin = _install_native_session(main_window)
	captured = main_window.capture_plus_properties_for_view(origin.view, "plus1")
	if captured is None:
		raise AssertionError("Live Plus capability was unavailable")
	expected_revision, submit = captured
	main_window.on_new()
	other = next(session for session in main_window.sessions if session is not origin)
	other_before = other.backend_snapshot
	closed = main_window.close_session_at(main_window.sessions.index(origin))
	outcome = submit(expected_revision, "plus1", (("font_size", 22),))

	assert closed and outcome.status == "unavailable" and outcome.commit is None
	assert other.backend_snapshot == other_before


#============================================
def test_projection_failure_retries_only_accepted_plus_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Retry reprojects accepted state without replaying the Plus patch."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window, theme_manager=main_window._theme_manager,
		prefs=main_window._prefs, mode_host=main_window, prepared_native_cdml=prepared,
	)

	def unavailable(_snapshot: object) -> object:
		"""Report one post-acceptance projection installation failure."""
		return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
			bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
			bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
		)

	try:
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, unavailable),
		)
		outcome = session.submit_plus_properties_patch(
			session.backend_snapshot.revision, "plus1", (("font_size", 23),),
		)
		if outcome.commit is None:
			raise AssertionError("Accepted Plus patch returned no backend snapshot")
		accepted = outcome.commit.snapshot

		def resubmission_must_not_run(*_args: object) -> object:
			"""Expose any retry that re-enters the public Plus patch action."""
			raise AssertionError("Projection retry resubmitted the accepted Plus patch")

		monkeypatch.setattr(session, "submit_plus_properties_patch", resubmission_must_not_run)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		retry = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and outcome.submitted
		assert (
			retry.status == "accepted" and session.backend_snapshot == accepted
			and _plus_facts(accepted.cdml)[0] == "23"
			and _selected_plus_ids(session) == {"plus1"}
		)
	finally:
		session.dispose()
