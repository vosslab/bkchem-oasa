"""Usability evidence for authoritative Qt document drawing styles."""

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.config.drawing_standard_preferences
import bkchem_qt.dialogs.drawing_standard_dialog
import bkchem_qt.models.document_session
import oasa.cdml_document
import oasa.cdml_presentation_insert
import oasa.cdml_standard
import oasa.safe_xml


_CDML = """\
<cdml version="26.07">
 <standard line_width="1px" font_size="12" font_family="Helvetica"
  line_color="#112233" area_color="">
  <bond width="6px" wedge-width="5px" double-ratio="0.75" />
  <atom show_hydrogens="0" />
 </standard>
 <molecule id="m1">
  <atom id="a1" name="O"><point x="0cm" y="0cm" /></atom>
  <atom id="a2" name="N"><point x="1cm" y="0cm" />
   <font size="9" color="#abcdef" />
  </atom>
  <bond id="b1" start="a1" end="a2" type="n2" />
 </molecule>
</cdml>
"""

_MULTI_CDML = """\
<cdml version="26.07">
 <standard line_width="1px" font_size="12" font_family="Helvetica"
  line_color="#112233" area_color="">
  <bond width="6px" wedge-width="5px" double-ratio="0.75" />
  <atom show_hydrogens="0" />
 </standard>
 <molecule id="m1"><atom id="a1" name="O">
  <point x="0cm" y="0cm" /></atom></molecule>
 <molecule id="m2"><atom id="a2" name="N">
  <point x="2cm" y="0cm" /></atom></molecule>
</cdml>
"""


