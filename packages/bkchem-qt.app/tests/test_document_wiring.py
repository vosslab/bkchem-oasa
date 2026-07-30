"""Tests for Patch 1: Document wiring between MainWindow and ChemView."""

# PIP3 modules
import PySide6.QtGui

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.models.document


#============================================
def test_view_has_document_property(main_window: object) -> None:
	"""ChemView.document returns Document after set_document()."""
	view = main_window.view
	assert view.document is not None, "view.document should not be None"
	assert view.document is main_window.document, (
		"view.document should be the same as mw.document"
	)


#============================================
def test_draw_mode_finds_undo_stack(main_window: object) -> None:
	"""Draw mode resolves undo stack via ModeEnvironment."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	stack = draw_mode._env.undo_stack
	assert stack is not None, "undo stack should not be None"
	assert isinstance(stack, PySide6.QtGui.QUndoStack), "should be QUndoStack"


#============================================
def test_draw_mode_creates_atom(main_window: object) -> None:
	"""Draw mode _create_atom_at() adds AtomItem to scene and AtomModel to document."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	# count items before
	atom_items_before = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(atom_items_before) == 0, "should start with no atoms"
	# create an atom
	result = draw_mode._create_atom_at(100.0, 200.0, "N")
	assert result is not None, "_create_atom_at should return AtomItem"
	# verify scene has the atom
	atom_items_after = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(atom_items_after) == 1, "should have 1 atom after creation"
	# verify document has the molecule
	assert len(main_window.document.molecules) == 1, (
		"document should have 1 molecule"
	)
	mol = main_window.document.molecules[0]
	assert len(mol.atoms) == 1, "molecule should have 1 atom"
	assert mol.atoms[0].symbol == "N", "atom symbol should be N"


#============================================
def test_undo_removes_atom(main_window: object) -> None:
	"""Undo after atom creation removes atom from scene and document."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	# create an atom
	draw_mode._create_atom_at(100.0, 200.0, "C")
	atom_items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(atom_items) == 1, "should have 1 atom"
	# undo
	main_window.document.undo_stack.undo()
	atom_items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(atom_items) == 0, "should have 0 atoms after undo"


#============================================
def test_new_document_rewires_view(main_window: object) -> None:
	"""set_document() on a new Document re-wires view.document."""
	old_doc = main_window.document
	# create a fresh document and wire it
	new_doc = bkchem_qt.models.document.Document(main_window)
	main_window._view.set_document(new_doc)
	assert main_window.view.document is new_doc, (
		"view.document should point to new doc"
	)
	assert main_window.view.document is not old_doc, (
		"should differ from old doc"
	)
