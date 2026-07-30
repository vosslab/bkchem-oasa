"""Focused projection-order coverage for document presentation objects."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import tests.graphics_test_retirement


#============================================
def _item_for_model(
		scene: PySide6.QtWidgets.QGraphicsScene, model: object,
		) -> PySide6.QtWidgets.QGraphicsItem:
	"""Return the one scene graphics item with the requested model identity."""
	for item in scene.items():
		if getattr(item, "document_object_model", None) is model:
			return item
	raise AssertionError("Expected graphics item was not projected")


#============================================
def test_document_object_stack_projects_reordered_presentation_z_values(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Reordering presentation models changes their projected drawing order."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	arrow = bkchem_qt.models.document_object.PresentationObject(
		"arrow", attributes={"id": "arrow-1"},
		points=[(20.0, 20.0, None), (70.0, 20.0, None)],
	)
	text = bkchem_qt.models.document_object.PresentationObject(
		"text", attributes={"id": "text-1"}, points=[(90.0, 20.0, None)],
	)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		document.add_presentation_object(arrow, mark_dirty=False)
		document.add_presentation_object(text, mark_dirty=False)
		bkchem_qt.canvas.document_projection.project_document_presentation(document, scene)
		arrow_item = _item_for_model(scene, arrow)
		text_item = _item_for_model(scene, text)
		document.replace_object_order([text, arrow], mark_dirty=False)
		assert text_item.zValue() < arrow_item.zValue()
