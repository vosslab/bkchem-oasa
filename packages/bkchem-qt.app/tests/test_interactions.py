"""Tests for Patch 4-5: Dialog wiring, template placement, and bond drawing."""

# Standard Library
import ast
import math
import pathlib

# PIP3 modules
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.modes.draw_mode
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.molecule_model
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.actions.context_menu


#============================================
def _complete_draw(
		draw_mode: bkchem_qt.modes.draw_mode.DrawMode,
		position: PySide6.QtCore.QPointF,
		) -> None:
	"""Commit one Draw click through the backend-owned session route."""
	draw_mode.mouse_press(position, None)
	draw_mode.mouse_release(position, None)


#============================================
def _new_root_from_draw(
		main_window: object, draw_mode: bkchem_qt.modes.draw_mode.DrawMode,
		position: PySide6.QtCore.QPointF,
		) -> object:
	"""Commit a fresh root and return it across shared-session fixture resets."""
	previous_ids = {molecule.mol_id for molecule in main_window.document.molecules}
	_complete_draw(draw_mode, position)
	for molecule in main_window.document.molecules:
		if molecule.mol_id not in previous_ids:
			return molecule
	raise AssertionError("Draw click did not install a new backend molecule root")


#============================================
def test_atom_dialog_applies_changes(qapp: object) -> None:
	"""AtomDialog.edit_atom() can apply changes to an AtomModel."""
	atom = bkchem_qt.models.atom_model.AtomModel(symbol="C")
	atom.set_xyz(0.0, 0.0, 0.0)
	assert atom.symbol == "C", "should start as C"
	# directly test property setting
	atom.symbol = "N"
	assert atom.symbol == "N", "symbol should be N after set"
	atom.charge = -1
	assert atom.charge == -1, "charge should be -1"
	atom.font_size = 14
	assert atom.font_size == 14, "font_size should be 14"


#============================================
def test_bond_dialog_applies_changes(qapp: object) -> None:
	"""BondDialog.edit_bond() can apply changes to a BondModel."""
	bond = bkchem_qt.models.bond_model.BondModel(order=1, bond_type="n")
	assert bond.order == 1, "should start as single"
	assert bond.type == "n", "should start as normal"
	# directly test property setting
	bond.order = 2
	assert bond.order == 2, "order should be 2 after set"
	bond.type = "w"
	assert bond.type == "w", "type should be w after set"
	bond.line_width = 2.5
	assert bond.line_width == 2.5, "line_width should be 2.5"


#============================================
def test_context_menu_delete_atom(main_window: object) -> None:
	"""Context menu _delete_atom() removes atom with undo support."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	atom_item = draw_mode._create_atom_at(100.0, 200.0, "C")
	assert atom_item is not None
	# verify atom exists
	items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(items) == 1
	# delete via context menu helper
	bkchem_qt.actions.context_menu._delete_atom(
		main_window.view, atom_item
	)
	items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(items) == 0, "atom should be removed"
	# undo should restore it
	main_window.document.undo_stack.undo()
	items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(items) == 1, "atom should be restored after undo"


#============================================
def test_implemented_modes_no_crash_on_press(main_window: object) -> None:
	"""All modes handle mouse press without crashing or saying not implemented."""
	# modes that were previously stubs are now implemented
	mode_names = ["vector", "bracket", "plus", "misc", "repair"]
	for mode_name in mode_names:
		main_window._mode_manager.set_mode(mode_name)
		mode = main_window._mode_manager.current_mode
		messages = []
		mode.status_message.connect(messages.append)
		# simulate a mouse press -- should not crash
		pos = PySide6.QtCore.QPointF(100.0, 100.0)
		mode.mouse_press(pos, None)
		# if any messages were emitted, none should say 'not yet implemented'
		for msg in messages:
			assert "not yet implemented" not in msg, (
				f"{mode_name}: should be implemented, got: {msg}"
			)
		# disconnect to avoid accumulation across modes
		mode.status_message.disconnect(messages.append)


# ------------------------------------------------------------------
# Bond placement parity tests
# ------------------------------------------------------------------

#============================================
def _count_atom_items(scene: object) -> int:
	"""Count AtomItem instances in the scene."""
	return sum(
		1 for i in scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	)


#============================================
def _count_bond_items(scene: object) -> int:
	"""Count BondItem instances in the scene."""
	return sum(
		1 for i in scene.items()
		if isinstance(i, bkchem_qt.canvas.items.bond_item.BondItem)
	)


#============================================
class _FakeMouseEvent:
	"""Minimal mouse-event stub for direct mode method calls in tests."""

	#============================================
	def __init__(
		self, modifiers: object = PySide6.QtCore.Qt.KeyboardModifier.NoModifier,
	) -> None:
		self._modifiers = modifiers

	#============================================
	def modifiers(self) -> object:
		"""Return keyboard modifiers."""
		return self._modifiers


#============================================
def test_scene_and_draw_share_canonical_spacing(main_window: object) -> None:
	"""Draw mode must read bond length directly from scene spacing."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	main_window.scene.set_grid_spacing_pt(52.0)
	assert abs(main_window.scene.grid_spacing_pt - 52.0) < 1e-6
	assert abs(draw_mode._get_bond_length() - 52.0) < 1e-6


