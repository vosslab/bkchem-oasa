"""Focused backend-history behavior for molecular template placement."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.template_mode


#============================================
def test_template_placement_undo_restores_the_prior_backend_snapshot(
		main_window: object,
		) -> None:
	"""Template placement participates in the session's authoritative history."""
	session = next(
		candidate for candidate in main_window.sessions
		if candidate.document is main_window.document and candidate.scene is main_window.scene
	)
	before = session.backend_snapshot
	session.mode_manager.set_mode("template")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.template_mode.TemplateMode):
		raise AssertionError("Template mode did not activate for the active session")
	mode.mouse_press(PySide6.QtCore.QPointF(180.0, 220.0), None)
	undo = session.undo_backend()

	assert undo.status == "accepted" and session.backend_snapshot.cdml == before.cdml
