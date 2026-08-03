"""Action-layer authority for mixed CDML top-level transforms."""

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.actions.align_actions
import bkchem_qt.actions.object_actions
import bkchem_qt.canvas.document_projection
import bkchem_qt.dialogs.scale_dialog
import bkchem_qt.main_window
import bkchem_qt.models.document_object
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.undo.commands


_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="2cm" y="1cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'</molecule><arrow id="arrow1"><point x="4cm" y="2cm"/>'
	'<point x="6cm" y="2cm"/></arrow></cdml>'
)


#============================================
def _native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Create one active synchronized session containing mixed durable roots."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise RuntimeError("Mixed transform test projection is unavailable")
	return registered


#============================================
def _select_mixed_roots(session: object) -> None:
	"""Select one atom and one arrow, yielding molecule plus artwork roots."""
	session.scene.clearSelection()
	for item in session.scene.items():
		atom = getattr(item, "atom_model", None)
		object_model = getattr(item, "document_object_model", None)
		if getattr(atom, "backend_durable_id", None) == "a1":
			item.setSelected(True)
		if getattr(object_model, "object_id", None) == "arrow1":
			item.setSelected(True)
	if not bkchem_qt.canvas.document_projection.selected_top_level_transform_keys(
			session.document, session.scene,
		):
		raise RuntimeError("Mixed transform roots were not selected")


