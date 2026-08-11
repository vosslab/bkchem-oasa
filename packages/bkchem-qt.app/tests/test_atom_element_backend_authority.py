"""Focused authoritative-CDML behavior checks for AtomMode substitutions."""

# PIP3 modules
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.actions.context_menu
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.modes.atom_mode
import bkchem_qt.modes.draw_mode
import oasa.cdml_document
import oasa.safe_xml


#============================================
def _active_session(main_window: object) -> object:
	"""Return the session owning the current public main-window projection."""
	for session in main_window.sessions:
		if session.document is main_window.document and session.scene is main_window.scene:
			return session
	raise AssertionError("Main window has no active document session")


#============================================
def _direct_children(element: object, name: str) -> tuple[object, ...]:
	"""Return direct compatibility-DOM children with one local CDML name."""
	return tuple(
		child for child in element.childNodes
		if getattr(child, "localName", None) == name
	)


#============================================
def _atom_elements(complete_cdml: str) -> dict[str, str]:
	"""Return canonical direct core atom element names by their durable IDs."""
	accepted = oasa.cdml_document.CDMLDocumentSession.load(complete_cdml).snapshot().cdml
	document = oasa.safe_xml.parse_dom_from_string(accepted)
	return {
		atom.getAttribute("id"): atom.getAttribute("name")
		for molecule in _direct_children(document.documentElement, "molecule")
		for atom in _direct_children(molecule, "atom")
	}


#============================================
def _draw_mode(session: object) -> bkchem_qt.modes.draw_mode.DrawMode:
	"""Activate and return the session-owned Draw mode."""
	session.mode_manager.set_mode("draw")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.draw_mode.DrawMode):
		raise AssertionError("DrawMode did not activate")
	return mode


#============================================
def _atom_mode(session: object) -> bkchem_qt.modes.atom_mode.AtomMode:
	"""Activate and return the session-owned Atom mode."""
	session.mode_manager.set_mode("atom")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.atom_mode.AtomMode):
		raise AssertionError("AtomMode did not activate")
	return mode


#============================================
def _draw_root_pair(session: object, element: str) -> str:
	"""Create one synchronized root pair and return one of its durable atom IDs."""
	mode = _draw_mode(session)
	mode.current_element = element
	position = PySide6.QtCore.QPointF(120.0, 160.0)
	mode.mouse_press(position, None)
	mode.mouse_release(position, None)
	facts = _atom_elements(session.backend_snapshot.cdml)
	if not facts:
		raise AssertionError("Draw did not create a canonical atom")
	return next(iter(facts))


#============================================
def _atom_item(scene: object, atom_id: str) -> object:
	"""Return the live projected item for one durable atom ID."""
	for item in scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.atom_id == atom_id
		):
			return item
	raise AssertionError("Current projection has no requested durable atom")


#============================================
def _click_atom(mode: object, item: object) -> None:
	"""Send one direct AtomMode click at a currently live atom projection."""
	position = PySide6.QtCore.QPointF(item.atom_model.x, item.atom_model.y)
	mode.mouse_press(position, None)


#============================================
@pytest.mark.parametrize(("source", "replacement"), (("C", "O"), ("N", "O")))
def test_atom_mode_replaces_any_supported_core_atom_through_backend_cdml(
		main_window: object, source: str, replacement: str,
		) -> None:
	"""Atom clicks replace canonical element data and restore fresh durable selection."""
	session = _active_session(main_window)
	atom_id = _draw_root_pair(session, source)
	before_snapshot = session.backend_snapshot
	before_document = session.document
	mode = _atom_mode(session)
	mode.set_element(replacement)
	_click_atom(mode, _atom_item(session.scene, atom_id))

	selected_keys = {
		bkchem_qt.canvas.document_projection.persistent_selection_key(item)
		for item in session.scene.selectedItems()
	}
	assert (
		_atom_elements(session.backend_snapshot.cdml)[atom_id] == replacement
		and session.backend_snapshot.revision > before_snapshot.revision
		and session.document is not before_document
		and ("atom", atom_id) in selected_keys
	)


