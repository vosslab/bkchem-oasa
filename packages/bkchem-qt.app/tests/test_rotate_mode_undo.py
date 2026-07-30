"""Focused persistent-state checks for rotate-mode drags."""

# PIP3 modules
import PySide6.QtCore


#============================================
def _selected_atom(main_window: object) -> object:
	"""Create and select one atom whose position can be rotated."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	atom_item = draw_mode._create_atom_at(100.0, 0.0, "C")
	atom_item.setSelected(True)
	return atom_item


#============================================
def _atom_state(atom_item: object, document: object) -> tuple[float, float, bool]:
	"""Return stable visible coordinates with the document dirty state."""
	state = (
		round(atom_item.atom_model.x, 6),
		round(atom_item.atom_model.y, 6),
		document.dirty,
	)
	return state


#============================================
def _rotate_preview(main_window: object) -> object:
	"""Start a deterministic quarter-turn preview around the origin."""
	main_window._mode_manager.set_mode("rotate")
	mode = main_window._mode_manager.current_mode
	mode.mouse_press(PySide6.QtCore.QPointF(0.0, 0.0), object())
	mode.mouse_move(PySide6.QtCore.QPointF(100.0, 0.0), object())
	mode.mouse_move(PySide6.QtCore.QPointF(0.0, 100.0), object())
	return mode


#============================================
def test_rotate_release_on_an_unsynchronized_atom_is_inert(
		main_window: object,
		) -> None:
	"""A local-only atom cannot become persistent through the rotate gesture."""
	atom_item = _selected_atom(main_window)
	main_window.document.mark_clean()
	mode = _rotate_preview(main_window)
	mode.mouse_release(PySide6.QtCore.QPointF(0.0, 100.0), object())

	assert _atom_state(atom_item, main_window.document) == (100.0, 0.0, False)


#============================================
def test_rotate_deactivate_cancels_an_unfinished_preview(
		main_window: object,
		) -> None:
	"""Changing mode abandons a live preview instead of persisting it."""
	atom_item = _selected_atom(main_window)
	main_window.document.mark_clean()
	mode = _rotate_preview(main_window)
	mode.deactivate()

	assert _atom_state(atom_item, main_window.document) == (100.0, 0.0, False)


#============================================
def test_rotate_release_without_motion_does_not_create_history(
		main_window: object,
		) -> None:
	"""A press-and-release without a drag leaves the saved state untouched."""
	atom_item = _selected_atom(main_window)
	main_window.document.mark_clean()
	main_window._mode_manager.set_mode("rotate")
	mode = main_window._mode_manager.current_mode
	origin = PySide6.QtCore.QPointF(0.0, 0.0)
	mode.mouse_press(origin, object())
	mode.mouse_release(origin, object())

	assert _atom_state(atom_item, main_window.document) == (100.0, 0.0, False)