#============================================
def _legacy_isolated_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Create one active isolated session with a selected local presentation root."""
	session = _native_session(main_window)
	model = bkchem_qt.models.document_object.PresentationObject(
		"polyline", points=[(1.0, 1.0, None), (2.0, 2.0, None)],
	)
	item = bkchem_qt.canvas.document_projection.create_presentation_item(model)
	session.document.undo_stack.push(
		bkchem_qt.undo.commands.AddPresentationObjectCommand(
			session.document, session.scene, model, item,
		),
	)
	item.setSelected(True)
	if not session.legacy_isolated:
		raise RuntimeError("Legacy scale test did not isolate its session")
	return session


#============================================
def _invoke(app: object, mode: str) -> None:
	"""Invoke one stable visible action for its expected backend mode."""
	if mode.startswith("align-"):
		direction = {
			"align-top": "top", "align-bottom": "bottom", "align-left": "left",
			"align-right": "right", "align-center-x": "center_h",
			"align-center-y": "center_v",
		}[mode]
		bkchem_qt.actions.align_actions._align_selection(app, direction)
		return
	if mode == "mirror-vertical":
		bkchem_qt.actions.object_actions.handle_vertical_mirror(app)
		return
	bkchem_qt.actions.object_actions.handle_horizontal_mirror(app)


#============================================
@pytest.mark.parametrize("mode", (
	"align-top", "align-bottom", "align-left", "align-right", "align-center-x",
	"align-center-y", "mirror-vertical", "mirror-horizontal",
))
def test_visible_transform_actions_submit_their_documented_backend_mode(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch, mode: str,
		) -> None:
	"""Each non-modal menu action commits one plain session-bound transform."""
	session = _native_session(main_window)
	requests = []
	original = main_window.persistent_operation_capability_for

	def capture(target: object) -> object:
		"""Record an action request while retaining the production capability."""
		submit = original(target)
		def submit_and_record(request: object) -> object:
			"""Record one plain request before its ordinary session dispatch."""
			requests.append(request)
			return submit(request)
		return submit_and_record

	monkeypatch.setattr(main_window, "persistent_operation_capability_for", capture)
	try:
		_select_mixed_roots(session)
		before = session.backend_snapshot
		_invoke(main_window, mode)

		assert (
			dict(requests[0].payload)["mode"] == mode
			and session.backend_snapshot.revision == before.revision + 1
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_scale_action_uses_backend_history_and_preserves_a_canonical_noop(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Scale accepts factors through the session and leaves a 1x1 scale unchanged."""
	session = _native_session(main_window)
	requests = []
	original = main_window.persistent_operation_capability_for

	def capture(target: object) -> object:
		"""Record immutable Scale intent before ordinary session dispatch."""
		submit = original(target)
		def submit_and_record(request: object) -> object:
			"""Keep one plain request while preserving production dispatch."""
			requests.append(request)
			return submit(request)
		return submit_and_record

	monkeypatch.setattr(main_window, "persistent_operation_capability_for", capture)
	try:
		_select_mixed_roots(session)
		monkeypatch.setattr(
			bkchem_qt.dialogs.scale_dialog.ScaleDialog,
			"get_scale_factors", lambda _parent: (0.5, 2.0),
		)
		bkchem_qt.actions.object_actions.handle_scale(main_window)
		changed = session.backend_snapshot
		_select_mixed_roots(session)
		monkeypatch.setattr(
			bkchem_qt.dialogs.scale_dialog.ScaleDialog,
			"get_scale_factors", lambda _parent: (1.0, 1.0),
		)
		bkchem_qt.actions.object_actions.handle_scale(main_window)

		assert (
			dict(requests[0].payload)["mode"] == "scale"
			and dict(requests[0].payload)["scale_x"] == 0.5
			and dict(requests[0].payload)["scale_y"] == 2.0
			and session.can_undo_backend
			and session.backend_snapshot == changed
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_scale_modal_uses_its_captured_revision_and_reports_stale_result(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An edit during Scale leaves its frozen request stale without Qt undo."""
	session = _native_session(main_window)
	outcomes = []
	try:
		_select_mixed_roots(session)
		def change_then_choose(_parent: object) -> tuple[float, float]:
			"""Commit once while the dialog is open, then accept scale factors."""
			session.submit_top_level_transform(
				session.backend_snapshot.revision, "mirror-horizontal",
				(("molecule", "m1"), ("presentation", "arrow1")),
			)
			return (2.0, 2.0)

		monkeypatch.setattr(
			bkchem_qt.dialogs.scale_dialog.ScaleDialog,
			"get_scale_factors", change_then_choose,
		)
		monkeypatch.setattr(main_window, "_show_persistent_action_outcome", outcomes.append)
		bkchem_qt.actions.object_actions.handle_scale(main_window)

		assert (
			session.backend_snapshot.revision == 1
			and outcomes[-1].failure_kind == "revision-conflict"
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_scale_modal_never_redirects_after_tab_switch_or_same_tab_replacement(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A modal Scale intent submits nowhere after tab switch or replacement."""
	first = _native_session(main_window)
	second = _native_session(main_window)
	replacement = None
	try:
		main_window._activate_session(first)
		_select_mixed_roots(first)
		def switch_tab(_parent: object) -> tuple[float, float]:
			"""Switch away before the action can submit its captured intent."""
			main_window._activate_session(second)
			return (2.0, 2.0)

		monkeypatch.setattr(
			bkchem_qt.dialogs.scale_dialog.ScaleDialog,
			"get_scale_factors", switch_tab,
		)
		bkchem_qt.actions.object_actions.handle_scale(main_window)
		after_switch = (first.backend_snapshot.revision, second.backend_snapshot.revision)
		main_window._activate_session(first)
		_select_mixed_roots(first)
		def replace_origin(_parent: object) -> tuple[float, float]:
			"""Replace the exact originating tab before modal acceptance returns."""
			nonlocal replacement
			prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
				_CDML,
			)
			replacement = main_window._construct_session(prepared_native_cdml=prepared)
			main_window._replace_with_prebuilt_session(first, replacement, activate=True)
			return (2.0, 2.0)

		monkeypatch.setattr(
			bkchem_qt.dialogs.scale_dialog.ScaleDialog,
			"get_scale_factors", replace_origin,
		)
		bkchem_qt.actions.object_actions.handle_scale(main_window)

		assert (
			after_switch == (0, 0)
			and first not in main_window.sessions
			and main_window._active_session is replacement
		)
	finally:
		for session in (replacement, second, first):
			if session in main_window.sessions:
				main_window._remove_session(session)


#============================================
def test_isolated_scale_modal_tab_switch_preserves_both_documents(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An isolated Scale dialog cannot apply its old local data to another tab."""
	first = _legacy_isolated_session(main_window)
	second = _native_session(main_window)
	main_window._activate_session(first)
	before = (
		first.backend_snapshot.revision, first.document.undo_stack.count(),
		second.backend_snapshot.revision, second.document.undo_stack.count(),
	)
	try:
		def switch_tab(_parent: object) -> tuple[float, float]:
			"""Change active aliases before the isolated dialog returns."""
			main_window._activate_session(second)
			return (2.0, 2.0)

		monkeypatch.setattr(
			bkchem_qt.dialogs.scale_dialog.ScaleDialog,
			"get_scale_factors", switch_tab,
		)
		bkchem_qt.actions.object_actions.handle_scale(main_window)

		assert before == (
			first.backend_snapshot.revision, first.document.undo_stack.count(),
			second.backend_snapshot.revision, second.document.undo_stack.count(),
		)
	finally:
		for session in (second, first):
			if session in main_window.sessions:
				main_window._remove_session(session)


#============================================
def test_isolated_scale_modal_replacement_preserves_origin_and_replacement(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An isolated Scale dialog cannot apply retained local data after replacement."""
	origin = _legacy_isolated_session(main_window)
	origin_revision = origin.backend_snapshot.revision
	replacement = None
	try:
		def replace_origin(_parent: object) -> tuple[float, float]:
			"""Replace the local source tab before Scale returns its factors."""
			nonlocal replacement
			prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
				_CDML,
			)
			replacement = main_window._construct_session(prepared_native_cdml=prepared)
			main_window._replace_with_prebuilt_session(origin, replacement, activate=True)
			return (2.0, 2.0)

		monkeypatch.setattr(
			bkchem_qt.dialogs.scale_dialog.ScaleDialog,
			"get_scale_factors", replace_origin,
		)
		bkchem_qt.actions.object_actions.handle_scale(main_window)

		assert (
			origin.backend_snapshot.revision == origin_revision
			and replacement.backend_snapshot.revision == 0
			and replacement.document.undo_stack.count() == 0
		)
	finally:
		for session in (replacement, origin):
			if session in main_window.sessions:
				main_window._remove_session(session)


#============================================
def test_action_projection_recovery_reuses_the_accepted_snapshot_only(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A menu transform recovers its accepted snapshot without a second request."""
	session = _native_session(main_window)
	requests = []
	outcomes = []
	original = main_window.persistent_operation_capability_for

	def capture(target: object) -> object:
		"""Record persistent submissions while preserving the production capability."""
		submit = original(target)
		def submit_and_record(request: object) -> object:
			"""Record one action request before ordinary backend dispatch."""
			requests.append(request)
			return submit(request)
		return submit_and_record

	def unavailable(_snapshot: object) -> object:
		"""Report one projection installation failure after backend acceptance."""
		return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
			bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
			bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
		)

	monkeypatch.setattr(main_window, "persistent_operation_capability_for", capture)
	monkeypatch.setattr(main_window, "_show_persistent_action_outcome", outcomes.append)
	session.install_projection_lifecycle_port(
		bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, unavailable),
	)
	try:
		_select_mixed_roots(session)
		bkchem_qt.actions.object_actions.handle_horizontal_mirror(main_window)
		accepted = session.backend_snapshot
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		recovered = session.retry_current_backend_projection()

		assert (
			outcomes[-1].status == "unavailable"
			and len(requests) == 1
			and recovered.status == "accepted"
			and session.backend_snapshot == accepted
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_isolated_session_keeps_the_existing_local_transform_undo_path(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A real local edit selects the isolated local mirror authority route."""
	session = _native_session(main_window)
	try:
		legacy_model = bkchem_qt.models.document_object.PresentationObject(
			"polyline", points=[(1.0, 1.0, None), (2.0, 2.0, None)],
		)
		legacy_item = bkchem_qt.canvas.document_projection.create_presentation_item(
			legacy_model,
		)
		session.document.undo_stack.push(
			bkchem_qt.undo.commands.AddPresentationObjectCommand(
				session.document, session.scene, legacy_model, legacy_item,
			),
		)
		_select_mixed_roots(session)
		undo_count = session.document.undo_stack.count()
		bkchem_qt.actions.object_actions.handle_vertical_mirror(main_window)

		assert (
			session.legacy_isolated
			and session.document.undo_stack.count() == undo_count + 1
			and session.backend_snapshot.revision == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
