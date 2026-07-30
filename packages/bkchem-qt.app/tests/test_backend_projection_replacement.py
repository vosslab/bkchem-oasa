"""Behavioral checks for disposable Qt projections of backend CDML."""

# PIP3 modules
import pytest
import PySide6.QtCore
import PySide6.QtWidgets
import shiboken6

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.mark_item
import bkchem_qt.canvas.document_projection
import bkchem_qt.io.cdml_document_io
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import oasa.cdml_document


_ARROW_CDML = (
	'<cdml version="0.15"><arrow id="arrow-1">'
	'<point x="1cm" y="1cm"/><point x="3cm" y="1cm"/>'
	'</arrow></cdml>'
)
_ARROW_AND_PLUS_CDML = (
	'<cdml version="0.15"><arrow id="arrow-1">'
	'<point x="1cm" y="1cm"/><point x="3cm" y="1cm"/>'
	'</arrow><plus id="plus-1"><point x="4cm" y="1cm"/>'
	'</plus></cdml>'
)
_TWO_ATOM_CDML = (
	'<cdml version="0.15"><molecule id="molecule-1">'
	'<atom id="atom-1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="atom-2" name="O"><point x="2cm" y="1cm"/></atom>'
	'</molecule></cdml>'
)
_MARKED_ATOM_CDML = (
	'<cdml version="0.15"><molecule id="molecule-1">'
	'<atom id="atom-1" name="C"><point x="1cm" y="1cm"/>'
	'<mark type="plus"/></atom></molecule></cdml>'
)


#============================================
def _new_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Create one isolated session for a backend projection test."""
	main_window._on_new()
	return main_window.sessions[-1]


#============================================
def _close_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Retire one test session without changing its backend saved baseline."""
	assert main_window._remove_session(session)


#============================================
def test_stale_or_foreign_snapshot_cannot_mutate_live_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Only the exact current snapshot may replace a session projection."""
	session = _new_tab(main_window)
	try:
		stale = session.backend_snapshot
		commit = session.commit_complete_candidate(_ARROW_CDML)
		foreign = oasa.cdml_document.CDMLDocumentSession.load(
			_ARROW_AND_PLUS_CDML,
		).snapshot()
		old_document = session.document
		assert not session.replace_projection_from_backend_snapshot(stale)
		assert (
			not session.replace_projection_from_backend_snapshot(foreign)
			and session.document is old_document
			and session.backend_snapshot == commit.snapshot
		)
	finally:
		_close_tab(main_window, session)


#============================================
def test_document_graphics_disposal_exhausts_items_after_binding_failure(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An item disposal fault cannot retain its scene or signal connection."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml(_ARROW_CDML)
	document = prepared.document
	arrow_item = prepared.presentation_items[0]
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	scene.addItem(arrow_item)
	binding = arrow_item._projection_binding

	def fail_before_item_cleanup() -> None:
		"""Bypass ordinary wrapper cleanup at the first item-disposal boundary."""
		raise RuntimeError("graphics item disposal failed")

	monkeypatch.setattr(arrow_item, "dispose", fail_before_item_cleanup)
	try:
		with pytest.raises(RuntimeError, match="Document graphics were detached"):
			document._dispose_document_graphics()
		assert not shiboken6.isValid(arrow_item) and binding._model is None
	finally:
		monkeypatch.undo()
		document.set_scene(None)
		bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)


#============================================
def test_detached_projection_disposal_exhausts_items_after_item_failure(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A detached-item fault cannot retain graphics or document-owned models."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml(_ARROW_CDML)
	arrow_item = prepared.presentation_items[0]
	binding = arrow_item._projection_binding

	def fail_before_item_cleanup() -> None:
		"""Bypass ordinary detached-wrapper cleanup at its first boundary."""
		raise RuntimeError("detached graphics item disposal failed")

	monkeypatch.setattr(arrow_item, "dispose", fail_before_item_cleanup)
	try:
		with pytest.raises(RuntimeError, match="Prepared projection was released"):
			bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)
		assert not shiboken6.isValid(arrow_item) and binding._item is None
	finally:
		monkeypatch.undo()


#============================================
def test_dispose_prepared_projection_disconnects_detached_graphics(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Prepared detached artwork crosses explicit terminal retirement."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml(_ARROW_CDML)
	arrow_item = prepared.presentation_items[0]
	bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)
	qapp.processEvents()
	assert not shiboken6.isValid(arrow_item)


#============================================
def test_dispose_prepared_projection_releases_detached_binding(
		) -> None:
	"""Disposing a prepared bundle releases its temporary model callback."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml(_ARROW_CDML)
	arrow_item = prepared.presentation_items[0]
	binding = arrow_item._projection_binding
	bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)
	assert binding._item is None


