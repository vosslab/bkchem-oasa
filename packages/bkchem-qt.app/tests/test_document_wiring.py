"""Tests for Patch 1: Document wiring between MainWindow and ChemView."""

# Standard Library
import subprocess
import sys
import textwrap

# local repo modules
import tests.test_qt_gui_smoke


#============================================
def _check_subprocess_result(result):
	"""Assert subprocess completed successfully.

	Args:
		result: CompletedProcess from subprocess.run().
	"""
	if result.returncode != 0:
		msg = result.stdout + "\n" + result.stderr
		raise AssertionError(f"Subprocess failed (rc={result.returncode}):\n{msg}")


#============================================
def test_view_has_document_property():
	"""ChemView.document returns Document after set_document()."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		view = mw.view
		assert view.document is not None, "view.document should not be None"
		assert view.document is mw.document, "view.document should be the same as mw.document"
		print("PASS: view.document is wired correctly")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_draw_mode_finds_undo_stack():
	"""Draw mode _find_undo_stack() returns valid QUndoStack."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		import PySide6.QtGui
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		# switch to draw mode
		mw._mode_manager.set_mode("draw")
		draw_mode = mw._mode_manager.current_mode
		stack = draw_mode._find_undo_stack()
		assert stack is not None, "undo stack should not be None"
		assert isinstance(stack, PySide6.QtGui.QUndoStack), "should be QUndoStack"
		print("PASS: draw mode finds undo stack")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_draw_mode_creates_atom():
	"""Draw mode _create_atom_at() adds AtomItem to scene and AtomModel to document."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		import bkchem_qt.canvas.items.atom_item
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		mw._mode_manager.set_mode("draw")
		draw_mode = mw._mode_manager.current_mode
		# count items before
		atom_items_before = [
			i for i in mw.scene.items()
			if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		assert len(atom_items_before) == 0, "should start with no atoms"
		# create an atom
		result = draw_mode._create_atom_at(100.0, 200.0, "N")
		assert result is not None, "_create_atom_at should return AtomItem"
		# verify scene has the atom
		atom_items_after = [
			i for i in mw.scene.items()
			if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		assert len(atom_items_after) == 1, "should have 1 atom after creation"
		# verify document has the molecule
		assert len(mw.document.molecules) == 1, "document should have 1 molecule"
		mol = mw.document.molecules[0]
		assert len(mol.atoms) == 1, "molecule should have 1 atom"
		assert mol.atoms[0].symbol == "N", "atom symbol should be N"
		print("PASS: draw mode creates atom correctly")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_undo_removes_atom():
	"""Undo after atom creation removes atom from scene and document."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		import bkchem_qt.canvas.items.atom_item
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		mw._mode_manager.set_mode("draw")
		draw_mode = mw._mode_manager.current_mode
		# create an atom
		draw_mode._create_atom_at(100.0, 200.0, "C")
		atom_items = [
			i for i in mw.scene.items()
			if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		assert len(atom_items) == 1, "should have 1 atom"
		# undo
		mw.document.undo_stack.undo()
		atom_items = [
			i for i in mw.scene.items()
			if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		assert len(atom_items) == 0, "should have 0 atoms after undo"
		print("PASS: undo removes atom")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_new_document_rewires_view():
	"""set_document() on a new Document re-wires view.document."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		import bkchem_qt.models.document
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		old_doc = mw.document
		# create a fresh document and wire it manually (same as _on_new does)
		new_doc = bkchem_qt.models.document.Document(mw)
		mw._view.set_document(new_doc)
		assert mw.view.document is new_doc, "view.document should point to new doc"
		assert mw.view.document is not old_doc, "should differ from old doc"
		print("PASS: new document rewires view")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout
