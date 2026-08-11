"""Focused persistence checks for presentation drawing modes."""

# PIP3 modules
import pytest
import PySide6.QtCore
import PySide6.QtWidgets

import bkchem_qt.main_window


#============================================
def _text_input(
		_parent: PySide6.QtWidgets.QWidget,
		_title: str,
		_label: str,
		) -> tuple[str, bool]:
	"""Provide deterministic text for the native annotation dialog."""
	return ("Heat", True)


#============================================
def test_arrow_drag_projects_backend_issued_persistent_id(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A drawn arrow is projected from canonical backend CDML, not Qt undo."""
	main_window._on_new()
	session = main_window._active_session
	try:
		main_window._mode_manager.set_mode("arrow")
		mode = main_window._mode_manager.current_mode
		start = PySide6.QtCore.QPointF(20.0, 30.0)
		end = PySide6.QtCore.QPointF(120.0, 30.0)
		mode.mouse_press(start, object())
		mode.mouse_move(end, object())
		mode.mouse_release(end, object())
		arrow_model = main_window.document.presentation_objects[-1]
		assert (
			arrow_model.attributes["id"] in session.backend_snapshot.cdml
			and not main_window.document.undo_stack.canUndo()
		)
	finally:
		assert main_window._remove_session(session)


#============================================
def test_text_mode_annotation_uses_backend_authority_without_qt_undo(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""One Text click projects OASA text without creating a Qt undo command."""
	main_window._on_new()
	session = main_window._active_session
	removed = False
	try:
		monkeypatch.setattr(PySide6.QtWidgets.QInputDialog, "getText", _text_input)
		main_window._mode_manager.set_mode("text")
		mode = main_window._mode_manager.current_mode
		outcomes = []
		operation = mode._persistent_operation

		def capture_outcome(request: object) -> object:
			"""Retain the real backend outcome while preserving the installed seam."""
			outcome = operation(request)
			outcomes.append(outcome)
			return outcome

		mode.set_persistent_operation(capture_outcome)
		mode.mouse_press(PySide6.QtCore.QPointF(70.0, 80.0), object())
		provisional_id = next(iter(outcomes[0].commit.id_map))
		durable_id = next(iter(outcomes[0].commit.id_map.values()))
		text_model = main_window.document.presentation_objects[-1]
		projected_semantics = {
			"kind": text_model.kind,
			"id": text_model.object_id,
			"content": text_model.display_text,
			"font": text_model.font_attributes,
		}
		projected_point = text_model.points[0][:2]
		qt_undo_available = main_window.document.undo_stack.canUndo()
	finally:
		removed = main_window._remove_session(session)

	assert (
		projected_semantics
		== {
			"kind": "text",
			"id": durable_id,
			"content": "Heat",
			"font": {"family": "Arial", "size": "14", "color": "#000000"},
		}
		and projected_point == pytest.approx((70.0, 80.0), abs=0.02)
	)
	assert durable_id != provisional_id and not qt_undo_available and removed