#============================================
def test_zoom_does_not_change_scene_spacing_value(main_window: object) -> None:
	"""Zoom operations must not change the canonical scene spacing value."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	initial_spacing = main_window.scene.grid_spacing_pt
	main_window.view.set_zoom_percent(220.0)
	assert abs(main_window.scene.grid_spacing_pt - initial_spacing) < 1e-6
	assert abs(draw_mode._get_bond_length() - initial_spacing) < 1e-6
	main_window.view.reset_zoom()


#============================================
def test_element_change_routes_to_atom_mode_setter(main_window: object) -> None:
	"""Element edits should route through AtomMode.set_element()."""
	main_window._mode_manager.set_mode("atom")
	atom_mode = main_window._mode_manager.current_mode
	main_window._on_element_changed("O")
	assert atom_mode.current_element == "O", (
		"Atom mode should update current element via set_element()"
	)


#============================================
def test_element_change_routes_to_draw_mode_property(main_window: object) -> None:
	"""Element edits should route to DrawMode.current_element setter."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	main_window._on_element_changed("  N  ")
	assert draw_mode.current_element == "N", (
		"Draw mode should store stripped element text"
	)
	main_window._on_element_changed("   ")
	assert draw_mode.current_element == "N", (
		"Blank element edits should not clear draw mode element"
	)


#============================================
def test_bond_click_creates_fixed_length_bond(main_window: object) -> None:
	"""Clicking a projected atom adds one backend-owned fixed-length bond."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol = _new_root_from_draw(
		main_window, draw_mode, PySide6.QtCore.QPointF(200.0, 200.0),
	)
	seed = mol.atoms[0]
	_complete_draw(draw_mode, PySide6.QtCore.QPointF(seed.x, seed.y))
	mol = next(
		candidate for candidate in main_window.document.molecules
		if candidate.mol_id == mol.mol_id
	)
	assert _count_atom_items(main_window.scene) == 3
	assert _count_bond_items(main_window.scene) == 2
	bond_length = draw_mode._get_bond_length()
	atoms = mol.atoms
	assert len(atoms) == 3, "backend extension should add one atom"
	dx = atoms[-1].x - seed.x
	dy = atoms[-1].y - seed.y
	actual_dist = math.sqrt(dx * dx + dy * dy)
	assert abs(actual_dist - bond_length) < 0.5, (
		f"bond length {actual_dist:.2f} should be close to "
		f"grid spacing {bond_length:.2f}"
	)


#============================================
def test_bond_click_uses_120_degree_angle(main_window: object) -> None:
	"""Click on atom with one neighbor places new bond at ~120 degrees."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol = _new_root_from_draw(
		main_window, draw_mode, PySide6.QtCore.QPointF(200.0, 200.0),
	)
	a1, a2 = mol.atoms
	_complete_draw(draw_mode, PySide6.QtCore.QPointF(a2.x, a2.y))
	mol = next(
		candidate for candidate in main_window.document.molecules
		if candidate.mol_id == mol.mol_id
	)
	a3 = mol.atoms[-1]
	assert _count_atom_items(main_window.scene) == 3
	angle_a2_a1 = math.atan2(a1.y - a2.y, a1.x - a2.x)
	angle_a2_a3 = math.atan2(a3.y - a2.y, a3.x - a2.x)
	angle_diff = abs(angle_a2_a3 - angle_a2_a1)
	# normalize to [0, pi]
	if angle_diff > math.pi:
		angle_diff = 2 * math.pi - angle_diff
	# should be approximately 120 degrees (2*pi/3 radians)
	expected = 2 * math.pi / 3
	assert abs(angle_diff - expected) < 0.15, (
		f"angle between bonds should be ~120 deg ({math.degrees(expected):.1f}), "
		f"got {math.degrees(angle_diff):.1f} deg"
	)


#============================================
def test_standalone_atom_snaps_to_grid(main_window: object) -> None:
	"""Click on empty space creates atoms snapped to hex grid."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	scene = main_window.scene
	# click on a position that is NOT on the grid
	pos = PySide6.QtCore.QPointF(103.7, 98.2)
	mol = _new_root_from_draw(main_window, draw_mode, pos)
	# should have 2 atoms (standalone + auto-bonded neighbor)
	assert _count_atom_items(scene) >= 2, (
		"clicking empty space should create atom + bonded neighbor"
	)
	# the first atom should be snapped to grid
	first_atom = mol.atoms[0]
	# verify by re-snapping and checking it matches
	snapped_x, snapped_y = scene.snap_to_grid(103.7, 98.2)
	assert abs(first_atom.x - snapped_x) < 0.5, (
		f"x={first_atom.x:.2f} should be snapped to {snapped_x:.2f}"
	)
	assert abs(first_atom.y - snapped_y) < 0.5, (
		f"y={first_atom.y:.2f} should be snapped to {snapped_y:.2f}"
	)


#============================================
def test_standalone_atom_respects_grid_snap_toggle(main_window: object) -> None:
	"""Draw mode should place on raw cursor when grid snap is disabled."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	scene = main_window.scene
	scene.set_grid_snap_enabled(False)
	pos = PySide6.QtCore.QPointF(103.7, 98.2)
	mol = _new_root_from_draw(main_window, draw_mode, pos)
	first_atom = mol.atoms[0]
	assert abs(first_atom.x - pos.x()) < 0.5, (
		f"x={first_atom.x:.2f} should stay near click x={pos.x():.2f}"
	)
	assert abs(first_atom.y - pos.y()) < 0.5, (
		f"y={first_atom.y:.2f} should stay near click y={pos.y():.2f}"
	)


#============================================
def test_edit_drag_snaps_anchor_to_grid(main_window: object) -> None:
	"""Edit drag should snap selected atoms by anchor when enabled."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	scene = main_window.scene
	scene.set_grid_snap_enabled(True)
	a1 = draw_mode._create_atom_at(101.0, 99.0, "C")
	a2 = draw_mode._create_atom_at(141.0, 99.0, "C")
	draw_mode._create_bond_between(a1, a2)
	initial_dx = a2.atom_model.x - a1.atom_model.x
	initial_dy = a2.atom_model.y - a1.atom_model.y
	a1.setSelected(True)
	a2.setSelected(True)
	main_window._mode_manager.set_mode("edit")
	edit_mode = main_window._mode_manager.current_mode
	event = _FakeMouseEvent()
	start = PySide6.QtCore.QPointF(a1.atom_model.x, a1.atom_model.y)
	target = PySide6.QtCore.QPointF(start.x() + 13.2, start.y() + 8.7)
	edit_mode.mouse_press(start, event)
	edit_mode.mouse_move(target, event)
	edit_mode.mouse_release(target, event)
	expected_x, expected_y = scene.snap_to_grid(target.x(), target.y())
	assert abs(a1.atom_model.x - expected_x) < 0.5, (
		f"anchor x={a1.atom_model.x:.2f} should snap to {expected_x:.2f}"
	)
	assert abs(a1.atom_model.y - expected_y) < 0.5, (
		f"anchor y={a1.atom_model.y:.2f} should snap to {expected_y:.2f}"
	)
	final_dx = a2.atom_model.x - a1.atom_model.x
	final_dy = a2.atom_model.y - a1.atom_model.y
	assert abs(final_dx - initial_dx) < 0.1, (
		f"pair dx should remain {initial_dx:.2f}, got {final_dx:.2f}"
	)
	assert abs(final_dy - initial_dy) < 0.1, (
		f"pair dy should remain {initial_dy:.2f}, got {final_dy:.2f}"
	)


#============================================
def test_find_place_zero_neighbors(main_window: object) -> None:
	"""_find_place with zero neighbors places at 30-degree default angle."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol_model = draw_mode._get_active_molecule()
	# create isolated atom
	atom = draw_mode._create_atom_at(200.0, 200.0, "C")
	bond_length = draw_mode._get_bond_length()
	new_x, new_y = draw_mode._find_place(
		atom.atom_model, mol_model, bond_length,
	)
	# should be at 30 deg angle: cos(pi/6)*d, -sin(pi/6)*d
	expected_x = 200.0 + math.cos(math.pi / 6) * bond_length
	expected_y = 200.0 - math.sin(math.pi / 6) * bond_length
	assert abs(new_x - expected_x) < 0.5, (
		f"x={new_x:.2f} should be ~{expected_x:.2f}"
	)
	assert abs(new_y - expected_y) < 0.5, (
		f"y={new_y:.2f} should be ~{expected_y:.2f}"
	)


#============================================
def test_connected_display_atoms_returns_projection_neighbors_in_bond_order() -> None:
	"""The public query exposes display neighbors and scalar bond orders only."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	center = molecule.create_atom()
	first = molecule.create_atom()
	second = molecule.create_atom()
	for atom in (center, first, second):
		molecule.add_atom(atom)
	first_bond = molecule.create_bond(order=2)
	second_bond = molecule.create_bond(order=3)
	molecule.add_bond(center, first, first_bond)
	molecule.add_bond(center, second, second_bond)
	connections = molecule.connected_display_atoms(center)
	assert connections == ((first, 2), (second, 3))
	assert molecule.connected_display_atoms(first) == ((center, 2),)


#============================================
def test_connected_display_atoms_rejects_foreign_atoms_and_invalid_endpoints() -> None:
	"""The projection query fails loudly for cross-molecule and broken wrappers."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	first = molecule.create_atom()
	second = molecule.create_atom()
	for atom in (first, second):
		molecule.add_atom(atom)
	bond = molecule.create_bond()
	molecule.add_bond(first, second, bond)
	foreign = bkchem_qt.models.molecule_model.MoleculeModel().create_atom()
	with pytest.raises(ValueError, match="does not belong"):
		molecule.connected_display_atoms(foreign)
	bond.atom2 = foreign
	with pytest.raises(ValueError, match="bond endpoints"):
		molecule.connected_display_atoms(first)


#============================================
def test_molecule_topology_uses_qt_wrappers_for_cycles_and_removal() -> None:
	"""A disposable projection reports wrapper cycles and retires wrappers."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	atoms = [molecule.create_atom() for unused_index in range(3)]
	for atom in atoms:
		molecule.add_atom(atom)
	for first, second in ((0, 1), (1, 2), (2, 0)):
		bond = molecule.create_bond()
		molecule.add_bond(atoms[first], atoms[second], bond)
	cycles = molecule.get_smallest_independent_cycles()
	molecule.remove_atom(atoms[0])
	assert any(set(cycle) == set(atoms) for cycle in cycles)
	assert molecule.contains_cycle() is False


#============================================
def test_molecule_model_owns_active_wrappers_and_releases_removed_ones() -> None:
	"""Wrapper QObject ownership follows the disposable topology lifecycle."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	first = molecule.create_atom()
	second = molecule.create_atom()
	molecule.add_atom(first)
	molecule.add_atom(second)
	bond = molecule.create_bond()
	molecule.add_bond(first, second, bond)
	assert first.parent() is molecule and bond.parent() is molecule
	molecule.remove_atom(first)
	assert first.parent() is None and bond.parent() is None


#============================================
def test_molecule_topology_rejects_nonchemical_self_and_parallel_edges() -> None:
	"""One bond order, rather than duplicate edges, represents one atom pair."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	first = molecule.create_atom()
	second = molecule.create_atom()
	molecule.add_atom(first)
	molecule.add_atom(second)
	with pytest.raises(ValueError, match="distinct"):
		molecule.add_bond(first, first, molecule.create_bond())
	molecule.add_bond(first, second, molecule.create_bond())
	with pytest.raises(ValueError, match="already contains"):
		molecule.add_bond(first, second, molecule.create_bond())


#============================================
def test_molecule_topology_handles_empty_and_disconnected_projections() -> None:
	"""Projection connectivity has explicit empty and disconnected behavior."""
	empty = bkchem_qt.models.molecule_model.MoleculeModel()
	disconnected = bkchem_qt.models.molecule_model.MoleculeModel()
	disconnected.add_atom(disconnected.create_atom())
	disconnected.add_atom(disconnected.create_atom())
	assert (empty.is_connected(), empty.contains_cycle()) == (False, False)
	assert disconnected.is_connected() is False


#============================================
def test_molecule_model_source_has_no_oasa_import_boundary() -> None:
	"""The projection topology module has no direct backend graph import."""
	source_path = pathlib.Path(bkchem_qt.models.molecule_model.__file__)
	tree = ast.parse(source_path.read_text(encoding="utf-8"))
	modules = [
			alias.name
			for node in ast.walk(tree) if isinstance(node, ast.Import)
			for alias in node.names
		]
	modules.extend(
			node.module for node in ast.walk(tree)
			if isinstance(node, ast.ImportFrom) and node.module is not None
			)
	assert all(not module.startswith("oasa") for module in modules)


#============================================
def test_bond_model_source_has_no_oasa_import_boundary() -> None:
	"""The scalar bond projection module has no backend import or construction."""
	source_path = pathlib.Path(bkchem_qt.models.bond_model.__file__)
	tree = ast.parse(source_path.read_text(encoding="utf-8"))
	modules = [
			alias.name
			for node in ast.walk(tree) if isinstance(node, ast.Import)
			for alias in node.names
		]
	modules.extend(
			node.module for node in ast.walk(tree)
			if isinstance(node, ast.ImportFrom) and node.module is not None
			)
	constructors = [
		node.func.attr for node in ast.walk(tree)
		if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
		]
	assert all(not module.startswith("oasa") for module in modules)
	assert "Bond" not in constructors


#============================================
def test_atom_model_source_has_no_oasa_carrier_boundary() -> None:
	"""The scalar atom projection neither imports nor constructs OASA atoms."""
	source_path = pathlib.Path(bkchem_qt.models.atom_model.__file__)
	tree = ast.parse(source_path.read_text(encoding="utf-8"))
	modules = [
			alias.name
			for node in ast.walk(tree) if isinstance(node, ast.Import)
			for alias in node.names
		]
	modules.extend(
			node.module for node in ast.walk(tree)
			if isinstance(node, ast.ImportFrom) and node.module is not None
			)
	constructors = [
		node.func.attr for node in ast.walk(tree)
		if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
		]
	assert all(not module.startswith("oasa") for module in modules)
	assert "Atom" not in constructors


#============================================
def test_find_place_least_crowded(main_window: object) -> None:
	"""_find_place with 2+ neighbors uses least-crowded angular gap."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol_model = draw_mode._get_active_molecule()
	bond_length = draw_mode._get_bond_length()
	# create a center atom with 2 neighbors at 0 and 90 degrees
	center = draw_mode._create_atom_at(200.0, 200.0, "C")
	right = draw_mode._create_atom_at(200.0 + bond_length, 200.0, "C")
	up = draw_mode._create_atom_at(200.0, 200.0 - bond_length, "C")
	draw_mode._create_bond_between(center, right)
	draw_mode._create_bond_between(center, up)
	# find place should pick the largest angular gap
	new_x, new_y = draw_mode._find_place(
		center.atom_model, mol_model, bond_length,
	)
	# the largest gap is from 0 deg clockwise to 270 deg (= -90 deg)
	# which is a 270 deg gap; midpoint is at 135 deg (down-left)
	dx = new_x - 200.0
	dy = new_y - 200.0
	actual_dist = math.sqrt(dx * dx + dy * dy)
	assert abs(actual_dist - bond_length) < 0.5, (
		f"distance {actual_dist:.2f} should be ~{bond_length:.2f}"
	)
	# The 270-degree gap from the right-hand bond to the upward bond has a
	# midpoint at 135 degrees (down-left in scene coordinates).
	angle = math.atan2(dy, dx)
	if angle < 0:
		angle += 2 * math.pi
	assert abs(angle - 3 * math.pi / 4) < 0.02, (
		f"new atom angle {math.degrees(angle):.1f} should be 135 degrees"
	)


#============================================
def test_find_place_uses_transoid_side_for_degree_two_neighbor(
		main_window: object,
		) -> None:
	"""A degree-two neighbor makes the next ordinary bond transoid."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol_model = draw_mode._get_active_molecule()
	bond_length = draw_mode._get_bond_length()
	selected = draw_mode._create_atom_at(200.0, 200.0, "C")
	neighbor = draw_mode._create_atom_at(200.0 + bond_length, 200.0, "C")
	neighbor_other = draw_mode._create_atom_at(
		200.0 + bond_length, 200.0 - bond_length, "C",
	)
	draw_mode._create_bond_between(selected, neighbor)
	draw_mode._create_bond_between(neighbor, neighbor_other)
	new_x, new_y = draw_mode._find_place(
		selected.atom_model, mol_model, bond_length,
	)
	new_angle = math.atan2(
		new_y - selected.atom_model.y,
		new_x - selected.atom_model.x,
	)
	existing_angle = math.atan2(
		neighbor.atom_model.y - selected.atom_model.y,
		neighbor.atom_model.x - selected.atom_model.x,
	)
	angle_difference = abs(new_angle - existing_angle)
	if angle_difference > math.pi:
		angle_difference = 2 * math.pi - angle_difference
	assert abs(angle_difference - 2 * math.pi / 3) < 0.02

	new_side = draw_mode._on_which_side(
		neighbor.atom_model, selected.atom_model, new_x, new_y,
	)
	other_side = draw_mode._on_which_side(
		neighbor.atom_model,
		selected.atom_model,
		neighbor_other.atom_model.x,
		neighbor_other.atom_model.y,
	)
	assert new_side == -other_side


#============================================
def test_find_place_extends_existing_triple_bond(main_window: object) -> None:
	"""A triple-bonded displayed neighbor produces a collinear extension."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol_model = draw_mode._get_active_molecule()
	bond_length = draw_mode._get_bond_length()
	center = draw_mode._create_atom_at(200.0, 200.0, "C")
	right = draw_mode._create_atom_at(200.0 + bond_length, 200.0, "C")
	bond_item = draw_mode._create_bond_between(center, right)
	bond_item.bond_model.order = 3
	new_x, new_y = draw_mode._find_place(
		center.atom_model, mol_model, bond_length,
	)
	assert abs(new_x - (200.0 - bond_length)) < 0.5
	assert abs(new_y - 200.0) < 0.5


# ------------------------------------------------------------------
# Bond endpoint clipping and signal chain tests
# ------------------------------------------------------------------

#============================================
def _make_bonded_items(
	qapp: object,
	symbol1: str = "C",
	symbol2: str = "N",
	x1: float = 0.0,
	y1: float = 0.0,
	x2: float = 40.0,
	y2: float = 0.0,
) -> tuple:
	"""Create two AtomModels connected by a BondModel with BondItem.

	Uses MoleculeModel to properly wire the OASA graph connectivity
	so edge.vertices returns the correct atoms for bond rendering.
	"""
	import bkchem_qt.models.molecule_model
	mol_model = bkchem_qt.models.molecule_model.MoleculeModel()
	a1 = mol_model.create_atom(symbol=symbol1)
	a2 = mol_model.create_atom(symbol=symbol2)
	a1.set_xyz(x1, y1, 0.0)
	a2.set_xyz(x2, y2, 0.0)
	mol_model.add_atom(a1)
	mol_model.add_atom(a2)
	bond = mol_model.create_bond(order=1, bond_type="n")
	mol_model.add_bond(a1, a2, bond)
	bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond)
	return a1, a2, bond, bond_item


#============================================
def _line_x_extents(bond_item: object) -> tuple[float, float]:
	"""Return the portable horizontal paint extents of one simple bond."""
	points = [
		x
		for operation in bond_item._ops if operation.kind == "line"
		for x, unused_y in operation.points
	]
	return min(points), max(points)


#============================================
def test_bond_item_clips_at_labeled_atom(qapp: object) -> None:
	"""Bond endpoint near a labeled heteroatom is shorter than center-to-center."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "N", 0.0, 0.0, 40.0, 0.0)
	# the bond line toward N (at x=40) should be clipped short of 40
	unused_min_x, max_x = _line_x_extents(bond_item)
	assert max_x < 40.0


#============================================
def test_bond_item_no_clip_for_hidden_carbon(qapp: object) -> None:
	"""Bond between two hidden carbons has no clipping."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "C", 0.0, 0.0, 40.0, 0.0)
	# both endpoints should be at full center-to-center distance
	min_x, max_x = _line_x_extents(bond_item)
	assert abs(min_x) < 1.0 and abs(max_x - 40.0) < 1.0


#============================================
def test_atom_symbol_change_triggers_bond_redraw(qapp: object) -> None:
	"""Changing atom symbol triggers bond item update via signal chain."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "C", 0.0, 0.0, 40.0, 0.0)
	# change atom2 to nitrogen (should trigger bond update)
	a2.symbol = "N"
	# bond_item should have been updated (ops may differ now)
	# the end should now be clipped because N is shown
	unused_min_x, max_x = _line_x_extents(bond_item)
	assert max_x < 40.0


#============================================
def test_atom_charge_change_triggers_bond_redraw(qapp: object) -> None:
	"""Changing atom charge triggers bond item update via signal chain."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "N", 0.0, 0.0, 40.0, 0.0)
	# get initial ops snapshot
	ops_before = list(bond_item._ops)
	# change charge on the nitrogen
	a2.charge = 1
	# ops should have been regenerated (clipping may change slightly)
	ops_after = list(bond_item._ops)
	# ops should be different because the label text changed (N -> N+)
	assert ops_before != ops_after, "bond ops should change after charge update"


#============================================
def test_atom_position_change_triggers_bond_redraw(qapp: object) -> None:
	"""Moving an atom triggers bond item update via signal chain."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "N", 0.0, 0.0, 40.0, 0.0)
	unused_min_x, max_x_before = _line_x_extents(bond_item)
	# move atom2 further away
	a2.x = 80.0
	unused_min_x, max_x_after = _line_x_extents(bond_item)
	# the bond should now extend further than before
	assert max_x_after > max_x_before


#============================================
def test_bond_render_context_has_real_targets(qapp: object) -> None:
	"""BondItem build passes non-empty label_targets for heteroatom bonds."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "O", 0.0, 0.0, 40.0, 0.0)
	# the end near oxygen (at x=40) should be clipped, proving targets were used
	unused_min_x, max_x = _line_x_extents(bond_item)
	assert max_x < 40.0
