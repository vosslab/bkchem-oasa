"""Focused backend-authoritative MarkMode behavior."""

# PIP3 modules
import pytest
import PySide6.QtCore
import yaml

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.mark_item
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.modes.edit_mode
import bkchem_qt.modes.mark_mode
import bkchem_qt.setup.mode_setup
import oasa.cdml_document
import oasa.safe_xml


_MARK_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'</molecule></cdml>'
)


#============================================
def _new_session(
		main_window: bkchem_qt.main_window.MainWindow, cdml_text: str = _MARK_CDML,
		) -> object:
	"""Create one synchronized private session with one durable atom."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		cdml_text,
	)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window, theme_manager=main_window._theme_manager,
		prefs=main_window._prefs, mode_host=main_window, prepared_native_cdml=prepared,
	)
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
		session, session.replace_projection_from_backend_snapshot,
	)
	session.install_projection_lifecycle_port(port)
	if session.retry_current_backend_projection().status != "accepted":
		raise RuntimeError("Mark test session did not project")
	return session


#============================================
def _dispose_session(session: object) -> None:
	"""Retire one test session through its window owner."""
	owner = session.parent()
	if not isinstance(owner, bkchem_qt.main_window.MainWindow):
		raise TypeError("Mark test session has no MainWindow owner")
	owner._dispose_session_later(session)


#============================================
def _mark_mode(session: object) -> bkchem_qt.modes.mark_mode.MarkMode:
	"""Activate and return this session's MarkMode."""
	session.mode_manager.set_mode("mark")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.mark_mode.MarkMode):
		raise AssertionError("MarkMode did not activate")
	return mode


#============================================
def _atom_item(session: object) -> object:
	"""Find the current durable atom projection."""
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return item
	raise AssertionError("Mark test projection omitted atom")


#============================================
def _mark_item(session: object, matching_mark_index: int) -> object:
	"""Find one current projected mark by its durable same-type ordinal."""
	for item in session.scene.items():
		model = getattr(item, "atom_mark_model", None)
		if (
			isinstance(item, bkchem_qt.canvas.items.mark_item.MarkItem)
			and model is not None and model.matching_mark_index == matching_mark_index
			):
			return item
	raise AssertionError("Mark test projection omitted requested ordinal")


#============================================
def _atom_fields(cdml_text: str) -> tuple[tuple[str, ...], str, str]:
	"""Read persisted mark types plus chemistry scalars from canonical CDML."""
	accepted_cdml = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	document = oasa.safe_xml.parse_dom_from_string(accepted_cdml.serialize())
	atom = document.getElementsByTagName("atom")[0]
	marks = tuple(mark.getAttribute("type") for mark in atom.getElementsByTagName("mark"))
	return marks, atom.getAttribute("charge"), atom.getAttribute("multiplicity")


#============================================
def _direct_mark_attribute(cdml_text: str, attribute: str) -> tuple[str, ...]:
	"""Read one preserved attribute from direct atom marks after strict CDML acceptance."""
	accepted_cdml = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	accepted = oasa.safe_xml.parse_dom_from_string(accepted_cdml.serialize())
	atom = accepted.getElementsByTagName("atom")[0]
	return tuple(
		child.getAttribute(attribute) for child in atom.childNodes
		if getattr(child, "tagName", None) == "mark"
	)


#============================================
def _mark_request(session: object, revision: int, action: str = "add") -> object:
	"""Build one exact plain mark request against a chosen revision."""
	return bkchem_qt.models.document_session.build_atom_mark_request(
		revision, "m1", "a1", action, "radical",
	)


