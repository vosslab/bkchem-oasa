"""Mixed molecule/artwork Object and Align transform behavior."""

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.actions.align_actions
import bkchem_qt.actions.file_actions
import bkchem_qt.actions.object_actions
import bkchem_qt.models.atom_model
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.models.molecule_model
import bkchem_qt.undo.commands
import tests.graphics_test_retirement


#============================================
class _ActionApp:
	"""Provide the small app boundary used by transform action handlers."""

	#============================================
	def __init__(self, document: bkchem_qt.models.document.Document) -> None:
		"""Bind the active document."""
		self.document = document

	#============================================
	def statusBar(self) -> "_ActionApp":
		"""Return the action-facing status target."""
		return self

	#============================================
	def showMessage(self, message: str, timeout: int) -> None:
		"""Accept action feedback without coupling behavior to wording."""
		del message, timeout


#============================================
def _selected_mixed_document() -> tuple[
		bkchem_qt.models.document.Document,
		PySide6.QtWidgets.QGraphicsScene,
		bkchem_qt.models.atom_model.AtomModel,
		bkchem_qt.models.atom_model.AtomModel,
		bkchem_qt.models.document_object.PresentationObject,
		]:
	"""Create one selected molecule and selected polyline in a live scene."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	first_atom = bkchem_qt.models.atom_model.AtomModel()
	second_atom = bkchem_qt.models.atom_model.AtomModel()
	second_atom.x = 20.0
	molecule.add_atom(first_atom)
	molecule.add_atom(second_atom)
	polyline = bkchem_qt.models.document_object.PresentationObject(
		"polyline", points=[(40.0, 10.0, None), (60.0, 20.0, None)],
		bounds=(40.0, 10.0, 20.0, 10.0),
	)
	document.add_molecule(molecule, mark_dirty=False)
	document.add_presentation_object(polyline, mark_dirty=False)
	bkchem_qt.actions.file_actions._project_molecules_to_scene(
		scene, document.molecules,
	)
	bkchem_qt.canvas.document_projection.project_document_presentation(
		document, scene,
	)
	for item in scene.items():
		if getattr(item, "atom_model", None) is first_atom or (
				getattr(item, "document_object_model", None) is polyline
				):
			item.setSelected(True)
	return document, scene, first_atom, second_atom, polyline


#============================================
def test_align_moves_full_molecule_and_artwork_then_undoes(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Top alignment moves the artwork and restores its full model geometry."""
	document, scene, first_atom, second_atom, polyline = _selected_mixed_document()
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		bkchem_qt.actions.align_actions._align_selection(_ActionApp(document), "top")
		assert (
			first_atom.y, second_atom.y, polyline.points, polyline.bounds,
		) == (
			0.0, 0.0, [(40.0, 0.0, None), (60.0, 10.0, None)],
			(40.0, 0.0, 20.0, 10.0),
		)
		document.undo_stack.undo()
		assert (
			first_atom.y, second_atom.y, polyline.points, polyline.bounds,
		) == (
			0.0, 0.0, [(40.0, 10.0, None), (60.0, 20.0, None)],
			(40.0, 10.0, 20.0, 10.0),
		)


#============================================
def test_vertical_mirror_transforms_mixed_model_geometry(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Vertical mirror uses aggregate persistent bounds for all top levels."""
	document, scene, first_atom, second_atom, polyline = _selected_mixed_document()
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		bkchem_qt.actions.object_actions.handle_vertical_mirror(_ActionApp(document))
		assert (
			first_atom.x, second_atom.x, polyline.points, polyline.bounds
			) == (
				60.0, 40.0, [(20.0, 10.0, None), (0.0, 20.0, None)],
				(0.0, 10.0, 20.0, 10.0),
			)


#============================================
def test_scale_uses_mixed_selection_bounds_as_its_pivot(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Scale applies the dialog's factors about aggregate model bounds."""
	document, scene, first_atom, second_atom, polyline = _selected_mixed_document()
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		import bkchem_qt.dialogs.scale_dialog
		monkeypatch.setattr(
			bkchem_qt.dialogs.scale_dialog.ScaleDialog, "get_scale_factors",
			lambda parent: (0.5, 2.0),
		)
		bkchem_qt.actions.object_actions.handle_scale(_ActionApp(document))
		assert (
			first_atom.x, second_atom.x, polyline.points, polyline.bounds
			) == (
				15.0, 25.0, [(35.0, 10.0, None), (45.0, 30.0, None)],
				(35.0, 10.0, 10.0, 20.0),
			)


#============================================
def test_discrete_mirrors_do_not_merge_on_undo_stack(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Two Object actions remain two independently undoable user edits."""
	document, scene, first_atom, second_atom, polyline = _selected_mixed_document()
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		app = _ActionApp(document)
		bkchem_qt.actions.object_actions.handle_vertical_mirror(app)
		after_vertical = (
			first_atom.x, first_atom.y, second_atom.x, second_atom.y,
			polyline.points, polyline.bounds,
		)
		bkchem_qt.actions.object_actions.handle_horizontal_mirror(app)
		document.undo_stack.undo()
		assert (
			first_atom.x, first_atom.y, second_atom.x, second_atom.y,
			polyline.points, polyline.bounds,
		) == after_vertical
