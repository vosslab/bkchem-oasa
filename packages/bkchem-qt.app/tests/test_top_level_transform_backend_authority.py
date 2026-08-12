"""Focused Qt adapter coverage for backend-owned top-level transforms."""

# PIP3 modules
import PySide6.QtWidgets
import shiboken6

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle


_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="2cm" y="1cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'</molecule><arrow id="arrow1"><point x="4cm" y="2cm"/>'
	'<point x="6cm" y="2cm"/></arrow></cdml>'
)
_IDLESS_ROOT_CDML = _CDML.replace('arrow id="arrow1"', 'arrow')
#============================================
def _new_session(main_window: bkchem_qt.main_window.MainWindow,
		cdml: str = _CDML) -> object:
	"""Return one standalone session loaded through the native CDML boundary."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(cdml)
	return bkchem_qt.models.document_session.DocumentSession(
		parent=main_window, theme_manager=main_window._theme_manager,
		prefs=main_window._prefs, mode_host=main_window, prepared_native_cdml=prepared,
	)


#============================================
def _install(session: object, deliver: object = None) -> None:
	"""Bind one projection port, defaulting to the production replacement path."""
	if deliver is None:
		deliver = session.replace_projection_from_backend_snapshot
	session.install_projection_lifecycle_port(
		bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, deliver),
	)


#============================================
def _dispose(session: object) -> None:
	"""Release a standalone session through its owning window reaper."""
	session.parent()._dispose_session_later(session)


#============================================
def _item(scene: PySide6.QtWidgets.QGraphicsScene, identifier: str) -> object:
	"""Return one projected item with the requested durable model ID."""
	return next(
		item for item in scene.items()
		if getattr(getattr(item, "document_object_model", None), "object_id", None) == identifier
		or getattr(getattr(item, "atom_model", None), "backend_durable_id", None) == identifier
		or getattr(getattr(item, "bond_model", None), "backend_durable_id", None) == identifier
	)


#============================================
def _presentation_item(scene: PySide6.QtWidgets.QGraphicsScene) -> object:
	"""Return the one projected presentation item in an inline fixture document."""
	return next(
		item for item in scene.items()
		if getattr(getattr(item, "document_object_model", None), "kind", None) == "arrow"
	)


#============================================
def test_transform_selection_uses_current_projection_membership(main_window: object) -> None:
	"""Current atom, bond, and artwork selections resolve to canonical roots."""
	session = _new_session(main_window)
	_install(session)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	try:
		_item(session.scene, "arrow1").setSelected(True)
		_item(session.scene, "a1").setSelected(True)
		_item(session.scene, "b1").setSelected(True)
		assert bkchem_qt.canvas.document_projection.selected_top_level_transform_keys(
			session.document, session.scene,
		) == (("molecule", "m1"), ("presentation", "arrow1"))
	finally:
		_dispose(session)


#============================================
def test_transform_selection_rejects_copied_current_model_metadata(main_window: object) -> None:
	"""A foreign item carrying a current molecule model cannot become a root."""
	session = _new_session(main_window)
	_install(session)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	try:
		lookalike = PySide6.QtWidgets.QGraphicsRectItem()
		lookalike.molecule_model = session.document.molecules[0]
		lookalike.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
		session.scene.addItem(lookalike)
		lookalike.setSelected(True)
		assert not bkchem_qt.canvas.document_projection.selected_top_level_transform_keys(
			session.document, session.scene,
		)
	finally:
		_dispose(session)


#============================================
def test_transform_selection_rejects_idless_persistent_root(main_window: object) -> None:
	"""An inline ID-less CDML arrow is not an addressable transform root."""
	session = _new_session(main_window, _IDLESS_ROOT_CDML)
	_install(session)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	try:
		_presentation_item(session.scene).setSelected(True)
		assert not bkchem_qt.canvas.document_projection.selected_top_level_transform_keys(
			session.document, session.scene,
		)
	finally:
		_dispose(session)


#============================================
def test_transform_rejects_valid_id_with_wrong_root_kind(main_window: object) -> None:
	"""OASA rejects a durable nonroot ID without session-side CDML inspection."""
	session = _new_session(main_window)
	_install(session)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	try:
		before = session.backend_snapshot
		outcome = session.submit_top_level_transform(
			before.revision, "mirror-horizontal", (("molecule", "point1"),),
		)
		assert outcome.failure_kind == "validation"
		assert (
			session.backend_snapshot == before
			and not session.can_undo_backend
			and not session.can_redo_backend
		)
	finally:
		_dispose(session)


#============================================
def test_current_projection_membership_rejects_retired_wrapper(main_window: object) -> None:
	"""A retired graphics wrapper returns false without crossing ``item.scene()``."""
	document = bkchem_qt.models.document.Document(main_window)
	scene = PySide6.QtWidgets.QGraphicsScene(main_window)
	item = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 1.0, 1.0)
	document.set_scene(scene)
	scene.addItem(item)
	document.register_current_projection_items((item,))
	shiboken6.delete(item)
	assert not document.is_current_projection_item(item)


#============================================
def test_transform_changed_acceptance_uses_backend_history(main_window: object) -> None:
	"""Changed transforms restore durable roots and backend undo/redo history."""
	session = _new_session(main_window)
	_install(session)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	try:
		outcome = session.submit_top_level_transform(
			session.backend_snapshot.revision, "mirror-horizontal",
			(("molecule", "m1"), ("presentation", "arrow1")),
		)
		assert outcome.status == "accepted" and session.can_undo_backend
		assert bkchem_qt.canvas.document_projection.selected_top_level_transform_keys(
			session.document, session.scene,
		) == (("molecule", "m1"), ("presentation", "arrow1"))
		assert session.undo_backend().status == "accepted" and session.redo_backend().status == "accepted"
	finally:
		_dispose(session)


#============================================
def test_transform_noop_and_stale_requests_leave_projection_intact(main_window: object) -> None:
	"""No-op and stale transforms retain one installed authoritative projection."""
	session = _new_session(main_window)
	_install(session)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	try:
		before = session.backend_snapshot
		projection = session.document
		noop = session.submit_top_level_transform(
			before.revision, "scale", (("molecule", "m1"),), 1.0, 1.0,
		)
		assert noop.status == "accepted" and session.document is projection
		changed = session.submit_top_level_transform(
			before.revision, "mirror-vertical", (("molecule", "m1"),),
		)
		stale = session.submit_top_level_transform(
			before.revision, "mirror-horizontal", (("molecule", "m1"),),
		)
		assert changed.status == "accepted" and stale.failure_kind == "revision-conflict"
	finally:
		_dispose(session)


#============================================
def test_transform_recovery_reprojects_accepted_snapshot_once(main_window: object) -> None:
	"""Accepted transform recovery uses the current snapshot without resubmission."""
	session = _new_session(main_window)
	calls = []
	original = session._backend_session.apply_top_level_transform

	def count(request: object) -> object:
		"""Record one backend submission while preserving the real operation."""
		calls.append(request)
		return original(request)

	def unavailable(snapshot: object) -> object:
		"""Report an installation failure after backend acceptance."""
		return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
			bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
			bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
		)

	session._backend_session.apply_top_level_transform = count
	_install(session, unavailable)
	try:
		outcome = session.submit_top_level_transform(
			session.backend_snapshot.revision, "mirror-horizontal",
			(("molecule", "m1"), ("presentation", "arrow1")),
		)
		accepted = session.backend_snapshot
		assert outcome.status == "unavailable" and len(calls) == 1
		_install(session)
		retried = session.retry_current_backend_projection()
		assert retried.status == "accepted" and session.backend_snapshot == accepted and len(calls) == 1
	finally:
		_dispose(session)
