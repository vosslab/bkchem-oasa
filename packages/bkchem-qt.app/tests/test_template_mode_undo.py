"""Focused backend-history behavior for molecular template placement."""


#============================================
def test_template_placement_undo_restores_the_prior_backend_snapshot(
		main_window: object,
		) -> None:
	"""Template placement participates in the session's authoritative history."""
	session = main_window._active_session
	before = session.backend_snapshot
	main_window._mode_manager.set_mode("template")
	mode = main_window._mode_manager.current_mode
	mode._place_template(180.0, 220.0)
	undo = session.undo_backend()

	assert undo.status == "accepted" and session.backend_snapshot.cdml == before.cdml
