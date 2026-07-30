"""Command-backed File > Properties paper behavior."""

# Standard Library
import re

# PIP3 modules
import pytest
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.file_actions
import bkchem_qt.dialogs.paper_properties_dialog
import bkchem_qt.io.snapshot_render
import bkchem_qt.models.document_session
import oasa.cdml_document
import oasa.cdml_render
import oasa.safe_xml


_MIXED_PAPER_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <v:paper type="vendor-sheet" v:keep="before"><v:child>opaque</v:child></v:paper>
 <standard paper_type="Letter" paper_orientation="landscape" />
 <v:surrounding id="vendor-before">keep</v:surrounding>
 <paper type="legacy-sheet" orientation="portrait" crop_svg="yes" v:raw="keep"><v:extension key="x">payload</v:extension></paper>
 <v:surrounding id="vendor-after">keep</v:surrounding>
 <paper type="A4" orientation="landscape" v:later="untouched"><v:later /></paper>
 <viewport viewport="0 0 10 10" />
</cdml>
"""


#============================================
def _direct_children(cdml_text: str) -> tuple[object, ...]:
	"""Read direct records through the hardened complete-CDML parser."""
	root = oasa.safe_xml.parse_dom_from_string(cdml_text).documentElement
	return tuple(
		child for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)


#============================================
def _direct_core_papers(cdml_text: str) -> tuple[object, ...]:
	"""Return direct editable CDML paper records in document order."""
	return tuple(
		child for child in _direct_children(cdml_text)
		if (child.localName or child.tagName) == "paper"
		and child.namespaceURI in (None, "", oasa.cdml_document.CDML_NAMESPACE_URI)
	)


#============================================
def _svg_mm_dimension(artifact: bytes, attribute: str) -> float:
	"""Read one generated SVG page dimension as a visual-output observation."""
	match = re.search(
		(rb'\b' + attribute.encode("ascii") + rb'="([0-9.]+)mm"'), artifact,
	)
	assert match is not None
	return float(match.group(1))


#============================================
def _install_backend_snapshot(main_window: object, session: object, complete_cdml: str) -> None:
	"""Install one backend CDML snapshot through the normal disposable projection path."""
	commit = session.commit_complete_candidate(complete_cdml)
	assert main_window._replace_session_projection(session, commit.snapshot)


#============================================
def _custom_paper() -> dict[str, str]:
	"""Return raw custom-paper attributes with one retained unknown field."""
	return {
			"type": "custom",
			"orientation": "landscape",
			"size_x": "100",
			"size_y": "250",
			"crop_svg": "1",
			"crop_margin": "18",
			"use_real_minus": "1",
			"replace_minus": "1",
			"vendor_extension": "kept",
	}


#============================================
#============================================
def test_cancelled_paper_properties_leave_document_unmodified(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Cancelling the file action cannot create a paper mutation or undo entry."""
	session = main_window._active_session
	before = session.backend_snapshot
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"exec", lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Rejected,
	)
	bkchem_qt.actions.file_actions._document_properties(main_window)
	assert session.backend_snapshot == before


