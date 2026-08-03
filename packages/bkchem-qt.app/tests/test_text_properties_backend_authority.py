"""Focused Qt behavior for backend-authoritative plain Text Configure."""

# Standard Library
import gc

# PIP3 modules
import PySide6.QtWidgets
import pytest
import shiboken6

# local repo modules
import oasa.cdml_document
import oasa.safe_xml

import bkchem_qt.actions.object_actions
import bkchem_qt.canvas.items.text_item
import bkchem_qt.dialogs.text_dialog
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle


_CDML = (
	'<cdml version="26.07"><molecule id="m1"><atom id="a1" name="C">'
	'<point x="1cm" y="1cm"/></atom></molecule><text id="text1" keep="yes">'
	'<point x="3cm" y="4cm"/><font family="Arial" size="13" color="#112233" '
	'keep="font"/><ftext>  Original label  </ftext></text></cdml>'
)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one projected native-CDML session with a durable Text target."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native Text CDML projection is unavailable")
	return registered


#============================================
def _text_item(session: object) -> object:
	"""Return the current durable Text projection."""
	for item in session.scene.items():
		model = getattr(item, "document_object_model", None)
		if (
			isinstance(item, bkchem_qt.canvas.items.text_item.TextItem)
			and getattr(model, "kind", None) == "text"
			and getattr(model, "object_id", None) == "text1"
		):
			return item
	raise AssertionError("Projected CDML did not produce the durable Text item")


#============================================
def _selected_text_ids(session: object) -> set[str]:
	"""Read durable Text IDs from current selected presentation projections."""
	return {
		item.document_object_model.object_id
		for item in session.scene.selectedItems()
		if getattr(getattr(item, "document_object_model", None), "kind", None) == "text"
	}


#============================================
def _text_facts(cdml_text: str) -> tuple[str, tuple[str, str, str], tuple[str, str]]:
	"""Read durable Text content and properties through hardened CDML helpers."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="compat")
	document = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for element in document.documentElement.childNodes:
		if (
			element.nodeType != element.ELEMENT_NODE
			or (element.localName or element.tagName) != "text"
			or element.getAttribute("id") != "text1"
		):
			continue
		font = next(
			child for child in element.childNodes
			if child.nodeType == child.ELEMENT_NODE
			and (child.localName or child.tagName) == "font"
		)
		ftext = next(
			child for child in element.childNodes
			if child.nodeType == child.ELEMENT_NODE
			and (child.localName or child.tagName) == "ftext"
		)
		plain = "".join(
			child.data for child in ftext.childNodes
			if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE)
		)
		return (
			plain,
			(font.getAttribute("family"), font.getAttribute("size"), font.getAttribute("color")),
			(element.getAttribute("keep"), font.getAttribute("keep")),
		)
	raise AssertionError("Accepted CDML has no durable Text target")


#============================================
def _accept_text_changes(
		monkeypatch: pytest.MonkeyPatch, changes: tuple[tuple[str, object], ...],
		observed: list[tuple[str, str, int, str]] | None = None,
		activate: object | None = None,
		) -> None:
	"""Make TextDialog expose its public values and accept immutable intent."""
	def accept(dialog: object) -> int:
		"""Observe initialized values and optionally change the active tab."""
		if observed is not None:
			observed.append((
				dialog.get_text(), dialog.get_font_family(),
				dialog.get_font_size(), dialog.get_font_color(),
			))
		if callable(activate):
			activate()
		return PySide6.QtWidgets.QDialog.DialogCode.Accepted

	def returned_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
		"""Return one caller-owned plain Text intent."""
		return changes

	monkeypatch.setattr(bkchem_qt.dialogs.text_dialog.TextDialog, "exec", accept)
	monkeypatch.setattr(bkchem_qt.dialogs.text_dialog.TextDialog, "changes", returned_changes)


#============================================
def test_text_dialog_reports_only_values_changed_after_widget_initialization(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Qt normalization is baseline state; a user edit reports only its field."""
	dialog = bkchem_qt.dialogs.text_dialog.TextDialog(
		"Initial", 999, font_family="Definitely Missing BKChem Test Font",
	)
	try:
		untouched = dialog.changes()
		dialog._text_edit.setPlainText("Changed")

		assert untouched == ()
		assert dialog.changes() == (("text", "Changed"),)
	finally:
		assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, dialog)


