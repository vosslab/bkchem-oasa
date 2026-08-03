"""Focused non-mutating artifact export coverage."""

# Standard Library
import contextlib

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets
import pytest
import shiboken6

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.scene
import bkchem_qt.io.export
import bkchem_qt.io.render_plan
import bkchem_qt.main_window
import bkchem_qt.models.document_object
import bkchem_qt.models.molecule_model


@contextlib.contextmanager
#============================================
def _content_scene(qapp: object) -> object:
	"""Yield a standalone scene and dispose it before its wrapper is released."""
	scene = bkchem_qt.canvas.scene.ChemScene()
	_add_content_presentation(scene)
	try:
		yield scene
	finally:
		_dispose_content_callbacks(scene)
		scene.dispose_contents()
		assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, scene)


#============================================
def _add_content_presentation(scene: PySide6.QtWidgets.QGraphicsScene) -> None:
	"""Add the fixture presentation without retaining its wrapper across yield."""
	model = bkchem_qt.models.document_object.PresentationObject(
		"text", points=[(40.0, 60.0, None)], xml_ftext="Export proof",
	)
	item = bkchem_qt.canvas.document_projection.create_presentation_item(model)
	assert item is not None
	scene.addItem(item)


#============================================
def _dispose_content_callbacks(scene: bkchem_qt.canvas.scene.ChemScene) -> None:
	"""Release content bindings without disturbing ChemScene decorations."""
	paper = scene._paper_item
	grid_overlay = scene._grid_overlay
	for item in list(scene.items()):
		if item is paper or item is grid_overlay:
			continue
		bkchem_qt.canvas.document_projection.dispose_item_callbacks(item)
#============================================
def test_svg_crop_plan_uses_content_without_paper_or_grid(qapp: object) -> None:
	"""Modeled SVG cropping chooses content bounds rather than the paper page."""
	with _content_scene(qapp) as scene:
		scene._paper_attributes = {"crop_svg": "1", "crop_margin": "7"}
		plan = bkchem_qt.io.render_plan.build_render_plan(scene, "svg")
		assert (
			plan.crop_to_content and not plan.include_decorations
			and plan.source_rect.width() < scene.paper_rect.width()
		)


#============================================
def test_png_and_pdf_plans_keep_the_paper_page(qapp: object) -> None:
	"""Non-SVG artifacts retain paper dimensions despite SVG crop metadata."""
	with _content_scene(qapp) as scene:
		scene._paper_attributes = {"crop_svg": "1", "crop_margin": "7"}
		png_plan = bkchem_qt.io.render_plan.build_render_plan(scene, "png")
		pdf_plan = bkchem_qt.io.render_plan.build_render_plan(scene, "pdf")
		assert (
			png_plan.source_rect == scene.paper_rect
			and pdf_plan.source_rect == scene.paper_rect
		)


#============================================
def test_svg_export_writes_an_svg_artifact(qapp: object, tmp_path: object) -> None:
	"""SVG export writes a nonempty SVG document to the requested path."""
	path = tmp_path / "drawing.svg"

	with _content_scene(qapp) as scene:
		bkchem_qt.io.export.export_svg(scene, str(path))

	assert path.read_bytes().startswith(b"<?xml")


#============================================
def test_png_export_writes_a_png_artifact(qapp: object, tmp_path: object) -> None:
	"""PNG export writes a nonempty PNG document to the requested path."""
	path = tmp_path / "drawing.png"

	with _content_scene(qapp) as scene:
		bkchem_qt.io.export.export_png(scene, str(path))

	assert path.read_bytes().startswith(b"\x89PNG")


#============================================
def test_pdf_export_writes_a_pdf_artifact(qapp: object, tmp_path: object) -> None:
	"""PDF export writes a nonempty PDF document to the requested path."""
	path = tmp_path / "drawing.pdf"

	with _content_scene(qapp) as scene:
		bkchem_qt.io.export.export_pdf(scene, str(path))

	assert path.read_bytes().startswith(b"%PDF")


#============================================
def test_selection_projection_carries_an_atom_attached_mark(qapp: object) -> None:
	"""Molecule selection carries its supported atom mark into the export scene."""
	with _content_scene(qapp) as scene:
		molecule = bkchem_qt.models.molecule_model.MoleculeModel()
		atom = molecule.create_atom("O")
		atom.set_xyz(45.0, 55.0)
		molecule.add_atom(atom)
		atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom)
		atom_item.molecule_model = molecule
		scene.addItem(atom_item)
		mark_model = bkchem_qt.models.document_object.AtomMarkModel(
			atom, {"type": "plus"},
		)
		bkchem_qt.canvas.document_projection.create_mark_item(mark_model, atom_item)
		atom_item.setSelected(True)
		projection = bkchem_qt.io.render_plan.project_supported_items(
			scene, scene.selectedItems(),
		)
		has_atom = any(getattr(item, "atom_model", None) is atom for item in projection.scene.items())
		has_mark = any(
			getattr(item, "atom_mark_model", None) is mark_model
			for item in projection.scene.items()
		)
		projection.dispose()
		assert has_atom and has_mark