#============================================
def test_invalid_custom_paper_dialog_does_not_accept_or_mutate_model(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A zero custom dimension remains in the dialog and is rejected in place."""
	paper = _custom_paper()
	dialog = bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog(
		paper, oasa.cdml_document.paper_catalog(),
	)
	try:
		dialog._width_spin.setValue(0.0)
		dialog.accept()
		assert dialog.result() == int(PySide6.QtWidgets.QDialog.DialogCode.Rejected)
	finally:
		dialog.deleteLater()
		qapp.processEvents()


#============================================
#============================================
def test_malformed_or_large_retained_paper_values_survive_unrelated_edit(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The dialog preserves raw values it cannot safely place in Qt editors."""
	paper = {
			"type": "custom", "size_x": "not-a-number",
			"size_y": "999999999999999999999999999999999999999999999999999",
			"crop_margin": "999999999999", "crop_svg": "0",
	}
	dialog = bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog(
		paper, oasa.cdml_document.paper_catalog(),
	)
	try:
		dialog._crop_svg_check.setChecked(True)
		assert dialog.changes() == (("crop_svg", True),)
	finally:
		dialog.deleteLater()
		qapp.processEvents()


#============================================
def test_dialog_preserves_unsupported_type_until_a_valid_authoring_choice(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""An unsupported raw type creates no patch until a user chooses a catalog name."""
	dialog = bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog(
		{"type": "legacy-sheet", "orientation": "sideways"},
		oasa.cdml_document.paper_catalog(),
	)
	try:
		assert dialog.changes() == ()
		dialog._type_combo.setCurrentText("C10")
		assert dialog.changes() == (("type", "C10"),)
	finally:
		dialog.deleteLater()
		qapp.processEvents()


#============================================
def test_dialog_leaves_raw_boolean_and_absent_paper_fields_out_of_its_patch(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Unedited compatibility values stay backend-owned rather than normalized."""
	dialog = bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog(
		{"type": "legacy-sheet", "crop_svg": "yes"},
		oasa.cdml_document.paper_catalog(),
	)
	try:
		assert dialog.changes() == ()
	finally:
		dialog.deleteLater()
		qapp.processEvents()


#============================================
def test_accepted_file_properties_commit_reprojects_and_uses_backend_undo(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Accepted paper properties use backend history rather than a local command."""
	session = main_window._active_session
	before = session.backend_snapshot
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"exec", lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Accepted,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"changes", lambda _dialog: (
			("type", "custom"), ("dimensions", (100.0, 250.0)),
			("orientation", "landscape"), ("crop_svg", True),
			("crop_margin", 18), ("use_real_minus", True),
			("replace_minus", True),
		),
	)
	bkchem_qt.actions.file_actions._document_properties(main_window)
	accepted = session.backend_snapshot
	projected_type = session.document.paper.attributes["type"]
	dirty_after_acceptance = session.document.dirty
	undo = session.undo_backend()

	assert (accepted.revision, projected_type, dirty_after_acceptance) == (
		before.revision + 1, "custom", True,
	)
	assert (undo.status, session.backend_snapshot.cdml) == ("accepted", before.cdml)


#============================================
def test_file_properties_invokes_the_backend_patch_not_a_complete_candidate(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The action submits only explicit intent to OASA's paper patch executor."""
	session = main_window._active_session
	backend = session._backend_session
	patch = backend.patch_paper_properties
	requests = []

	def record_patch(request: object) -> object:
		"""Record the typed boundary value before ordinary backend execution."""
		requests.append(request)
		return patch(request)

	def forbid_complete_candidate(_prepared: object) -> object:
		"""Make an obsolete complete-document paper route fail immediately."""
		raise AssertionError("Paper Properties reached the complete-candidate route")

	monkeypatch.setattr(backend, "patch_paper_properties", record_patch)
	monkeypatch.setitem(
		session._operation_commit_executors, "complete-candidate", forbid_complete_candidate,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"exec", lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Accepted,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"changes", lambda _dialog: (("crop_svg", True),),
	)
	bkchem_qt.actions.file_actions._document_properties(main_window)

	assert len(requests) == 1
	assert (
		isinstance(requests[0], oasa.cdml_document.CDMLPaperPropertiesPatch)
		and requests[0].changes == (("crop_svg", True),)
	)


#============================================
def test_absent_paper_uses_backend_default_observation_and_explicit_field_patch(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An absent paper displays and creates the backend's exact effective default."""
	session = main_window._active_session
	_install_backend_snapshot(main_window, session, """\
<cdml><standard paper_type="Letter" paper_orientation="landscape" /><viewport /></cdml>""")
	context = session.paper_properties_context()
	dialog = bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog(
		context["attributes"], session.paper_catalog(), context["default_type"],
		context["default_orientation"],
	)
	try:
		assert (
			dialog._type_combo.currentText(), dialog._orientation_combo.currentText(), dialog.changes(),
		) == ("Letter", "landscape", ())
	finally:
		dialog.deleteLater()
		qapp.processEvents()
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"exec", lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Accepted,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"changes", lambda _dialog: (("crop_margin", 12),),
	)
	bkchem_qt.actions.file_actions._document_properties(main_window)
	paper, = _direct_core_papers(session.backend_snapshot.cdml)
	assert (
		paper.getAttribute("type"), paper.getAttribute("orientation"),
		paper.getAttribute("crop_margin"),
	) == ("Letter", "landscape", "12")


#============================================
def test_live_action_preserves_mixed_paper_envelope_at_direct_core_boundary(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""One patch changes only the first direct core paper amid opaque paper-like XML."""
	session = main_window._active_session
	_install_backend_snapshot(main_window, session, _MIXED_PAPER_CDML)
	before = session.backend_snapshot
	before_children = tuple(child.toxml() for child in _direct_children(before.cdml))
	first_before, second_before = _direct_core_papers(before.cdml)
	assert session.document.paper.attributes == {
		"type": "legacy-sheet", "orientation": "portrait", "crop_svg": "yes", "v:raw": "keep",
	}
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"exec", lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Accepted,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"changes", lambda _dialog: (("crop_margin", 17),),
	)
	bkchem_qt.actions.file_actions._document_properties(main_window)
	after = session.backend_snapshot
	first_after, second_after = _direct_core_papers(after.cdml)
	after_children = tuple(child.toxml() for child in _direct_children(after.cdml))

	assert after.revision == before.revision + 1
	assert first_after.getAttribute("type") == "legacy-sheet"
	assert first_after.getAttribute("orientation") == "portrait"
	assert first_after.getAttribute("crop_svg") == "yes"
	assert first_after.getAttribute("crop_margin") == "17"
	assert first_after.getAttribute("v:raw") == "keep"
	assert tuple(
		child.toxml() for child in first_after.childNodes
		if child.nodeType == child.ELEMENT_NODE
	) == tuple(
		child.toxml() for child in first_before.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	assert second_after.toxml() == second_before.toxml()
	assert after_children[0] == before_children[0]
	assert after_children[2] == before_children[2]
	assert after_children[4] == before_children[4]
	assert tuple(child.tagName for child in _direct_children(after.cdml)) == tuple(
		child.tagName for child in _direct_children(before.cdml)
	)


#============================================
def test_stale_changed_paper_patch_keeps_snapshot_history_and_projection(
		main_window: object,
		) -> None:
	"""A stale nonempty paper request cannot alter the accepted Qt/backend state."""
	session = main_window._active_session
	stale_revision = session.backend_snapshot.revision
	accepted = session.submit_persistent_operation(
		bkchem_qt.models.document_session.build_paper_properties_request(
			stale_revision, (("crop_svg", True),),
		),
	)
	before = session.backend_snapshot
	document = session.document
	history = session._backend_history
	rejected = session.submit_persistent_operation(
		bkchem_qt.models.document_session.build_paper_properties_request(
			stale_revision, (("crop_margin", 9),),
		),
	)

	assert accepted.status == "accepted"
	assert (
		rejected.status == "rejected"
		and session.backend_snapshot == before
		and session.document is document
		and session._backend_history == history
	)


#============================================
@pytest.mark.parametrize("changes, expected_width_mm, expected_height_mm", (
	((("type", "C10"),), 28.0, 40.0),
	((("type", "custom"), ("dimensions", (200.5, 300.25))), 200.5, 300.25),
))
def test_live_scene_and_snapshot_render_share_backend_paper_semantics(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		changes: tuple[tuple[str, object], ...], expected_width_mm: float,
		expected_height_mm: float,
		) -> None:
	"""A live scene and detached SVG use the same backend catalog and dimensions."""
	session = main_window._active_session
	_install_backend_snapshot(
		main_window, session, '<cdml><paper type="A4" orientation="portrait" /></cdml>',
	)
	outcome = session.submit_persistent_operation(
		bkchem_qt.models.document_session.build_paper_properties_request(
			session.backend_snapshot.revision, changes,
		),
	)
	page = session.scene.paper_rect
	result = bkchem_qt.io.snapshot_render.render_request(
		oasa.cdml_render.CDMLRenderRequest(session.backend_snapshot, "svg"),
	)
	assert isinstance(result, oasa.cdml_render.CDMLRenderResult)
	assert result.artifact is not None
	assert outcome.status == "accepted"
	assert page.width() == pytest.approx(expected_width_mm * 72.0 / 25.4)
	assert page.height() == pytest.approx(expected_height_mm * 72.0 / 25.4)
	assert _svg_mm_dimension(result.artifact, "width") == pytest.approx(expected_width_mm, abs=0.2)
	assert _svg_mm_dimension(result.artifact, "height") == pytest.approx(expected_height_mm, abs=0.2)
	qapp.processEvents()


#============================================
def test_unchanged_paper_properties_leave_authoritative_state_intact(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Canonical paper no-op leaves revision, history, and projection untouched."""
	session = main_window._active_session
	initial = session.submit_persistent_operation(
		bkchem_qt.models.document_session.build_paper_properties_request(
			session.backend_snapshot.revision, (),
		),
	)
	before = session.backend_snapshot
	document = session.document
	history = session._backend_history
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"exec", lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Accepted,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog,
		"changes", lambda _dialog: (),
	)
	bkchem_qt.actions.file_actions._document_properties(main_window)

	assert initial.status == "accepted"
	assert (
		session.backend_snapshot == before
		and session.document is document
		and session._backend_history == history
	)


#============================================
def test_replaced_session_after_dialog_acceptance_cannot_retarget_paper_edit(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A dialog accepted after tab replacement cannot mutate either session."""
	source = main_window._active_session
	before = source.backend_snapshot

	def replace_tab(_dialog: object) -> int:
		"""Replace the active session while the detached dialog remains open."""
		main_window._on_new()
		return int(PySide6.QtWidgets.QDialog.DialogCode.Accepted)

	monkeypatch.setattr(
		bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog, "exec", replace_tab,
	)
	bkchem_qt.actions.file_actions._document_properties(main_window)

	assert source.backend_snapshot == before
	assert main_window._active_session.backend_snapshot.revision == 0
