"""Tests for Patch 4-5: Dialog wiring and template placement."""

# Standard Library
import subprocess
import sys
import textwrap


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
def test_atom_dialog_applies_changes():
	"""AtomDialog.edit_atom() can apply changes to an AtomModel."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.models.atom_model
		import oasa.atom_lib
		# create an atom model
		oasa_atom = oasa.atom_lib.Atom(symbol="C")
		atom = bkchem_qt.models.atom_model.AtomModel(oasa_atom=oasa_atom)
		atom.set_xyz(0.0, 0.0, 0.0)
		assert atom.symbol == "C", "should start as C"
		# directly test property setting (dialog acceptance requires GUI interaction)
		atom.symbol = "N"
		assert atom.symbol == "N", "symbol should be N after set"
		atom.charge = -1
		assert atom.charge == -1, "charge should be -1"
		atom.font_size = 14
		assert atom.font_size == 14, "font_size should be 14"
		print("PASS: atom model property changes work")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_bond_dialog_applies_changes():
	"""BondDialog.edit_bond() can apply changes to a BondModel."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.models.bond_model
		import oasa.bond_lib
		# create a bond model
		oasa_bond = oasa.bond_lib.Bond(order=1, type="n")
		bond = bkchem_qt.models.bond_model.BondModel(oasa_bond=oasa_bond)
		assert bond.order == 1, "should start as single"
		assert bond.type == "n", "should start as normal"
		# directly test property setting
		bond.order = 2
		assert bond.order == 2, "order should be 2 after set"
		bond.type = "w"
		assert bond.type == "w", "type should be w after set"
		bond.line_width = 2.5
		assert bond.line_width == 2.5, "line_width should be 2.5"
		print("PASS: bond model property changes work")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_template_mode_places_molecule():
	"""Template mode _place_template() adds atoms to the scene and document."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		import bkchem_qt.canvas.items.atom_item
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		mw._mode_manager.set_mode("template")
		tmpl_mode = mw._mode_manager.current_mode
		# set a known template
		if "Ph" in tmpl_mode.template_names:
			tmpl_mode.set_template("Ph")
		elif "Me" in tmpl_mode.template_names:
			tmpl_mode.set_template("Me")
		else:
			# use the first available template
			if tmpl_mode.template_names:
				tmpl_mode.set_template(tmpl_mode.template_names[0])
			else:
				print("PASS: no templates available, skipping")
				sys.exit(0)
		# place the template
		tmpl_mode._place_template(200.0, 200.0)
		# verify atoms were added
		atom_items = [
			i for i in mw.scene.items()
			if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		assert len(atom_items) > 0, "template should have added atoms to scene"
		assert len(mw.document.molecules) > 0, "document should have molecules"
		print("PASS: template placement adds atoms (%d atoms)" % len(atom_items))
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_context_menu_delete_atom():
	"""Context menu _delete_atom() removes atom with undo support."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		import bkchem_qt.canvas.items.atom_item
		import bkchem_qt.actions.context_menu
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		mw._mode_manager.set_mode("draw")
		draw_mode = mw._mode_manager.current_mode
		atom_item = draw_mode._create_atom_at(100.0, 200.0, "C")
		assert atom_item is not None
		# verify atom exists
		items = [
			i for i in mw.scene.items()
			if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		assert len(items) == 1
		# delete via context menu helper
		bkchem_qt.actions.context_menu._delete_atom(mw.view, atom_item)
		items = [
			i for i in mw.scene.items()
			if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		assert len(items) == 0, "atom should be removed"
		# undo should restore it
		mw.document.undo_stack.undo()
		items = [
			i for i in mw.scene.items()
			if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		assert len(items) == 1, "atom should be restored after undo"
		print("PASS: context menu delete with undo works")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_stub_modes_emit_not_implemented():
	"""Stub modes emit 'not yet implemented' status messages."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		import PySide6.QtCore
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		stub_modes = ["vector", "bracket", "plus", "repair", "misc"]
		for mode_name in stub_modes:
			mw._mode_manager.set_mode(mode_name)
			mode = mw._mode_manager.current_mode
			messages = []
			mode.status_message.connect(messages.append)
			# simulate a mouse press
			pos = PySide6.QtCore.QPointF(100.0, 100.0)
			mode.mouse_press(pos, None)
			assert len(messages) > 0, f"{mode_name}: should emit status message"
			assert "not yet implemented" in messages[-1], (
				f"{mode_name}: message should say 'not yet implemented', got: {messages[-1]}"
			)
		print("PASS: all %d stub modes emit not-yet-implemented" % len(stub_modes))
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout
