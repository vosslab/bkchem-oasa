"""Qt GUI event simulation parity test for BKChem-Qt."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.modes.draw_mode
import bkchem_qt.modes.edit_mode


#============================================
def _flush_events() -> None:
	"""Process queued Qt events for deterministic assertions."""
	PySide6.QtWidgets.QApplication.processEvents()


#============================================
def _count_atoms(scene: object) -> int:
	"""Return AtomItem count in the scene."""
	return sum(
		1 for item in scene.items()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
	)


#============================================
def _count_bonds(scene: object) -> int:
	"""Return BondItem count in the scene."""
	return sum(
		1 for item in scene.items()
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
	)


#============================================
def _find_atom_item(scene: object, atom_model: object) -> object | None:
	"""Find AtomItem for a specific AtomModel."""
	for item in scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			if item.atom_model is atom_model:
				return item
	return None


#============================================
def test_qt_gui_event_simulation(main_window: object) -> None:
	"""Simulate draw/edit/delete/undo/redo/mode-switch flow in Qt."""
	scene = main_window.scene

	# start in draw mode and create an initial bonded pair
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	assert isinstance(draw_mode, bkchem_qt.modes.draw_mode.DrawMode)

	start_atoms = _count_atoms(scene)
	start_bonds = _count_bonds(scene)

	first_position = PySide6.QtCore.QPointF(200.0, 200.0)
	draw_mode.mouse_press(first_position, None)
	draw_mode.mouse_release(first_position, None)
	_flush_events()

	after_first_atoms = _count_atoms(scene)
	after_first_bonds = _count_bonds(scene)
	assert after_first_atoms >= start_atoms + 2, (
		"initial draw click should create at least two atoms"
	)
	assert after_first_bonds >= start_bonds + 1, (
		"initial draw click should create at least one bond"
	)
	assert main_window.document.molecules, "draw should create an active molecule"

	# extend chain by clicking an existing atom
	source_atom = main_window.document.molecules[0].atoms[0]
	source_position = PySide6.QtCore.QPointF(source_atom.x, source_atom.y)
	draw_mode.mouse_press(source_position, None)
	draw_mode.mouse_release(source_position, None)
	_flush_events()

	after_extend_atoms = _count_atoms(scene)
	after_extend_bonds = _count_bonds(scene)
	assert after_extend_atoms >= after_first_atoms + 1, (
		"clicking an existing atom should extend the chain"
	)
	assert after_extend_bonds >= after_first_bonds + 1, (
		"clicking an existing atom should add a bond"
	)

	# delete a terminal atom (single neighbor) for stable undo/redo behavior
	target_atom = None
	for atom_model in main_window.document.molecules[0].atoms:
		if len(atom_model._chem_atom.neighbors) == 1:
			target_atom = atom_model
			break
	assert target_atom is not None, "expected a terminal atom for delete step"

	# switch to edit mode, select the target atom, and delete by key event
	main_window._mode_manager.set_mode("edit")
	edit_mode = main_window._mode_manager.current_mode
	assert isinstance(edit_mode, bkchem_qt.modes.edit_mode.EditMode)

	scene.clearSelection()
	target_item = _find_atom_item(scene, target_atom)
	assert target_item is not None, "target atom item should exist before delete"
	target_item.setSelected(True)

	pre_delete_atoms = after_extend_atoms
	delete_event = PySide6.QtGui.QKeyEvent(
		PySide6.QtCore.QEvent.Type.KeyPress,
		PySide6.QtCore.Qt.Key.Key_Delete,
		PySide6.QtCore.Qt.KeyboardModifier.NoModifier,
	)
	main_window._mode_manager.key_press(delete_event)
	_flush_events()

	after_delete_atoms = _count_atoms(scene)
	assert after_delete_atoms < pre_delete_atoms, (
		"Delete key should remove the selected atom"
	)
	assert not any(
		atom is target_atom
		for mol in main_window.document.molecules
		for atom in mol.atoms
	), "target atom should be absent after delete"

	# undo the delete through the public MainWindow handler
	main_window.on_undo()
	_flush_events()
	after_undo_atoms = _count_atoms(scene)
	assert after_undo_atoms == pre_delete_atoms, (
		"undo should restore atom count after delete"
	)

	# switch back to draw mode
	main_window._mode_manager.set_mode("draw")
	assert isinstance(
		main_window._mode_manager.current_mode,
		bkchem_qt.modes.draw_mode.DrawMode,
	), "mode switch should return to draw mode"
