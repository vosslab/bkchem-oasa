"""Regression coverage for terminal graphics retained by Qt undo history."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets
import pytest
import shiboken6

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.undo.commands


#============================================
class _NoopCommand(PySide6.QtGui.QUndoCommand):
	"""Provide a real new QUndoStack branch without retaining graphics."""


#============================================
def _presentation(object_id: str) -> bkchem_qt.models.document_object.PresentationObject:
	"""Return one minimal persistent presentation model for an undo command."""
	return bkchem_qt.models.document_object.PresentationObject(
		"polyline", attributes={"id": object_id},
		points=[(1.0, 1.0, None), (5.0, 5.0, None)],
	)


#============================================
def _undone_add_command(
		document: bkchem_qt.models.document.Document,
		scene: PySide6.QtWidgets.QGraphicsScene,
		object_id: str,
		) -> tuple[PySide6.QtWidgets.QGraphicsRectItem, PySide6.QtWidgets.QGraphicsRectItem]:
	"""Push then undo an actual graphics-retaining presentation command."""
	root = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 6.0, 6.0)
	child = PySide6.QtWidgets.QGraphicsRectItem(1.0, 1.0, 2.0, 2.0, root)
	document.undo_stack.push(bkchem_qt.undo.commands.AddPresentationObjectCommand(
		document, scene, _presentation(object_id), root,
	))
	document.undo_stack.undo()
	return root, child


#============================================
def test_rebranch_terminally_retires_detached_redo_graphics_tree(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A new branch explicitly retires an undone command's complete tree."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	root, child = _undone_add_command(document, scene, "history-rebranch")

	document.undo_stack.push(_NoopCommand("New branch"))

	assert not shiboken6.isValid(root) and not shiboken6.isValid(child)


#============================================
def test_history_clear_terminally_retires_detached_command_graphics_tree(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Clear retires an undone command tree before Qt releases its command."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	root, child = _undone_add_command(document, scene, "history-clear")

	document.undo_stack.clear()

	assert not shiboken6.isValid(root) and not shiboken6.isValid(child)


#============================================
def test_document_undo_history_rejects_unowned_finite_eviction(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A future finite history policy must define graphics retirement first."""
	document = bkchem_qt.models.document.Document()

	with pytest.raises(ValueError, match="requires unlimited capacity"):
		document.undo_stack.setUndoLimit(1)

	assert document.undo_stack.undoLimit() == 0


#============================================
def test_rebranch_failure_transfers_detached_root_to_document_reaper(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed rebranch deletion stays reaper-owned until explicit retry."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	reaper = bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper()
	document.set_graphics_retirement_reaper(reaper)
	root, child = _undone_add_command(document, scene, "history-reaper")
	real_delete = shiboken6.delete

	#============================================
	def fail_root_delete(item: object) -> None:
		"""Leave the root under the document's explicit terminal owner once."""
		if item is root:
			raise RuntimeError("injected undo-history root retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6, "delete", fail_root_delete,
	)
	document.undo_stack.push(_NoopCommand("New branch"))

	assert (
		shiboken6.isValid(root)
		and not shiboken6.isValid(child)
		and reaper.owns_detached_root(root)
	)

	monkeypatch.undo()
	reaper.drain()
	assert not shiboken6.isValid(root) and not reaper.owns_detached_root(root)


#============================================
def test_ownerless_history_retry_stays_with_global_terminal_reaper(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A standalone Document never reclaims a failed history root from its reaper."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	root, child = _undone_add_command(document, scene, "history-ownerless-reaper")
	reaper = bkchem_qt.canvas.graphics_retirement.detached_graphics_retirement_reaper
	delete_attempts = 0
	real_delete = shiboken6.delete

	#============================================
	def fail_first_root_delete(item: object) -> None:
		"""Keep the first failed root under the process-level terminal owner."""
		nonlocal delete_attempts
		if item is root:
			delete_attempts += 1
			if delete_attempts == 1:
				raise RuntimeError("injected ownerless history retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete",
		fail_first_root_delete,
	)
	# A history-clear scan fails once.  Repeating the scan before Qt releases its
	# command must leave the explicit process reaper as the sole terminal owner.
	document._retire_all_history_graphics()
	document._retire_all_history_graphics()

	assert (
		delete_attempts == 1
		and shiboken6.isValid(root)
		and not shiboken6.isValid(child)
		and reaper.owns_detached_root(root)
	)

	monkeypatch.undo()
	reaper.drain()
	assert not shiboken6.isValid(root) and not reaper.owns_detached_root(root)
	document.undo_stack.clear()


#============================================
def test_document_clear_keeps_scene_and_history_retirement_separate(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Clear gives a failed detached history root one session-owned record."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	reaper = bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper()
	document.set_graphics_retirement_reaper(reaper)

	live_model = _presentation("history-live")
	live_root = bkchem_qt.canvas.document_projection.create_presentation_item(live_model)
	assert live_root is not None
	live_child = PySide6.QtWidgets.QGraphicsRectItem(1.0, 1.0, 2.0, 2.0, live_root)
	document.undo_stack.push(bkchem_qt.undo.commands.AddPresentationObjectCommand(
		document, scene, live_model, live_root,
	))
	detached_root, detached_child = _undone_add_command(
		document, scene, "history-detached",
	)
	assert live_root.scene() is scene
	assert detached_root.scene() is None
	real_delete = shiboken6.delete

	#============================================
	def fail_detached_root_delete(item: object) -> None:
		"""Keep just the detached command root for the reaper retry."""
		if item is detached_root:
			raise RuntimeError("injected Document.clear detached-history failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete",
		fail_detached_root_delete,
	)
	document.clear()

	assert not shiboken6.isValid(live_root)
	assert not shiboken6.isValid(live_child)
	assert shiboken6.isValid(detached_root)
	assert not shiboken6.isValid(detached_child)
	assert reaper.owns_detached_root(detached_root)
	assert not bkchem_qt.canvas.graphics_retirement.detached_graphics_retirement_reaper.owns_detached_root(
		detached_root,
	)

	monkeypatch.undo()
	reaper.drain()
	assert not shiboken6.isValid(detached_root)
	assert not reaper.owns_detached_root(detached_root)


#============================================
def test_session_disposal_keeps_failed_history_root_reaper_owned_until_resolution(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Session disposal gives a failed history root one delete attempt and owner."""
	session = main_window.sessions[0]
	document = session.document
	root, child = _undone_add_command(document, session.scene, "history-session")
	delete_attempts = 0
	real_delete = shiboken6.delete

	#============================================
	def fail_first_root_delete(item: object) -> None:
		"""Leave the detached history root for MainWindow's controlled retry."""
		nonlocal delete_attempts
		if item is root:
			delete_attempts += 1
			if delete_attempts == 1:
				raise RuntimeError("injected session-history retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete",
		fail_first_root_delete,
	)
	with pytest.raises(RuntimeError, match="Session was queued after a disposal failure"):
		main_window._remove_session(session)

	pending = main_window._pending_session_deletions[id(session)]
	records = pending.retained_graphics_records
	assert (
		delete_attempts == 1
		and shiboken6.isValid(root)
		and not shiboken6.isValid(child)
		and records is not None
		and records.detached is not None
		and records.detached.roots == [root]
	)

	assert main_window._pending_session_graphics_are_resolved(pending)
	assert delete_attempts == 2 and not shiboken6.isValid(root)
	monkeypatch.undo()
