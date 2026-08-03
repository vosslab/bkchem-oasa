"""Explicit terminal ownership for test-created document scenes.

The context manager keeps standalone test scenes on the same explicit Qt
retirement path as temporary export projections.  It intentionally accepts
only objects a test already owns: a QApplication, Document, and bare scene.
"""

# Standard Library
import contextlib

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.main_window
import bkchem_qt.models.document


#============================================
@contextlib.contextmanager
def bare_document_scene_retirement(
		app: PySide6.QtWidgets.QApplication,
		document: bkchem_qt.models.document.Document,
		scene: PySide6.QtWidgets.QGraphicsScene,
		) -> object:
	"""Retire one test-owned Document and standalone scene after its body.

	The document first disconnects its model and undo bindings while the scene
	is still live.  Item identities captured before that transition distinguish
	detached document graphics from roots that remain scene-owned.  The existing
	temporary-scene reaper then owns both lists through native deletion.
	"""
	body_error = None
	try:
		yield
	except BaseException as exc:
		body_error = exc
		raise
	finally:
		cleanup_error = _retire_document_scene(app, document, scene)
		if cleanup_error is not None:
			if body_error is None:
				raise cleanup_error from cleanup_error.__cause__
			body_error.add_note(f"Standalone scene cleanup also failed: {cleanup_error}")


#============================================
def retire_terminal_top_level_widgets(
		app: PySide6.QtWidgets.QApplication,
		widgets: tuple[PySide6.QtWidgets.QWidget, ...] | None = None,
		) -> None:
	"""Retire test-process top-level widgets while honoring native validity.

	Qt can retain a Python wrapper in its top-level enumeration after the native
	object was retired during a session's controlled reaper drain.  The wrapper
	is absent at this terminal boundary, so it receives no further Qt call.
	"""
	targets = tuple(app.topLevelWidgets()) if widgets is None else widgets
	for widget in targets:
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(widget):
			continue
		widget.close()
		if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(widget):
			continue
		if isinstance(widget, bkchem_qt.main_window.MainWindow):
			if not bkchem_qt.main_window.drain_pending_session_deletions(app, widget):
				raise RuntimeError("MainWindow session reaper did not drain")
		if bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(widget):
			if not bkchem_qt.main_window.delete_qobject_and_wait(app, widget):
				raise RuntimeError("Top-level QObject deletion was not delivered")


#============================================
def _retire_document_scene(
		app: PySide6.QtWidgets.QApplication,
		document: bkchem_qt.models.document.Document,
		scene: PySide6.QtWidgets.QGraphicsScene,
		) -> RuntimeError | None:
	"""Complete the bounded cleanup sequence and return its first diagnostic."""
	try:
		scene.clearSelection()
		initial_items = list(scene.items())
		document.clear()
		document.set_scene(None)
		remaining_scene_items = list(scene.items())
		remaining_ids = {id(item) for item in remaining_scene_items}
		detached_items = [item for item in initial_items if id(item) not in remaining_ids]
		reaper = bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper
		record = reaper.retire(scene, remaining_scene_items, detached_items)
		reaper.drain()
		app.processEvents()
		reaper.drain()
		if not record.resolved:
			return RuntimeError("Standalone scene retirement left an unresolved record")
		if record.diagnostics:
			cleanup_error = RuntimeError("Standalone scene retirement reported a diagnostic")
			cleanup_error.__cause__ = record.diagnostics[0]
			return cleanup_error
		if not bkchem_qt.main_window.delete_qobject_and_wait(app, document):
			return RuntimeError("Standalone Document QObject deletion was not delivered")
	except RuntimeError as exc:
		cleanup_error = RuntimeError("Standalone scene cleanup failed")
		cleanup_error.__cause__ = exc
		return cleanup_error
	return None
