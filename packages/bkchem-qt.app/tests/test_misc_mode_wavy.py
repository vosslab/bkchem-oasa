"""Focused public-dispatch contracts for the Qt Misc mode."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.modes.misc_mode


#============================================
def _live_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Return the public live session that owns the public active document."""
	return next(session for session in main_window.sessions if session.document is main_window.document)


#============================================
def _select_wavy(
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> bkchem_qt.modes.misc_mode.MiscMode:
	"""Select Wavy through the public session mode manager and BaseMode API."""
	session.mode_manager.set_mode("misc")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.misc_mode.MiscMode):
		raise TypeError("Misc selection did not install MiscMode")
	mode.set_submode("wavy")
	return mode


#============================================
def _drag_wavy(
		session: bkchem_qt.models.document_session.DocumentSession,
		start: PySide6.QtCore.QPointF, end: PySide6.QtCore.QPointF,
		) -> None:
	"""Dispatch one Wavy drag through public ModeManager mouse methods."""
	session.mode_manager.mouse_press(start, object())
	session.mode_manager.mouse_move(end, object())
	session.mode_manager.mouse_release(end, object())


def test_zero_length_wavy_gesture_is_a_clean_no_op(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A press/release without displacement leaves backend authority unchanged."""
	session = _live_session(main_window)
	_select_wavy(session)
	before_snapshot = session.backend_snapshot
	point = PySide6.QtCore.QPointF(20.0, 30.0)
	_drag_wavy(session, point, point)

	assert session.backend_snapshot == before_snapshot
	assert session.document.presentation_objects == []


#============================================
def test_extreme_wavy_drag_leaves_public_document_unchanged(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An unrepresentable drag leaves backend authority and projection unchanged."""
	session = _live_session(main_window)
	_select_wavy(session)
	before_snapshot = session.backend_snapshot
	_drag_wavy(session, PySide6.QtCore.QPointF(-1e308, 0), PySide6.QtCore.QPointF(1e308, 0))

	assert session.backend_snapshot == before_snapshot
	assert session.document.presentation_objects == []


#============================================
def test_absent_wavy_callback_leaves_state_clean_and_accepts_a_new_gesture(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An absent callback makes no edit, then a new gesture reaches an injected callback."""
	session = _live_session(main_window)
	mode = _select_wavy(session)
	before_snapshot = session.backend_snapshot
	mode.set_persistent_operation(None)
	_drag_wavy(session, PySide6.QtCore.QPointF(20.0, 30.0), PySide6.QtCore.QPointF(100.0, 50.0))
	received: list[tuple[tuple[str, object], ...]] = []

	def capture(
			request: bkchem_qt.models.document_session.PersistentOperationRequest,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Record a second public request without accepting a local fallback."""
		received.append(request.payload)
		return bkchem_qt.models.document_session.PersistentActionOutcome(
			"rejected", "Wavy creation rejected", None,
		)

	mode.set_persistent_operation(capture)
	_drag_wavy(session, PySide6.QtCore.QPointF(200.0, 300.0), PySide6.QtCore.QPointF(260.0, 330.0))

	assert session.backend_snapshot == before_snapshot
	assert received == [(("start", (200.0, 300.0)), ("end", (260.0, 330.0)))]


#============================================
def test_rejected_wavy_callback_leaves_state_clean_and_accepts_a_new_gesture(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A rejected callback makes no edit and receives each independent public drag."""
	session = _live_session(main_window)
	mode = _select_wavy(session)
	before_snapshot = session.backend_snapshot
	received: list[tuple[tuple[str, object], ...]] = []

	def reject(
			request: bkchem_qt.models.document_session.PersistentOperationRequest,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Record each request while returning a typed backend rejection."""
		received.append(request.payload)
		return bkchem_qt.models.document_session.PersistentActionOutcome(
			"rejected", "Wavy creation rejected", None,
		)

	mode.set_persistent_operation(reject)
	_drag_wavy(session, PySide6.QtCore.QPointF(20.0, 30.0), PySide6.QtCore.QPointF(100.0, 50.0))
	_drag_wavy(session, PySide6.QtCore.QPointF(200.0, 300.0), PySide6.QtCore.QPointF(260.0, 330.0))

	assert session.backend_snapshot == before_snapshot
	assert received[-1] == (("start", (200.0, 300.0)), ("end", (260.0, 330.0)))
