"""Session-bound routing for mixed top-level transform menu actions.

This module turns a selected Qt projection into a short-lived, plain CDML
operation request.  OASA owns every accepted persistent change; Qt keeps only
the interaction required to collect selection and scale factors.
"""

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.models.document_session


_MODE_LABELS = {
	"align-top": "Align Top",
	"align-bottom": "Align Bottom",
	"align-left": "Align Left",
	"align-right": "Align Right",
	"align-center-x": "Align Center Horizontally",
	"align-center-y": "Align Center Vertically",
	"scale": "Scale",
	"mirror-vertical": "Vertical Mirror",
	"mirror-horizontal": "Horizontal Mirror",
}


#============================================
def active_transform_session(app: object) -> object | None:
	"""Return the exact live session represented by all active app aliases."""
	session = getattr(app, "_active_session", None)
	document = getattr(app, "document", None)
	scene = getattr(app, "scene", None)
	view = getattr(app, "view", None)
	sessions = getattr(app, "sessions", ())
	if session is None or document is None or scene is None or view is None:
		return None
	if session.is_disposed or session not in sessions:
		return None
	if (
			session.document is not document
			or session.scene is not scene
			or session.view is not view
		):
		return None
	return session


#============================================
def _show_outcome(app: object, outcome: object) -> None:
	"""Display one typed session outcome and refresh menu state."""
	app._show_persistent_action_outcome(outcome)
	app._refresh_document_actions()


#============================================
def _capture_request_context(app: object, mode: str) -> tuple[object, int, tuple, object] | None:
	"""Capture one active backend transform target without retaining Qt wrappers."""
	if mode not in _MODE_LABELS:
		raise ValueError("Top-level transform mode is unsupported")
	session = active_transform_session(app)
	if session is None or not session.can_commit_persistent_action:
		app.statusBar().showMessage("Transform is unavailable", 3000)
		return None
	root_keys = bkchem_qt.canvas.document_projection.selected_top_level_transform_keys(
		session.document, session.scene,
	)
	if not root_keys:
		app.statusBar().showMessage(
			"Select only durable supported objects to transform", 3000,
		)
		return None
	try:
		submit = app.persistent_operation_capability_for(session)
	except ValueError:
		app.statusBar().showMessage("Transform is unavailable", 3000)
		return None
	context = (session, session.backend_snapshot.revision, root_keys, submit)
	return context


#============================================
def _submit_captured_transform(
		app: object, context: tuple[object, int, tuple, object], mode: str,
		scale_x: float | None = None, scale_y: float | None = None,
		) -> None:
	"""Submit one captured request only while its session remains active."""
	session, revision, root_keys, submit = context
	if active_transform_session(app) is not session:
		app.statusBar().showMessage("Transform no longer applies to this tab", 3000)
		return
	request = bkchem_qt.models.document_session.build_top_level_transform_request(
		revision, mode, root_keys, scale_x, scale_y,
	)
	# ``request`` and ``submit`` retain only immutable intent and the exact
	# session capability.  The selected document/scene wrappers were released
	# before this call, so accepted projection replacement never depends on them.
	outcome = submit(request)
	_show_outcome(app, outcome)


#============================================
def submit_backend_transform(app: object, mode: str) -> bool:
	"""Submit one non-modal backend-owned top-level transform when synchronized.

	Returns ``True`` only when the caller's active session is synchronized and
	the operation was routed through its captured backend capability.
	"""
	context = _capture_request_context(app, mode)
	if context is None:
		return False
	_submit_captured_transform(app, context, mode)
	return True


#============================================
def submit_scale_transform(app: object, get_scale_factors: object) -> bool:
	"""Capture a synchronized scale request before a modal factor choice.

	The dialog sees no document, scene, projection, or session model.  An edit
	committed while it is open intentionally makes the frozen revision stale.
	"""
	context = _capture_request_context(app, "scale")
	if context is None:
		return False
	factors = get_scale_factors(app)
	if factors is None:
		return True
	if type(factors) is not tuple or len(factors) != 2:
		raise ValueError("Scale dialog must return two immutable factors")
	_submit_captured_transform(app, context, "scale", factors[0], factors[1])
	return True
