"""Focused persistent-presentation interactions in edit mode."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.main_window
import bkchem_qt.models.document_object
import bkchem_qt.undo.commands


#============================================
class _MouseEvent:
	"""Minimal mode-event stand-in with a deterministic modifier state."""

	#============================================
	def __init__(self, modifiers: PySide6.QtCore.Qt.KeyboardModifier) -> None:
		"""Store the modifier state expected by EditMode."""
		self._modifiers = modifiers

	#============================================
	def modifiers(self) -> PySide6.QtCore.Qt.KeyboardModifier:
		"""Return the modifier state expected by EditMode."""
		return self._modifiers


#============================================
def _edit_mode(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Activate and return the document's edit interaction mode."""
	main_window._mode_manager.set_mode("edit")
	mode = main_window._mode_manager.current_mode
	assert mode is not None
	return mode


#============================================
def _add_presentation(main_window: bkchem_qt.main_window.MainWindow) -> tuple:
	"""Add one persistent line and return its model and projection."""
	model = bkchem_qt.models.document_object.PresentationObject(
		"polyline",
		attributes={"id": "editable-line"},
		points=[(40.0, 20.0, None), (70.0, 20.0, None)],
	)
	item = bkchem_qt.canvas.document_projection.create_presentation_item(model)
	assert item is not None
	main_window.document.undo_stack.push(
		bkchem_qt.undo.commands.AddPresentationObjectCommand(
			main_window.document, main_window.scene, model, item,
		),
	)
	return model, item


#============================================
def _add_atom(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Draw and return one atom through the public draw-mode implementation."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	assert draw_mode is not None
	atom_item = draw_mode._create_atom_at(20.0, 20.0, "C")
	assert atom_item is not None
	return atom_item


#============================================
def test_edit_mode_click_can_extend_atom_selection_to_presentation(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Shift-click extends an atom selection to persistent artwork."""
	atom_item = _add_atom(main_window)
	_unused_presentation, presentation_item = _add_presentation(main_window)
	edit_mode = _edit_mode(main_window)
	main_window.scene.clearSelection()
	plain_event = _MouseEvent(PySide6.QtCore.Qt.KeyboardModifier.NoModifier)
	shift_event = _MouseEvent(
		PySide6.QtCore.Qt.KeyboardModifier.ShiftModifier,
	)
	edit_mode.mouse_press(PySide6.QtCore.QPointF(55.0, 20.0), plain_event)
	edit_mode.mouse_press(PySide6.QtCore.QPointF(20.0, 20.0), shift_event)
	assert atom_item.isSelected() and presentation_item.isSelected()


#============================================
def test_edit_mode_mixed_drag_undo_restores_atom_and_presentation_geometry(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""One undo restores both sides of an atom-and-artwork drag together."""
	atom_item = _add_atom(main_window)
	presentation, presentation_item = _add_presentation(main_window)
	edit_mode = _edit_mode(main_window)
	main_window.scene.set_grid_snap_enabled(False)
	atom_item.setSelected(True)
	presentation_item.setSelected(True)
	before = ((atom_item.atom_model.x, atom_item.atom_model.y), presentation.points)
	event = _MouseEvent(PySide6.QtCore.Qt.KeyboardModifier.NoModifier)
	edit_mode.mouse_press(PySide6.QtCore.QPointF(20.0, 20.0), event)
	edit_mode.mouse_move(PySide6.QtCore.QPointF(35.0, 20.0), event)
	edit_mode.mouse_release(PySide6.QtCore.QPointF(35.0, 20.0), event)
	main_window.document.undo_stack.undo()
	assert (
		(atom_item.atom_model.x, atom_item.atom_model.y), presentation.points,
	) == before


#============================================
def test_edit_mode_deactivate_cancels_mixed_drag_preview_without_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Mode deactivation restores every mixed transient preview before release."""
	atom_item = _add_atom(main_window)
	presentation, presentation_item = _add_presentation(main_window)
	edit_mode = _edit_mode(main_window)
	main_window.scene.set_grid_snap_enabled(False)
	atom_item.setSelected(True)
	presentation_item.setSelected(True)
	before = ((atom_item.atom_model.x, atom_item.atom_model.y), presentation.points)
	undo_count = main_window.document.undo_stack.count()
	event = _MouseEvent(PySide6.QtCore.Qt.KeyboardModifier.NoModifier)
	edit_mode.mouse_press(PySide6.QtCore.QPointF(20.0, 20.0), event)
	edit_mode.mouse_move(PySide6.QtCore.QPointF(35.0, 20.0), event)
	edit_mode.deactivate()

	assert (
		(atom_item.atom_model.x, atom_item.atom_model.y), presentation.points,
	) == before and main_window.document.undo_stack.count() == undo_count


#============================================
def test_edit_mode_delete_undo_restores_same_presentation_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Delete/undo retains the original artwork projection and its model."""
	presentation, presentation_item = _add_presentation(main_window)
	edit_mode = _edit_mode(main_window)
	presentation_item.setSelected(True)
	edit_mode._delete_selected()
	main_window.document.undo_stack.undo()
	assert (
		presentation in main_window.document.presentation_objects
		and presentation_item.scene() is main_window.scene
	)
