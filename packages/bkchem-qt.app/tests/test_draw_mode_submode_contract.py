"""Focused behavior checks for DrawMode submode dispatch."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import oasa.cdml_document
import oasa.safe_xml


#============================================
def _draw_mode(main_window: object) -> object:
	"""Activate and return the real DrawMode for the active document."""
	main_window._mode_manager.set_mode("draw")
	mode = main_window._mode_manager.current_mode
	if mode is None:
		raise AssertionError("DrawMode did not activate")
	return mode


#============================================
def _direct_children(element: object, name: str) -> tuple[object, ...]:
	"""Return direct compatibility-DOM children with one local CDML name."""
	children = tuple(
		child for child in element.childNodes
		if getattr(child, "localName", None) == name
	)
	return children


#============================================
def _active_session(main_window: object) -> object:
	"""Return the live session that owns the current projection."""
	for session in main_window.sessions:
		if session.document is main_window.document and session.scene is main_window.scene:
			return session
	raise AssertionError("Main window has no active projected session")


#============================================
def _atom_item_by_durable_id(scene: object, atom_id: str) -> object:
	"""Return one atom from the current projection by its backend-issued ID."""
	for item in scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == atom_id
		):
			return item
	raise AssertionError("Current projection has no requested durable atom")


#============================================
def _bond_item_by_durable_id(scene: object, bond_id: str) -> object:
	"""Return one current bond projection using its backend-issued identity."""
	for item in scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
			and item.bond_model.backend_durable_id == bond_id
		):
			return item
	raise AssertionError("Current projection has no requested durable bond")


#============================================
def _new_bond_identity(
		before_cdml: str, accepted_cdml: str,
		) -> tuple[tuple[str, str], str, str, str]:
	"""Return backend-issued atom and bond IDs from one accepted Draw result."""
	# CDMLDocumentSession first applies the owning CDML validation boundary.
	before = oasa.cdml_document.CDMLDocumentSession.load(before_cdml).snapshot().cdml
	accepted = oasa.cdml_document.CDMLDocumentSession.load(accepted_cdml).snapshot().cdml
	before_document = oasa.safe_xml.parse_dom_from_string(before)
	accepted_document = oasa.safe_xml.parse_dom_from_string(accepted)
	before_ids = {
		bond.getAttribute("id")
		for molecule in _direct_children(before_document.documentElement, "molecule")
		for bond in _direct_children(molecule, "bond")
	}
	new_bonds = tuple(
		(molecule, bond)
		for molecule in _direct_children(accepted_document.documentElement, "molecule")
		for bond in _direct_children(molecule, "bond")
		if bond.getAttribute("id") not in before_ids
	)
	if len(new_bonds) != 1:
		raise AssertionError("Draw gesture did not create one canonical durable bond")
	molecule, bond = new_bonds[0]
	atom_ids = tuple(sorted((bond.getAttribute("start"), bond.getAttribute("end"))))
	if len(atom_ids) != 2 or not all(atom_ids):
		raise AssertionError("Canonical Draw bond did not name two durable atoms")
	if any(
		atom_id not in {atom.getAttribute("id") for atom in _direct_children(molecule, "atom")}
		for atom_id in atom_ids
	):
		raise AssertionError("Canonical Draw bond endpoints were not direct durable atoms")
	identity = (atom_ids, bond.getAttribute("id"), bond.getAttribute("type"),
			bond.getAttribute("simple_double"))
	return identity


#============================================
def _drag_new_bond(
		draw_mode: object,
		start: PySide6.QtCore.QPointF,
		end: PySide6.QtCore.QPointF,
		) -> None:
	"""Create one bond through the mode's public drag handlers."""
	draw_mode.mouse_press(start, None)
	draw_mode.mouse_move(end, None)
	draw_mode.mouse_release(end, None)


#============================================
def test_draw_bond_submodes_reach_the_oasa_cdml_writer(main_window: object) -> None:
	"""Selected wedge-double styling becomes canonical OASA CDML output."""
	draw_mode = _draw_mode(main_window)
	session = _active_session(main_window)
	before_cdml = session.backend_snapshot.cdml
	draw_mode.set_submode("double")
	draw_mode.set_submode("wedge")
	draw_mode.set_submode("simpledouble")
	_drag_new_bond(
		draw_mode,
		PySide6.QtCore.QPointF(180.0, 160.0),
		PySide6.QtCore.QPointF(180.0, 160.0),
	)
	atom_ids, bond_id, bond_type, simple_double = _new_bond_identity(
		before_cdml, session.backend_snapshot.cdml,
	)
	# Reacquire only backend-issued identities after acceptance replaced the projection.
	for atom_id in atom_ids:
		_atom_item_by_durable_id(session.scene, atom_id)
	_bond_item_by_durable_id(session.scene, bond_id)

	assert (bond_type, simple_double) == ("w2", "1")


#============================================
def test_fixed_submode_snaps_drag_to_the_selected_angle_and_length(
		main_window: object,
		) -> None:
	"""A fixed 6-degree drag uses both selected geometric constraints."""
	draw_mode = _draw_mode(main_window)
	main_window.scene.set_grid_snap_enabled(False)
	seed_position = PySide6.QtCore.QPointF(200.0, 200.0)
	# A blank public Draw gesture creates the seed through the backend and reprojects it.
	draw_mode.mouse_press(seed_position, None)
	draw_mode.mouse_release(seed_position, None)
	session = _active_session(main_window)
	seed_id = next(iter(session.document.molecules[0].atoms)).backend_durable_id
	if seed_id is None:
		raise AssertionError("Backend Draw result did not issue a durable seed ID")
	seed_item = _atom_item_by_durable_id(session.scene, seed_id)
	before_ids = {
		item.atom_model.backend_durable_id
		for item in session.scene.items()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
	}
	draw_mode.set_submode("6")
	draw_mode.set_submode("fixed")
	_drag_new_bond(
		draw_mode,
		PySide6.QtCore.QPointF(seed_item.atom_model.x, seed_item.atom_model.y),
		PySide6.QtCore.QPointF(300.0, 225.0),
	)
	after_ids = {
		item.atom_model.backend_durable_id
		for item in session.scene.items()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
	}
	new_ids = after_ids - before_ids
	if len(new_ids) != 1:
		raise AssertionError("Backend Draw drag did not reproject one new durable atom")
	seed_item = _atom_item_by_durable_id(session.scene, seed_id)
	atom = _atom_item_by_durable_id(session.scene, next(iter(new_ids)))
	length = math.hypot(
		atom.atom_model.x - seed_item.atom_model.x,
		atom.atom_model.y - seed_item.atom_model.y,
	)
	angle = math.degrees(math.atan2(
		atom.atom_model.y - seed_item.atom_model.y,
		atom.atom_model.x - seed_item.atom_model.x,
	))
	angle_is_selected = abs((angle / 6.0) - round(angle / 6.0)) < 0.01

	assert abs(length - draw_mode._get_bond_length()) < 0.01 and angle_is_selected
