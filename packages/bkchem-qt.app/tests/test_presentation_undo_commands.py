"""One reversible persistent-presentation command."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.undo.commands
import tests.graphics_test_retirement


#============================================
def test_remove_presentation_undo_restores_retained_item_identity(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Undo reuses the removed projection at its original document position."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	first = bkchem_qt.models.document_object.PresentationObject(
		"polyline", attributes={"id": "first"},
		points=[(10.0, 20.0, None), (40.0, 50.0, None)],
	)
	removed = bkchem_qt.models.document_object.PresentationObject(
		"polyline", attributes={"id": "removed"},
		points=[(20.0, 30.0, None), (50.0, 60.0, None)],
	)
	last = bkchem_qt.models.document_object.PresentationObject(
		"polyline", attributes={"id": "last"},
		points=[(30.0, 40.0, None), (60.0, 70.0, None)],
	)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		for object_model in (first, removed, last):
			document.add_presentation_object(object_model, mark_dirty=False)
		removed_item = bkchem_qt.canvas.document_projection.create_presentation_item(
			removed,
		)
		assert removed_item is not None
		scene.addItem(removed_item)
		document.undo_stack.push(
			bkchem_qt.undo.commands.RemovePresentationObjectCommand(
				document, scene, removed, removed_item,
			),
		)
		document.undo_stack.undo()
		assert document.object_index(removed) == 1 and removed_item.scene() is scene