#============================================
def test_object_configure_projects_authoritative_text_values_and_selection(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Public Configure submits dialog values and selects the fresh Text wrapper."""
	session = _install_native_session(main_window)
	observed = []
	try:
		old_document = session.document
		old_item = _text_item(session)
		old_item.setSelected(True)
		_accept_text_changes(monkeypatch, (
			("text", "Configured label"), ("font_family", "Courier"),
			("font_size", 20), ("font_color", "#AABBCC"),
		), observed)
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		# The accepted candidate has returned.  Its projection survives collection
		# because the installed Document owns active graphics wrappers explicitly.
		gc.collect()
		facts = _text_facts(session.backend_snapshot.cdml)
		current_text = _text_item(session)

		assert observed == [("  Original label  ", "Arial", 13, "#112233")]
		assert (
			facts == ("Configured label", ("Courier", "20", "#aabbcc"), ("yes", "font"))
			and session.document is not old_document and current_text is not old_item
			and _selected_text_ids(session) == {"text1"}
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_repeated_text_configure_keeps_the_installed_wrapper_alive_through_collection(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Every accepted Configure replacement keeps its selected projection wrapper live."""
	session = _install_native_session(main_window)
	changes = iter((
		(("text", "First replacement"),),
		(("text", "Second replacement"),),
	))
	try:
		_text_item(session).setSelected(True)
		_accept_text_changes(monkeypatch, next(changes))
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		gc.collect()
		first_item = _text_item(session)
		first_is_current = (
			shiboken6.isValid(first_item)
			and session.document.is_current_projection_item(first_item)
			and _selected_text_ids(session) == {"text1"}
		)
		_accept_text_changes(monkeypatch, next(changes))
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		gc.collect()
		second_item = _text_item(session)

		assert first_is_current
		assert (
			second_item is not first_item
			and shiboken6.isValid(second_item)
			and session.document.is_current_projection_item(second_item)
			and _selected_text_ids(session) == {"text1"}
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_backend_undo_restores_exact_preconfigure_text_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Plain Configure uses backend history and undo restores exact complete CDML."""
	session = _install_native_session(main_window)
	try:
		before = session.backend_snapshot
		_text_item(session).setSelected(True)
		_accept_text_changes(monkeypatch, (("text", "Changed"),))
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		undo = session.undo_backend()

		assert undo.status == "accepted" and session.backend_snapshot.cdml == before.cdml
		assert _text_facts(session.backend_snapshot.cdml)[0] == "  Original label  "
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_modal_configure_remains_bound_to_origin_when_activation_changes(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A captured dialog intent cannot retarget to a newly active tab."""
	origin = _install_native_session(main_window)
	other = None
	try:
		_text_item(origin).setSelected(True)
		def activate_other() -> None:
			"""Open and activate one independent public tab while the dialog is open."""
			main_window.on_new()

		_accept_text_changes(
			monkeypatch, (("text", "Origin only"),), activate=activate_other,
		)
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		other = next(session for session in main_window.sessions if session is not origin)

		assert _text_facts(origin.backend_snapshot.cdml)[0] == "Origin only"
		assert "Origin only" not in other.backend_snapshot.cdml
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)


#============================================
def test_captured_text_action_is_typed_unavailable_after_public_close(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained plain Text capability cannot act after its tab closes."""
	origin = _install_native_session(main_window)
	captured = main_window.capture_text_properties_for_view(origin.view, "text1")
	if captured is None:
		raise AssertionError("Live Text capability was unavailable")
	expected_revision, submit = captured
	main_window.on_new()
	other = next(session for session in main_window.sessions if session is not origin)
	other_before = other.backend_snapshot
	closed = main_window.close_session_at(main_window.sessions.index(origin))
	outcome = submit(expected_revision, "text1", (("text", "late"),))

	assert closed and outcome.status == "unavailable" and outcome.commit is None
	assert other.backend_snapshot == other_before


#============================================
def test_session_rejects_text_payload_target_mismatch_before_backend_mutation(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""The public request grammar correlates its one durable Text target exactly."""
	session = _install_native_session(main_window)
	try:
		before = session.backend_snapshot
		request = bkchem_qt.models.document_session.PersistentOperationRequest(
			"text.properties.patch", "Edit Text Properties",
			(
				("expected_revision", before.revision), ("text_id", "text1"),
				("changes", (("text", "wrong target"),)),
			),
			frozenset({("presentation", "other")}),
		)
		outcome = session.submit_persistent_operation(request)

		assert outcome.status == "rejected" and outcome.failure_kind == "validation"
		assert session.backend_snapshot == before
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_projection_failure_retries_only_the_exact_accepted_text_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Accepted Text state survives projection failure and retry does not resubmit."""
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
		outcome = session.submit_text_properties_patch(
			session.backend_snapshot.revision, "text1", (("text", "Accepted"),),
		)
		if outcome.commit is None:
			raise AssertionError("Accepted Text patch returned no backend snapshot")
		accepted = outcome.commit.snapshot

		def resubmission_must_not_run(*_args: object) -> object:
			"""Expose any retry that re-enters the public Text patch action."""
			raise AssertionError("Projection retry resubmitted the accepted Text patch")

		monkeypatch.setattr(session, "submit_text_properties_patch", resubmission_must_not_run)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		retry = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and outcome.submitted
		assert (
			retry.status == "accepted" and session.backend_snapshot == accepted
			and _text_facts(accepted.cdml)[0] == "Accepted"
			and _selected_text_ids(session) == {"text1"}
		)
	finally:
		session.dispose()