#============================================
def test_export_projection_disposal_retires_its_temporary_scene(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Export disposal retains the temporary scene through deferred Qt deletion."""
	with _content_scene(qapp) as scene:
		projection = bkchem_qt.io.render_plan.project_supported_items(scene)
		temporary_scene = projection.scene
		projection.dispose()
		bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()
	assert temporary_scene is not None and not shiboken6.isValid(temporary_scene)


#============================================
def test_export_projection_uses_one_child_first_terminal_owner(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Tracked export graphics retire explicitly without a second scene clear."""
	with _content_scene(qapp) as scene:
		molecule = bkchem_qt.models.molecule_model.MoleculeModel()
		atom = molecule.create_atom("O")
		atom.set_xyz(45.0, 55.0)
		molecule.add_atom(atom)
		atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom)
		atom_item.molecule_model = molecule
		scene.addItem(atom_item)
		mark_model = bkchem_qt.models.document_object.AtomMarkModel(
			atom, {"type": "plus"},
		)
		bkchem_qt.canvas.document_projection.create_mark_item(mark_model, atom_item)
		atom_item.setSelected(True)

		original_scene = PySide6.QtWidgets.QGraphicsScene
		class ClearRejectingTemporaryScene(original_scene):
			"""Make a second temporary-scene content owner observable."""

			#============================================
			def clear(self) -> None:
				"""Reject scene-content retirement after explicit root deletion."""
				raise AssertionError("temporary export scene must not clear tracked roots")

		monkeypatch.setattr(
			bkchem_qt.io.render_plan.PySide6.QtWidgets,
			"QGraphicsScene", ClearRejectingTemporaryScene,
		)
		projection = bkchem_qt.io.render_plan.project_supported_items(
			scene, scene.selectedItems(),
		)
		projected_atom = next(
			item for item in projection.items
			if getattr(item, "atom_model", None) is atom
		)
		projected_mark = next(
			item for item in projection.items
			if getattr(item, "atom_mark_model", None) is mark_model
		)
		delete_order = []
		original_delete = shiboken6.delete

		#============================================
		def record_graphics_delete(item: object) -> None:
			"""Record the explicit graphics boundary before retaining normal behavior."""
			if item is projected_mark or item is projected_atom:
				delete_order.append(item)
			original_delete(item)

		monkeypatch.setattr(shiboken6, "delete", record_graphics_delete)
		projection.dispose()
		bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()
		assert (
			delete_order.index(projected_mark) < delete_order.index(projected_atom)
			and not shiboken6.isValid(projected_mark)
			and not shiboken6.isValid(projected_atom)
		)


#============================================
def test_failed_export_projection_retires_earlier_atom_callbacks(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A later adoption failure retains and releases a populated scene root."""
	with _content_scene(qapp) as scene:
		first_molecule = bkchem_qt.models.molecule_model.MoleculeModel()
		first_atom = first_molecule.create_atom("C")
		first_molecule.add_atom(first_atom)
		second_molecule = bkchem_qt.models.molecule_model.MoleculeModel()
		second_atom = second_molecule.create_atom("O")
		second_molecule.add_atom(second_atom)
		source_items = []
		for molecule, atom in ((first_molecule, first_atom), (second_molecule, second_atom)):
			source_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom)
			source_item.molecule_model = molecule
			scene.addItem(source_item)
			source_items.append(source_item)
		callback_calls = []
		created_items = []
		original_atom_item = bkchem_qt.canvas.items.atom_item.AtomItem

		class RecordingAtomItem(original_atom_item):
			"""Record whether the temporary item's model callback remains live."""

			#============================================
			def _on_property_changed(self, property_name: str, value: object) -> None:
				"""Record a delivery before preserving the normal refresh behavior."""
				callback_calls.append((property_name, value))
				super()._on_property_changed(property_name, value)

		#============================================
		def construct_or_fail(atom: object) -> PySide6.QtWidgets.QGraphicsItem:
			"""Construct a temporary atom whose owner can report its native state."""
			item = RecordingAtomItem(atom)
			created_items.append(item)
			return item

		original_scene = PySide6.QtWidgets.QGraphicsScene
		class FailingTemporaryScene(original_scene):
			"""Fail the second adoption after one temporary root becomes scene-owned."""

			adoption_count = 0

			#============================================
			def addItem(self, item: PySide6.QtWidgets.QGraphicsItem) -> None:
				"""Keep the second root detached while preserving the first scene root."""
				if isinstance(item, RecordingAtomItem):
					type(self).adoption_count += 1
					if type(self).adoption_count == 2:
						raise RuntimeError("temporary scene adoption failed")
				super().addItem(item)

		monkeypatch.setattr(
			bkchem_qt.canvas.items.atom_item, "AtomItem", construct_or_fail,
		)
		monkeypatch.setattr(
			bkchem_qt.io.render_plan.PySide6.QtWidgets,
			"QGraphicsScene", FailingTemporaryScene,
		)
		original_delete = shiboken6.delete

		#============================================
		def fail_detached_root(item: object) -> None:
			"""Keep the adopted temporary root in the production reaper once."""
			if item is created_items[0]:
				raise RuntimeError("injected detached export root failure")
			original_delete(item)

		monkeypatch.setattr(shiboken6, "delete", fail_detached_root)
		with pytest.raises(RuntimeError, match="temporary scene adoption failed") as failure:
			bkchem_qt.io.render_plan.project_supported_items(scene, source_items)
		created_items[0].atom_model.symbol = "N"
		assert (
			callback_calls == []
			and bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper
			.owns_detached_root(created_items[0])
			and any("retirement remains owned" in note for note in failure.value.__notes__)
		)
		monkeypatch.setattr(shiboken6, "delete", original_delete)
		bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()
		assert not shiboken6.isValid(created_items[0])
