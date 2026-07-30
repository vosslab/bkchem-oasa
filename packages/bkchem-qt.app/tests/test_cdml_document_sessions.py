"""Native-wrapper teardown regression coverage for CDML document sessions."""

# Standard Library
import pathlib

# PIP3 modules
import pytest
import shiboken6
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.canvas.graphics_retirement


FULL_DOCUMENT_CDML = """<?xml version="1.0" encoding="utf-8"?>
<cdml version="0.15" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
  <paper type="custom" orientation="landscape" size_x="280" size_y="180"/>
  <molecule id="mol-1">
    <atom id="atom-1" name="C"><point x="1.000cm" y="2.000cm"/><mark type="radical" value="1"/></atom>
  </molecule>
  <arrow id="arrow-1"><point x="3.000cm" y="4.000cm"/><point x="5.000cm" y="4.000cm"/></arrow>
</cdml>
"""


#============================================
class _UndoRetainedGraphicsCommand(PySide6.QtGui.QUndoCommand):
	"""Retain one detached graphics root across undo history for teardown."""

	#============================================
	def __init__(self, item: PySide6.QtWidgets.QGraphicsItem) -> None:
		"""Store the detached root without making a persistent edit."""
		super().__init__("Test graphics retention")
		self._item = item

	#============================================
	def redo(self) -> None:
		"""Keep this test-only command semantically inert."""

	#============================================
	def undo(self) -> None:
		"""Keep this test-only command semantically inert."""

	#============================================
	def graphics_items(self) -> list[PySide6.QtWidgets.QGraphicsItem]:
		"""Expose the detached root through the production undo protocol."""
		return [self._item]

#============================================
def _drain_deferred_deletes(app: PySide6.QtWidgets.QApplication) -> None:
	"""Deliver the same deferred-delete queue drained by the shared fixture."""
	for _pass in range(2):
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		app.processEvents()

#============================================
def test_removing_session_invalidates_document_projection_wrappers(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		tmp_path: pathlib.Path,
		) -> None:
	"""Session disposal invalidates projected artwork before Python GC runs."""
	source = tmp_path / "teardown.cdml"
	source.write_text(FULL_DOCUMENT_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	presentation_item = next(
		item for item in session.scene.items()
		if getattr(item, "document_object_model", None) is (
			session.document.presentation_objects[0]
		)
	)
	mark_item = next(
		item for item in session.scene.items()
		if getattr(item, "atom_mark_model", None) is session.document.marks[0]
	)
	scene = session.scene
	view = session.view
	main_window._on_new()

	removed = main_window._remove_session(session)
	_drain_deferred_deletes(qapp)

	assert removed and not any(
		shiboken6.isValid(wrapper)
		for wrapper in (presentation_item, mark_item, scene, view, session)
	)


#============================================
def test_graphics_rich_session_close_uses_the_reaper_protocol(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		tmp_path: pathlib.Path,
		) -> None:
	"""Public close retires labels, marks, preview, and undo-held graphics once."""
	source = tmp_path / "graphics-rich-teardown.cdml"
	source.write_text(FULL_DOCUMENT_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session

	atom_item = next(
		item for item in session.scene.items()
		if getattr(item, "atom_model", None) is session.document.molecules[0].atoms[0]
	)
	assert atom_item.childItems()
	mark_item = next(
		item for item in session.scene.items()
		if getattr(item, "atom_mark_model", None) is session.document.marks[0]
	)
	undo_item = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 8.0, 8.0)
	session.scene.addItem(undo_item)
	session.scene.removeItem(undo_item)
	session.document.undo_stack.push(_UndoRetainedGraphicsCommand(undo_item))

	arrow_mode = session.mode_manager._modes["arrow"]
	arrow_mode.mouse_press(PySide6.QtCore.QPointF(10.0, 10.0), None)
	arrow_mode.mouse_move(PySide6.QtCore.QPointF(35.0, 10.0), None)
	preview = arrow_mode._preview_line
	assert preview is not None

	session.document.mark_clean()
	main_window._on_new()
	assert main_window._remove_session(session)
	assert bkchem_qt.main_window.drain_pending_session_deletions(qapp, main_window)

	assert not main_window._pending_session_deletions
	assert not any(
		shiboken6.isValid(wrapper)
		for wrapper in (atom_item, mark_item, undo_item, preview, session)
	)


#============================================
def test_failed_detached_graphics_retirement_stays_with_the_session_reaper(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The reaper owns a failed detached root until its controlled resolution."""
	assert main_window._on_new()
	session = main_window._active_session
	undo_item = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 8.0, 8.0)
	session.scene.addItem(undo_item)
	session.scene.removeItem(undo_item)
	session.document.undo_stack.push(_UndoRetainedGraphicsCommand(undo_item))
	real_delete = shiboken6.delete

	def fail_only_the_detached_root(item: object) -> None:
		"""Make the explicit retirement boundary report one controlled failure."""
		if item is undo_item:
			raise RuntimeError("controlled detached graphics retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete", fail_only_the_detached_root,
	)
	session.document.mark_clean()
	with pytest.raises(RuntimeError, match="queued after a disposal failure"):
		main_window._remove_session(session)
	pending = next(iter(main_window._pending_session_deletions.values()))
	retained = pending.retained_detached_graphics

	assert shiboken6.isValid(undo_item)
	assert undo_item in retained.roots and retained.diagnostics

	monkeypatch.undo()
	assert bkchem_qt.main_window.drain_pending_session_deletions(qapp, main_window)
	assert not shiboken6.isValid(undo_item)