#============================================
def test_dispose_prepared_projection_uses_supplied_session_reaper(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Prepared cleanup keeps an injected terminal failure with its caller."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml(_ARROW_CDML)
	arrow_item = prepared.presentation_items[0]
	reaper = bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper()
	real_delete = shiboken6.delete

	#============================================
	def fail_arrow_delete(item: object) -> None:
		"""Retain the explicit prepared root until its owner retries it."""
		if item is arrow_item:
			raise RuntimeError("injected prepared projection retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6, "delete", fail_arrow_delete,
	)
	try:
		with pytest.raises(RuntimeError, match="Prepared projection was released"):
			bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared, reaper)
		assert shiboken6.isValid(arrow_item) and reaper.owns_detached_root(arrow_item)
		monkeypatch.undo()
		reaper.drain()
		assert not shiboken6.isValid(arrow_item)
	finally:
		monkeypatch.undo()


#============================================
def test_partial_detached_molecule_builder_releases_earlier_items(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A later atom-construction failure disconnects earlier detached graphics."""
	original_init = bkchem_qt.canvas.items.atom_item.AtomItem.__init__
	created = []

	def fail_second_atom(
			self: bkchem_qt.canvas.items.atom_item.AtomItem,
			*args: object, **kwargs: object,
			) -> None:
		"""Keep the first item, then force the second constructor to fail."""
		if created:
			raise RuntimeError("later atom item failed")
		original_init(self, *args, **kwargs)
		created.append(self)

	monkeypatch.setattr(
		bkchem_qt.canvas.items.atom_item.AtomItem, "__init__", fail_second_atom,
	)
	with pytest.raises(RuntimeError, match="later atom item failed"):
		bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml(_TWO_ATOM_CDML)
	first_item = created[0]
	assert not shiboken6.isValid(first_item)


#============================================
def test_invalid_prepared_mark_is_rejected_without_scene_ownership_probe(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Atom-owned marks never need a scene() probe during installation."""
	session = _new_tab(main_window)
	try:
		commit = session.commit_complete_candidate(_MARKED_ATOM_CDML)
		prepared = bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml(
			commit.snapshot.cdml,
		)
		mark = prepared.mark_items[0]
		shiboken6.delete(mark)
		monkeypatch.setattr(
			bkchem_qt.io.cdml_document_io,
			"prepare_projection_from_cdml", lambda *_args: prepared,
		)
		result = session.replace_projection_from_backend_snapshot(commit.snapshot)
		assert result.status == "installation-failed" and session.document is None
	finally:
		_close_tab(main_window, session)


#============================================
def test_valid_prepared_mark_keeps_atom_parent_without_scene_probe(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A valid mark enters the session scene through its installed atom parent."""
	session = _new_tab(main_window)
	created_marks = []
	original_create_mark = bkchem_qt.canvas.document_projection.create_mark_item
	original_scene = bkchem_qt.canvas.items.mark_item.MarkItem.scene

	def remember_mark(model: object, atom_item: object) -> object:
		"""Capture the one detached mark produced by the prepared projection."""
		item = original_create_mark(model, atom_item)
		if item is not None:
			created_marks.append(item)
		return item

	def fail_mark_scene(self: object) -> object:
		"""Prove installation never probes a child mark's scene ownership."""
		raise AssertionError("mark scene() must not be queried during installation")

	try:
		commit = session.commit_complete_candidate(_MARKED_ATOM_CDML)
		monkeypatch.setattr(
			bkchem_qt.canvas.document_projection, "create_mark_item", remember_mark,
		)
		monkeypatch.setattr(
			bkchem_qt.canvas.items.mark_item.MarkItem, "scene", fail_mark_scene,
		)
		assert session._projection_lifecycle_port.project(commit.snapshot)
		mark = created_marks[0]
		parent = mark.parentItem()
		assert isinstance(parent, bkchem_qt.canvas.items.atom_item.AtomItem)
		assert original_scene(mark) is session.scene
		assert session.backend_projection_synchronized
	finally:
		monkeypatch.undo()
		_close_tab(main_window, session)


#============================================
def test_failed_current_install_retries_only_accepted_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An accepted newer revision remains final after projection retirement."""
	session = _new_tab(main_window)
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		assert session.replace_projection_from_backend_snapshot(first.snapshot)
		accepted = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)
		install = session._install_prepared_projection
		def fail_install(*_args: object) -> None:
			"""Inject one install failure after the live projection retires."""
			raise RuntimeError("install fault")
		monkeypatch.setattr(
			session, "_install_prepared_projection", fail_install,
		)
		assert (
			not session.replace_projection_from_backend_snapshot(accepted.snapshot)
			and session.document is None
			and session.backend_snapshot == accepted.snapshot
		)
		monkeypatch.setattr(session, "_install_prepared_projection", install)
		prepared_snapshots = []
		prepare = bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml
		def remember_prepare(cdml: str, reaper: object) -> object:
			"""Record the exact backend CDML prepared by explicit recovery."""
			prepared_snapshots.append(cdml)
			return prepare(cdml, reaper)
		monkeypatch.setattr(
			bkchem_qt.io.cdml_document_io, "prepare_projection_from_cdml", remember_prepare,
		)
		retry = session.retry_current_backend_projection()
		assert retry.status == "accepted" and prepared_snapshots == [accepted.snapshot.cdml]
	finally:
		_close_tab(main_window, session)


#============================================
def test_candidate_cleanup_failure_retains_primary_replacement_diagnostic(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Candidate cleanup cannot hide the post-retirement install failure."""
	session = _new_tab(main_window)
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		assert session.replace_projection_from_backend_snapshot(first.snapshot)
		accepted = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)
		original_cleanup = session._dispose_prepared_projection

		def fail_install(*_args: object) -> None:
			"""Fail after the current projection has become terminally retired."""
			raise RuntimeError("primary installation failure")

		def cleanup_then_fail(candidate: object) -> None:
			"""Complete candidate retirement, then report its independent fault."""
			original_cleanup(candidate)
			raise RuntimeError("candidate cleanup failure")

		monkeypatch.setattr(session, "_install_prepared_projection", fail_install)
		monkeypatch.setattr(session, "_dispose_prepared_projection", cleanup_then_fail)
		result = session.replace_projection_from_backend_snapshot(accepted.snapshot)
		assert (
			result.status == "installation-failed"
			and result.phase == "installation"
			and session.document is None
			and not session.backend_projection_synchronized
			and not session._projection_replacing
			and session.projection_error is result.diagnostic
			and isinstance(session.projection_error.__cause__, RuntimeError)
			and str(session.projection_error.__cause__) == "primary installation failure"
			and any(
				str(diagnostic) == "candidate cleanup failure"
				for diagnostic in session._teardown_diagnostics
			)
		)
	finally:
		monkeypatch.undo()
		_close_tab(main_window, session)


#============================================
def test_preparation_unavailable_keeps_only_view_aliases_bound(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A stale displayed projection remains view-only after preparation fails."""
	session = _new_tab(main_window)
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		assert session._projection_lifecycle_port.project(first.snapshot)
		old_document = session.document
		assert main_window._document_signal_source is old_document
		accepted = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)

		def fail_prepare(*_args: object) -> object:
			"""Reject preparation without retiring the existing view-only document."""
			raise RuntimeError("preparation fault")

		monkeypatch.setattr(
			bkchem_qt.io.cdml_document_io, "prepare_projection_from_cdml", fail_prepare,
		)
		result = session._projection_lifecycle_port.project(accepted.snapshot)
		assert (
			result.status == "preparation-unavailable"
			and session.document is old_document
			and main_window.document is old_document
			and main_window._document_signal_source is None
			and main_window._property_dock._document is None
			and not session.backend_projection_synchronized
			and not session.can_commit_persistent_action
		)
	finally:
		monkeypatch.undo()
		_close_tab(main_window, session)


#============================================
def test_stale_session_port_is_inert_and_cannot_retarget_active_aliases(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained foreign port cannot change the active tab or its dock aliases."""
	foreign = main_window.sessions[0]
	active = _new_tab(main_window)
	try:
		port = foreign._projection_lifecycle_port
		result = port.project(foreign.backend_snapshot)
		assert result.installed and main_window.document is active.document
		aliases = (
			main_window._active_session, main_window._document, main_window._scene,
			main_window._view, main_window._mode_manager, main_window._property_dock._document,
		)
		foreign.clear_projection_lifecycle_port()
		assert port.project(foreign.backend_snapshot).status == "session-unavailable"
		assert aliases == (
			main_window._active_session, main_window._document, main_window._scene,
			main_window._view, main_window._mode_manager, main_window._property_dock._document,
		)
	finally:
		_close_tab(main_window, active)


#============================================
def test_delivery_that_clears_its_port_cannot_emit_a_stale_notice(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A synchronous delivery disposal leaves every active alias and dock inert."""
	foreign = main_window.sessions[0]
	active = _new_tab(main_window)
	notices = []
	try:
		def clear_port(_snapshot: object) -> object:
			"""Invalidate this delivery seam while returning a computed result."""
			foreign.clear_projection_lifecycle_port()
			return bkchem_qt.models.document_session.ProjectionLifecycleResult(
				bkchem_qt.models.document_session.ProjectionLifecycleStatus.INSTALLED,
				bkchem_qt.models.document_session.ProjectionLifecyclePhase.COMPLETE,
			)

		port = bkchem_qt.models.document_session.SessionProjectionLifecyclePort(
			foreign, clear_port,
			lambda _session, result: notices.append(result),
		)
		foreign.install_projection_lifecycle_port(port)
		aliases = (
			main_window._active_session, main_window._document, main_window._scene,
			main_window._view, main_window._mode_manager, main_window._property_dock._document,
		)
		result = port.project(foreign.backend_snapshot)
		assert result.installed and notices == []
		assert aliases == (
			main_window._active_session, main_window._document, main_window._scene,
			main_window._view, main_window._mode_manager, main_window._property_dock._document,
		)
	finally:
		_close_tab(main_window, active)