#============================================
def test_same_element_and_missing_durable_identity_leave_backend_unchanged(
		main_window: object,
		) -> None:
	"""No-op or unaddressable AtomMode clicks never create an accepted change."""
	session = _active_session(main_window)
	atom_id = _draw_root_pair(session, "C")
	mode = _atom_mode(session)
	before = session.backend_snapshot
	mode.set_element("C")
	_click_atom(mode, _atom_item(session.scene, atom_id))
	assert session.backend_snapshot == before

	item = _atom_item(session.scene, atom_id)
	item.atom_model.bind_backend_durable_id(None)
	mode.set_element("O")
	_click_atom(mode, item)
	assert session.backend_snapshot == before


#============================================
def test_context_element_edit_updates_backend_cdml_and_uses_backend_undo(
		main_window: object,
		) -> None:
	"""Context element edits use the canonical backend history and projection."""
	session = _active_session(main_window)
	atom_id = _draw_root_pair(session, "C")
	before = session.backend_snapshot
	before_document = session.document
	item = _atom_item(session.scene, atom_id)
	atom_model = item.atom_model
	del item
	bkchem_qt.actions.context_menu._set_atom_symbol(session.view, atom_model, "O")
	changed = session.backend_snapshot
	selected_keys = {
		bkchem_qt.canvas.document_projection.persistent_selection_key(item)
		for item in session.scene.selectedItems()
	}
	undo = session.undo_backend()

	assert (
		_atom_elements(changed.cdml)[atom_id] == "O"
		and changed.revision > before.revision
		and session.document is not before_document
		and ("atom", atom_id) in selected_keys
		and undo.status == "accepted"
		and _atom_elements(session.backend_snapshot.cdml)[atom_id] == "C"
	)


#============================================
def test_context_element_noop_or_inactive_view_leaves_backend_unchanged(
		main_window: object,
		) -> None:
	"""Same-element and unavailable context actions keep persistent state unchanged."""
	session = _active_session(main_window)
	atom_id = _draw_root_pair(session, "C")
	item = _atom_item(session.scene, atom_id)
	atom_model = item.atom_model
	del item
	before = session.backend_snapshot
	bkchem_qt.actions.context_menu._set_atom_symbol(session.view, atom_model, "C")
	inactive_session = main_window._create_session(activate=False)
	try:
		bkchem_qt.actions.context_menu._set_atom_symbol(
			inactive_session.view, atom_model, "O",
		)
	finally:
		main_window._remove_session(inactive_session)

	assert session.backend_snapshot == before


#============================================
def test_atom_projection_failure_recovers_only_the_accepted_snapshot(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Accepted element changes recover by public snapshot reprojection only."""
	session = _active_session(main_window)
	atom_id = _draw_root_pair(session, "N")
	install_projection = session._install_prepared_projection
	failure_pending = True
	failed_snapshot = None

	def fail_first_projection_install(
			prepared: object, selected_keys: object, file_path: object,
			projected_snapshot: object,
			) -> None:
		"""Fail only the first installation of this accepted atom snapshot."""
		nonlocal failure_pending, failed_snapshot
		if failure_pending:
			failure_pending = False
			failed_snapshot = projected_snapshot
			raise RuntimeError("one-time projection installation failure")
		install_projection(prepared, selected_keys, file_path, projected_snapshot)

	monkeypatch.setattr(session, "_install_prepared_projection", fail_first_projection_install)
	mode = _atom_mode(session)
	mode.set_element("O")
	_click_atom(mode, _atom_item(session.scene, atom_id))
	accepted_snapshot = session.backend_snapshot

	assert (
		failed_snapshot == accepted_snapshot
		and _atom_elements(accepted_snapshot.cdml)[atom_id] == "O"
		and not session.backend_projection_synchronized
	)
	retry = session.retry_current_backend_projection()
	assert (
		retry.status == "accepted"
		and session.backend_snapshot == accepted_snapshot
		and session.backend_projection_synchronized
		and _atom_elements(session.backend_snapshot.cdml)[atom_id] == "O"
	)
