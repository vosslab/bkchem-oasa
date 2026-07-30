"""Regression coverage for standalone document-scene test cleanup."""

# PIP3 modules
import PySide6.QtWidgets
import pytest
import shiboken6

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import tests.graphics_test_retirement


#============================================
def test_bare_document_scene_retirement_retires_detached_and_scene_owned_roots(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""One terminal helper owns both document and unrelated standalone roots."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	presentation = bkchem_qt.models.document_object.PresentationObject(
		"text", attributes={"id": "retirement-text"}, points=[(20.0, 20.0, None)],
	)
	document_item = None
	foreign_root = None
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		document.add_presentation_object(presentation, mark_dirty=False)
		bkchem_qt.canvas.document_projection.project_document_presentation(document, scene)
		document_item = next(iter(scene.items()))
		foreign_root = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 5.0, 5.0)
		PySide6.QtWidgets.QGraphicsRectItem(1.0, 1.0, 2.0, 2.0, foreign_root)
		scene.addItem(foreign_root)
	assert not shiboken6.isValid(document_item) and not shiboken6.isValid(foreign_root)


#============================================
def test_bare_scene_cleanup_error_chains_first_retirement_diagnostic(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A resolved retry still reports its original native-retirement diagnostic."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	presentation = bkchem_qt.models.document_object.PresentationObject(
		"text", attributes={"id": "retirement-failure-text"}, points=[(20.0, 20.0, None)],
	)
	document_item = None
	original_delete = shiboken6.delete
	failed_once = False

	#============================================
	def fail_first_document_root_delete(item: object) -> None:
		"""Inject one detached-root failure before the production reaper retries."""
		nonlocal failed_once
		if item is document_item and not failed_once:
			failed_once = True
			raise RuntimeError("injected standalone root retirement failure")
		original_delete(item)

	monkeypatch.setattr(shiboken6, "delete", fail_first_document_root_delete)
	with pytest.raises(RuntimeError, match="Standalone scene cleanup") as failure:
		with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
			document.add_presentation_object(presentation, mark_dirty=False)
			bkchem_qt.canvas.document_projection.project_document_presentation(document, scene)
			document_item = next(iter(scene.items()))
	diagnostic = failure.value
	while diagnostic.__cause__ is not None:
		diagnostic = diagnostic.__cause__
	assert "injected standalone root retirement failure" in str(diagnostic)


#============================================
def test_bare_scene_cleanup_failure_keeps_body_exception_primary(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A body failure receives cleanup context without losing its own traceback."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	presentation = bkchem_qt.models.document_object.PresentationObject(
		"text", attributes={"id": "retirement-body-error-text"}, points=[(20.0, 20.0, None)],
	)
	document_item = None
	original_delete = shiboken6.delete
	failed_once = False

	#============================================
	def fail_first_document_root_delete(item: object) -> None:
		"""Inject one detached-root failure before the production reaper retries."""
		nonlocal failed_once
		if item is document_item and not failed_once:
			failed_once = True
			raise RuntimeError("injected standalone root retirement failure")
		original_delete(item)

	monkeypatch.setattr(shiboken6, "delete", fail_first_document_root_delete)
	with pytest.raises(AssertionError, match="body failure") as failure:
		with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
			document.add_presentation_object(presentation, mark_dirty=False)
			bkchem_qt.canvas.document_projection.project_document_presentation(document, scene)
			document_item = next(iter(scene.items()))
			raise AssertionError("body failure")
	assert any("Standalone scene cleanup also failed" in note for note in failure.value.__notes__)


#============================================
def test_terminal_detached_failure_stays_reaper_owned_until_retry(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed terminal delete has one explicit reaper owner before retry."""
	root = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 5.0, 5.0)
	child = PySide6.QtWidgets.QGraphicsRectItem(1.0, 1.0, 2.0, 2.0, root)
	reaper = bkchem_qt.canvas.graphics_retirement.detached_graphics_retirement_reaper
	real_delete = shiboken6.delete

	#============================================
	def fail_root_delete(item: object) -> None:
		"""Leave only the root for the controlled reaper retry."""
		if item is root:
			raise RuntimeError("injected terminal detached deletion failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete", fail_root_delete,
	)
	coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
	coordinator.retire_detached_projection_items([root])

	assert (
		shiboken6.isValid(root)
		and not shiboken6.isValid(child)
		and reaper.owns_detached_root(root)
	)

	monkeypatch.undo()
	reaper.drain()
	assert not shiboken6.isValid(root) and not reaper.owns_detached_root(root)


#============================================
def test_invalid_known_scene_retires_detached_projection_root(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A stale scene wrapper never receives a removal call during retirement."""
	scene = PySide6.QtWidgets.QGraphicsScene()
	root = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 5.0, 5.0)
	child = PySide6.QtWidgets.QGraphicsRectItem(1.0, 1.0, 2.0, 2.0, root)
	scene.addItem(root)
	scene.removeItem(root)
	shiboken6.delete(scene)

	coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
	coordinator.retire_scene_projection_items(scene, [root])

	assert not shiboken6.isValid(root) and not shiboken6.isValid(child)


#============================================
def test_scene_removal_failure_transfers_roots_to_reaper_before_retry(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed scene removal retains the complete tree until controlled recovery."""
	scene = PySide6.QtWidgets.QGraphicsScene()
	root = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 5.0, 5.0)
	child = PySide6.QtWidgets.QGraphicsRectItem(1.0, 1.0, 2.0, 2.0, root)
	scene.addItem(root)
	reaper = bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper()
	coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()

	#============================================
	def fail_scene_removal(
			unused_scene: PySide6.QtWidgets.QGraphicsScene,
			unused_root: PySide6.QtWidgets.QGraphicsItem,
			) -> None:
		"""Keep the known tree scene-owned until the reaper retries it."""
		raise RuntimeError("injected scene removal failure")

	monkeypatch.setattr(coordinator, "_remove_scene_root", fail_scene_removal)
	coordinator.retire_scene_projection_items(scene, [root], reaper=reaper)

	assert (
		shiboken6.isValid(root)
		and shiboken6.isValid(child)
		and reaper.owns_scene_projection_root(root)
	)

	monkeypatch.undo()
	reaper.drain()
	assert not shiboken6.isValid(root) and not reaper.owns_scene_projection_root(root)
