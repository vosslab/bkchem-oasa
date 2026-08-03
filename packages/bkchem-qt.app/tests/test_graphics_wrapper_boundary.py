"""Public lifetime behavior for invalid disposable graphics wrappers."""

# PIP3 modules
import PySide6.QtWidgets
import shiboken6

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.undo.commands
import tests.graphics_test_retirement


#============================================
def test_invalid_graphics_wrappers_have_no_durable_target(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Selection and model traversal treat retired wrappers as absent."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	item = PySide6.QtWidgets.QGraphicsItemGroup()
	handle = PySide6.QtWidgets.QGraphicsRectItem(0.0, 0.0, 2.0, 2.0, item)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		scene.addItem(item)
		document.register_current_projection_items((item, handle))
		coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
		coordinator.retire_scene_projection_items(scene, [item])
		assert bkchem_qt.canvas.document_projection.persistent_selection_key(item) is None
		assert document.molecule_for_current_projection_item(handle) is None


#============================================
def test_retired_scene_has_no_selection_before_document_detaches_it(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A stale captured scene becomes an empty selection surface."""
	del qapp
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	shiboken6.delete(scene)
	try:
		assert not document.has_selection and not document.selected_atoms
	finally:
		document.set_scene(None)


#============================================
def test_stale_presentation_undo_does_not_mutate_replacement_scene(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A command retained from an old projection becomes inert after replacement."""
	document = bkchem_qt.models.document.Document()
	old_scene = PySide6.QtWidgets.QGraphicsScene()
	replacement_scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(old_scene)
	model = bkchem_qt.models.document_object.PresentationObject(
		"polyline", attributes={"id": "retired"}, points=[(0.0, 0.0, None)],
	)
	item = bkchem_qt.canvas.document_projection.create_presentation_item(model)
	assert item is not None
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, old_scene):
		document.add_presentation_object(model, mark_dirty=False)
		old_scene.addItem(item)
		command = bkchem_qt.undo.commands.RemovePresentationObjectCommand(
			document, old_scene, model, item,
		)
		command.redo()
		document.set_scene(replacement_scene)
		command.undo()
		assert model not in document.objects and not replacement_scene.items()
		document.set_scene(old_scene)
		bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.retire(
			replacement_scene, [], [],
		)
		bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()