#============================================
def _install_native_session(main_window: object, cdml: str = _CDML) -> object:
	"""Register one synchronized document with inherited and explicit styles."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(cdml)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	return main_window._register_session(session, activate=True)


#============================================
def _menu_action(main_window: object, label: str) -> object:
	"""Find one visible action by walking the public menu tree."""
	pending = list(main_window.menuBar().actions())
	while pending:
		action = pending.pop(0)
		if action.text().replace("&", "") == label:
			return action
		menu = action.menu()
		if menu is not None:
			pending.extend(menu.actions())
	raise AssertionError("visible menu action is missing: %s" % label)


#============================================
def _projection_facts(session: object) -> tuple[object, ...]:
	"""Return effective style facts from the current disposable projection."""
	molecule, = session.document.molecules
	first, second = molecule.atoms
	bond, = molecule.bonds
	return (
		first.font_size, first.font_family, first.line_color, first.show_hydrogens,
		second.font_size, second.line_color, bond.line_width, bond.bond_width,
		bond.wedge_width, bond.double_length_ratio,
	)


#============================================
def _accept_changes(
		monkeypatch: pytest.MonkeyPatch,
		changes: tuple[tuple[str, object], ...], activate: object | None = None,
		application_scope: str = "defaults", override_fields: tuple[str, ...] = (),
		personal_action: str = "none",
		) -> None:
	"""Make the real modal action accept caller-provided plain intent."""
	def accept(_dialog: object) -> int:
		if callable(activate):
			activate()
		return PySide6.QtWidgets.QDialog.DialogCode.Accepted

	monkeypatch.setattr(
		bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog, "exec", accept,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog,
		"changes", lambda _dialog: changes,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog,
		"application_scope", lambda _dialog: application_scope,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog,
		"override_fields", lambda _dialog: override_fields,
	)
	monkeypatch.setattr(
		bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog,
		"personal_action", lambda _dialog: personal_action,
	)


#============================================
def _select_molecule(session: object, molecule_id: str) -> None:
	"""Select one current atom projection from the requested molecule root."""
	for item in session.scene.items():
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			continue
		molecule = session.document.molecule_for_graphics_item(item)
		if molecule.mol_id == molecule_id:
			item.setSelected(True)
			return
	raise AssertionError("molecule projection is missing: %s" % molecule_id)


#============================================
def _element_by_id(cdml: str, identifier: str) -> object:
	"""Return one exact serialized element by durable ID."""
	document = oasa.safe_xml.parse_dom_from_string(cdml)
	matches = [
		element for element in document.getElementsByTagName("*")
		if element.getAttribute("id") == identifier
	]
	assert len(matches) == 1
	return matches[0]


#============================================
def test_new_presentations_use_present_document_defaults() -> None:
	"""New artwork authors the current standard instead of hard-coded Qt colors."""
	base = (
		'<cdml version="26.07"><standard line_width="2.5px" font_size="17" '
		'font_family="Courier" line_color="#224466" area_color="#ddeeff" />'
		'</cdml>'
	)
	backend = oasa.cdml_document.CDMLDocumentSession.load(base)
	arrow_result = oasa.cdml_presentation_insert.insert_arrow(
		backend,
		oasa.cdml_presentation_insert.CDMLArrowInsertRequest(
			backend.revision, "normal", False, ((0.0, 0.0), (20.0, 0.0)),
		),
	)
	arrow = _element_by_id(
		arrow_result.snapshot.cdml, arrow_result.presentation_ids[0],
	)
	text_result = oasa.cdml_presentation_insert.insert_text(
		backend,
		oasa.cdml_presentation_insert.CDMLTextInsertRequest(
			backend.revision, (0.0, 0.0), "Note",
		),
	)
	text = _element_by_id(
		text_result.snapshot.cdml, text_result.presentation_ids[0],
	)
	vector_result = oasa.cdml_presentation_insert.insert_geometric(
		backend,
		oasa.cdml_presentation_insert.CDMLGeometricInsertRequest(
			backend.revision, "rect", ((0.0, 0.0), (20.0, 20.0)),
		),
	)
	vector = _element_by_id(
		vector_result.snapshot.cdml, vector_result.presentation_ids[0],
	)

	assert (arrow.getAttribute("width"), arrow.getAttribute("color")) == (
		"2.5", "#224466",
	)
	font = text.getElementsByTagName("font")[0]
	assert (
		font.getAttribute("family"), font.getAttribute("size"),
		font.getAttribute("color"), text.getAttribute("background-color"),
	) == ("Courier", "17", "#224466", "#ddeeff")
	assert (
		vector.getAttribute("width"), vector.getAttribute("line_color"),
		vector.getAttribute("area_color"),
	) == ("2.5", "#224466", "#ddeeff")


#============================================
def test_new_presentation_gesture_receives_the_backend_standard_observation(
		main_window: object,
		) -> None:
	"""The session passes stable values instead of reparsing retained standard XML."""
	session = _install_native_session(main_window)
	try:
		outcome = session.commit_arrow((0.0, 40.0), (40.0, 40.0))
		assert outcome.status == "accepted"
		arrow_ids = [
			record.identifier
			for record in oasa.cdml_document.CDMLDocument.parse(
				session.backend_snapshot.cdml,
			).objects()
			if record.local_name == "arrow"
		]
		arrow = _element_by_id(session.backend_snapshot.cdml, arrow_ids[-1])
		assert (arrow.getAttribute("width"), arrow.getAttribute("color")) == (
			"1", "#112233",
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_visible_document_style_action_reprojects_and_undoes_inherited_values(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A user-visible Apply changes CDML, dirty state, projection, and history."""
	session = _install_native_session(main_window)
	try:
		before = session.backend_snapshot
		old_document = session.document
		action = _menu_action(main_window, "Document Drawing Style...")
		_accept_changes(monkeypatch, (
			("line_width", 2.0), ("font_size", 18),
			("font_family", "Courier"), ("line_color", "#445566"),
			("area_color", "#ffffff"), ("bond_width", 8.0),
			("wedge_width", 7.0), ("double_ratio", 0.5),
			("show_hydrogens", True),
		))

		assert action.isEnabled()
		action.trigger()
		qapp.processEvents()
		after = session.backend_snapshot
		projected = _projection_facts(session)
		standard = session.drawing_standard()
		undone = session.undo_backend()

		assert after.revision == before.revision + 1 and after.is_dirty
		assert session.document is not old_document
		assert projected[:6] == (18, "Courier", "#445566", True, 9, "#abcdef")
		assert projected[6:] == pytest.approx((2.0, 8.0, 7.0, 0.5), rel=1e-5)
		assert (standard.font_size, standard.line_color, standard.area_color) == (
			18, "#445566", "#ffffff",
		)
		assert session.document.undo_stack.canUndo() is False
		assert undone.status == "accepted" and session.backend_snapshot.cdml == before.cdml
		assert _projection_facts(session) == (
			12, "Helvetica", "#112233", False,
			9, "#abcdef", 1.0, 6.0, 5.0, 0.75,
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_cancelled_document_style_action_has_no_side_effects(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Cancel leaves revision, dirty state, projection, and backend history alone."""
	session = _install_native_session(main_window)
	try:
		before = session.backend_snapshot
		old_document = session.document
		monkeypatch.setattr(
			bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog,
			"exec", lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Rejected,
		)
		_menu_action(main_window, "Document Drawing Style...").trigger()
		qapp.processEvents()

		assert session.backend_snapshot == before
		assert session.document is old_document and not session.can_undo_backend
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_document_style_accept_cannot_retarget_after_tab_switch(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A tab switch during the modal dialog leaves both documents unchanged."""
	origin = _install_native_session(main_window)
	other = None
	other_before = {}
	try:
		origin_before = origin.backend_snapshot
		def activate_other() -> None:
			"""Create and capture another active document during the modal dialog."""
			main_window.on_new()
			active = main_window._active_session
			other_before["session"] = active
			other_before["snapshot"] = active.backend_snapshot

		_accept_changes(monkeypatch, (("font_size", 30),), activate_other)
		_menu_action(main_window, "Document Drawing Style...").trigger()
		qapp.processEvents()
		other = other_before["session"]

		assert origin.backend_snapshot == origin_before
		assert other.backend_snapshot == other_before["snapshot"]
		assert "no longer applies" in main_window.statusBar().currentMessage()
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)


#============================================
def test_document_style_dialog_keeps_invalid_color_visible(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Invalid text stays editable with an actionable inline recovery message."""
	backend = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	observation = backend.drawing_standard(
		oasa.cdml_standard.CDMLDrawingStandardQuery(0),
	)
	dialog = bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog(observation)
	try:
		dialog._line_color_edit.setText("black")
		dialog.accept()

		assert dialog.result() == int(PySide6.QtWidgets.QDialog.DialogCode.Rejected)
		assert dialog._line_color_edit.text() == "black"
		assert "hexadecimal color" in dialog._error_label.text()
	finally:
		dialog.deleteLater()
		qapp.processEvents()


#============================================
def test_selected_scope_materializes_backend_overrides_and_preserves_selection(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Selected scope is one undoable CDML commit, never a Qt model rewrite."""
	session = _install_native_session(main_window, _MULTI_CDML)
	try:
		before = session.backend_snapshot
		assert session.retry_current_backend_projection().status == "accepted"
		_select_molecule(session, "m1")
		_accept_changes(
			monkeypatch, (("font_size", 18), ("line_color", "#445566")),
			application_scope="selected",
			override_fields=("font_size", "line_color"),
		)
		_menu_action(main_window, "Document Drawing Style...").trigger()
		qapp.processEvents()
		first = _element_by_id(session.backend_snapshot.cdml, "a1")
		second = _element_by_id(session.backend_snapshot.cdml, "a2")

		assert session.backend_snapshot.revision == before.revision + 1
		assert (
			first.getElementsByTagName("font")[0].getAttribute("size"),
			first.getElementsByTagName("font")[0].getAttribute("color"),
		) == ("18", "#445566")
		assert second.getElementsByTagName("font") == []
		assert session.document.selected_direct_root_molecule_ids == ("m1",)
		assert session.undo_backend().status == "accepted"
		assert session.backend_snapshot.cdml == before.cdml
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_all_values_scope_replaces_existing_object_overrides(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""All-values scope materializes every applicable value on every root."""
	session = _install_native_session(main_window, _MULTI_CDML)
	try:
		all_fields = (
			"line_width", "font_size", "font_family", "line_color", "area_color",
			"bond_width", "wedge_width", "double_ratio", "show_hydrogens",
		)
		_accept_changes(
			monkeypatch, (("font_family", "Courier"), ("font_size", 16)),
			application_scope="all", override_fields=all_fields,
		)
		_menu_action(main_window, "Document Drawing Style...").trigger()
		qapp.processEvents()
		atoms = tuple(
			_element_by_id(session.backend_snapshot.cdml, identifier)
			for identifier in ("a1", "a2")
		)

		assert all(
			atom.getElementsByTagName("font")[0].getAttribute("family") == "Courier"
			and atom.getElementsByTagName("font")[0].getAttribute("size") == "16"
			and atom.getAttribute("hydrogens") == "off"
			for atom in atoms
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_personal_default_save_without_document_change_stays_outside_cdml_history(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Preference-only intent saves complete values without dirtying the file."""
	session = _install_native_session(main_window)
	saved = []
	try:
		before = session.backend_snapshot
		monkeypatch.setattr(
			bkchem_qt.config.drawing_standard_preferences,
			"save_personal_drawing_standard",
			lambda _prefs, values: saved.append(values),
		)
		_accept_changes(monkeypatch, (), personal_action="save")
		_menu_action(main_window, "Document Drawing Style...").trigger()
		qapp.processEvents()

		assert session.backend_snapshot == before
		assert saved and dict(saved[0])["font_size"] == 12
		assert "personal default saved" in main_window.statusBar().currentMessage()
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_dialog_exposes_eligible_scope_all_values_and_reversible_personal_removal(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The real dialog makes consequential scope and preference intent explicit."""
	backend = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	dialog = bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog(
		backend.drawing_standard(oasa.cdml_standard.CDMLDrawingStandardQuery(0)),
		selected_root_count=2, personal_default_exists=True,
	)
	try:
		dialog._selected_scope.setChecked(True)
		dialog._all_values.setChecked(True)
		dialog._remove_personal_button.click()

		assert dialog.application_scope() == "selected"
		assert len(dialog.override_fields()) == 9
		assert "2 selected objects" in dialog._apply_button.text()
		assert dialog.personal_action() == "remove"
	finally:
		dialog.deleteLater()
		qapp.processEvents()