#============================================
def test_mark_yaml_public_vocabulary_submits_immutable_backend_requests(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Every public Mark YAML choice produces its one documented request scalar."""
	expected_types = (
		("radical", "radical"), ("biradical", "biradical"),
		("electronpair", "electronpair"),
		("dottedelectronpair", "dotted_electronpair"),
		("plusincircle", "plus"), ("minusincircle", "minus"),
		("pzorbital", "pz_orbital"),
	)
	expected_actions = ("add", "remove")
	modes_config = yaml.safe_load(
		bkchem_qt.setup.mode_setup.get_modes_yaml_path().read_text(encoding="utf-8"),
	)
	submodes = modes_config["modes"]["mark"]["submodes"]
	assert (
		submodes[0]["group_label"],
		tuple(option["key"] for option in submodes[0]["options"]),
		submodes[0]["default"],
		submodes[1]["group_label"],
		tuple(option["key"] for option in submodes[1]["options"]),
		submodes[1]["default"],
	) == ("Mark Type", tuple(key for key, _value in expected_types), 0,
		"Action", expected_actions, 0)
	session = _new_session(main_window)
	try:
		mode = _mark_mode(session)
		submitted = []

		def record(request: object) -> object:
			"""Capture the exact immutable public request submitted by MarkMode."""
			submitted.append(request)
			return type("Outcome", (), {"message": "recorded"})()

		mode.set_persistent_operation(record)
		mode.set_atom_mark_revision(lambda: 17)
		item = _atom_item(session)
		position = PySide6.QtCore.QPointF(item.atom_model.x, item.atom_model.y)
		for action in expected_actions:
			mode.on_submode_switch(1, action)
			for yaml_key, backend_type in expected_types:
				mode.on_submode_switch(0, yaml_key)
				session.mode_manager.mouse_press(position, object())
				request = submitted.pop()
				assert (
					isinstance(
						request,
						bkchem_qt.models.document_session.PersistentOperationRequest,
					),
					request.operation_key,
					dict(request.payload),
				) == (
					True, "atom.mark.apply", {
						"expected_revision": 17, "molecule_id": "m1", "atom_id": "a1",
						"action": action, "mark_type": backend_type,
					},
				)
		assert not submitted
	finally:
		_dispose_session(session)


#============================================
def test_mark_mode_add_remove_uses_backend_history_and_chemistry_scalars(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A click uses OASA history, canonical marks, and durable atom selection."""
	session = _new_session(main_window)
	try:
		mode = _mark_mode(session)
		mode.on_submode_switch(0, "plusincircle")
		item = _atom_item(session)
		position = PySide6.QtCore.QPointF(item.atom_model.x, item.atom_model.y)
		del item
		session.mode_manager.mouse_press(position, object())
		added = session.backend_snapshot
		undone = session.undo_backend()
		redone = session.redo_backend()

		assert _atom_fields(added.cdml) == (("plus",), "1", "")
		assert (
			undone.status == "accepted" and redone.status == "accepted"
			and _atom_fields(session.backend_snapshot.cdml) == (("plus",), "1", "")
			and all(
				not isinstance(item, bkchem_qt.canvas.items.mark_item.MarkItem)
				for item in session.scene.selectedItems()
			)
			and any(
				isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
				for item in session.scene.selectedItems()
			)
		)
	finally:
		_dispose_session(session)


#============================================
def test_mark_remove_no_match_preserves_exact_snapshot_and_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""No-match removal is a backend-accepted no-op with no reprojection history."""
	session = _new_session(main_window)
	try:
		mode = _mark_mode(session)
		mode.on_submode_switch(1, "remove")
		item = _atom_item(session)
		position = PySide6.QtCore.QPointF(item.atom_model.x, item.atom_model.y)
		del item
		before_snapshot = session.backend_snapshot
		before_document = session.document
		session.mode_manager.mouse_press(position, object())

		assert session.backend_snapshot == before_snapshot and session.document is before_document
	finally:
		_dispose_session(session)


#============================================
def test_edit_delete_selected_mark_uses_its_ordinal_and_backend_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Delete removes only the selected duplicate and restores parent-atom selection."""
	cdml = _MARK_CDML.replace(
		'<cdml version="26.07">', '<cdml version="26.07" xmlns:v="urn:vendor">',
	).replace(
		'<point x="1cm" y="1cm"/>',
		'<point x="1cm" y="1cm"/><mark type="plus" data-origin="first" '
		'x="1.2cm" y="1.2cm" auto="0" size="10"/><v:mark type="plus" '
		'data-origin="foreign"/><mark type="plus" '
		'data-origin="second" x="1.3cm" y="1.3cm" auto="0" size="10"/>',
	).replace('name="C"', 'name="C" charge="2"')
	session = _new_session(main_window, cdml)
	try:
		session.mode_manager.set_mode("edit")
		mode = session.mode_manager.current_mode
		if not isinstance(mode, bkchem_qt.modes.edit_mode.EditMode):
			raise AssertionError("EditMode did not activate")
		item = _mark_item(session, 1)
		session.scene.clearSelection()
		item.setSelected(True)
		del item
		mode._delete_selected()
		atom_selected = any(
			isinstance(selected, bkchem_qt.canvas.items.atom_item.AtomItem)
			for selected in session.scene.selectedItems()
		)
		accepted_cdml = session.backend_snapshot.cdml
		charge = _atom_fields(accepted_cdml)[1]
		undo_status = session.undo_backend().status

		assert _direct_mark_attribute(accepted_cdml, "data-origin") == ("first",)
		assert atom_selected and charge == "1" and undo_status == "accepted"
	finally:
		_dispose_session(session)


#============================================
def test_selected_mark_delete_recovers_only_its_accepted_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed selected-mark replacement recovers through exact snapshot retry."""
	cdml = _MARK_CDML.replace(
		'<point x="1cm" y="1cm"/>',
		'<point x="1cm" y="1cm"/><mark type="plus" x="1.2cm" y="1.2cm" '
		'auto="0" size="10"/>',
	)
	session = _new_session(main_window, cdml)
	try:
		def unavailable(_snapshot: object) -> object:
			"""Report one typed post-acceptance projection installation failure."""
			return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
			)

		port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
			session, unavailable,
		)
		session.install_projection_lifecycle_port(port)
		session.mode_manager.set_mode("edit")
		mode = session.mode_manager.current_mode
		if not isinstance(mode, bkchem_qt.modes.edit_mode.EditMode):
			raise AssertionError("EditMode did not activate")
		item = _mark_item(session, 0)
		session.scene.clearSelection()
		item.setSelected(True)
		del item
		mode._delete_selected()
		accepted = session.backend_snapshot
		unsynchronized_before_retry = not session.backend_projection_synchronized
		def resubmission_must_not_run(_request: object) -> object:
			"""Prove recovery uses the accepted snapshot rather than Delete intent."""
			raise AssertionError("Selected-mark Delete was resubmitted during recovery")

		monkeypatch.setattr(session, "submit_persistent_operation", resubmission_must_not_run)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		recovered = session.retry_current_backend_projection()

		assert _direct_mark_attribute(accepted.cdml, "type") == () and unsynchronized_before_retry
		assert recovered.status == "accepted" and session.backend_snapshot == accepted
	finally:
		_dispose_session(session)


#============================================
@pytest.mark.parametrize("case", ("mixed", "foreign", "id-less"))
def test_selected_mark_delete_ineligible_selection_is_inert(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch, case: str,
		) -> None:
	"""Invalid selected-mark evidence never creates a backend or Qt mutation."""
	cdml = _MARK_CDML.replace(
		'<point x="1cm" y="1cm"/>',
		'<point x="1cm" y="1cm"/><mark type="plus" x="1.2cm" y="1.2cm" '
		'auto="0" size="10"/>',
	)
	session = _new_session(main_window, cdml)
	try:
		session.mode_manager.set_mode("edit")
		mode = session.mode_manager.current_mode
		if not isinstance(mode, bkchem_qt.modes.edit_mode.EditMode):
			raise AssertionError("EditMode did not activate")
		mark = _mark_item(session, 0)
		if case == "mixed":
			_atom_item(session).setSelected(True)
		elif case == "foreign":
			monkeypatch.setattr(session.document, "is_current_projection_item", lambda _item: False)
		else:
			mark.atom_mark_model.atom_model.bind_backend_durable_id(None)
		mark.setSelected(True)
		before = session.backend_snapshot
		mode._delete_selected()

		assert session.backend_snapshot == before and not session.document.undo_stack.canUndo()
		assert not session.legacy_isolated
	finally:
		_dispose_session(session)


#============================================
def test_mark_mode_without_a_durable_atom_is_inert(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An ID-less local atom cannot become a hidden persistent mutation route."""
	session = _new_session(main_window)
	try:
		_mark_mode(session)
		item = _atom_item(session)
		item.atom_model.bind_backend_durable_id(None)
		position = PySide6.QtCore.QPointF(item.atom_model.x, item.atom_model.y)
		before = session.backend_snapshot
		session.mode_manager.mouse_press(position, object())

		assert session.backend_snapshot == before and not session.legacy_isolated
	finally:
		_dispose_session(session)


#============================================
def test_stale_mark_request_is_atomic_and_keeps_backend_navigation_unchanged(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A stale immutable mark intent cannot mutate or create local history."""
	session = _new_session(main_window)
	try:
		before = session.backend_snapshot
		outcome = session.submit_persistent_operation(
			_mark_request(session, before.revision - 1),
		)

		assert outcome.status == "rejected" and outcome.failure_kind == "revision-conflict"
		assert session.backend_snapshot == before and not session.can_undo_backend
	finally:
		_dispose_session(session)


#============================================
def test_accepted_mark_projection_failure_retries_only_current_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A final accepted mark is recovered by projection, never intent resubmission."""
	session = _new_session(main_window)
	original_install = session._install_prepared_projection
	initial_install = True

	def fail_initial_install(*args: object, **kwargs: object) -> None:
		"""Fail one replacement installation and allow the explicit retry."""
		nonlocal initial_install
		if initial_install:
			initial_install = False
			raise RuntimeError("intentional mark projection failure")
		original_install(*args, **kwargs)

	monkeypatch.setattr(session, "_install_prepared_projection", fail_initial_install)
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
		session, session.replace_projection_from_backend_snapshot,
	)
	session.install_projection_lifecycle_port(port)
	try:
		outcome = session.submit_persistent_operation(
			_mark_request(session, session.backend_snapshot.revision),
		)
		accepted = session.backend_snapshot
		recovered = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and outcome.submitted
		assert recovered.status == "accepted" and session.backend_snapshot == accepted
	finally:
		_dispose_session(session)
