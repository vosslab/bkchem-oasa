"""Focused persistence and undo contracts for Qt-owned CDML fragments."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.io.cdml_io
import tests.graphics_test_retirement


#============================================
#============================================
#============================================
def test_remove_atom_undo_restores_pruned_fragment(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Structural undo restores both fragment references and graph endpoints."""
	document = bkchem_qt.io.cdml_io.load_cdml_document_string("""<cdml version="0.15"
		xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
		<molecule id="mol-1"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
		<atom id="a2" name="O"><point x="2cm" y="1cm"/></atom><bond id="b1" start="a1" end="a2" type="n" order="1"/>
		<fragment id="f1" type="explicit"><vertex id="a1"/><vertex id="a2"/><bond id="b1"/></fragment></molecule>
	</cdml>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	molecule = document.molecules[0]
	first, second = molecule.atoms
	bond = molecule.bonds[0]
	first_item = bkchem_qt.canvas.items.atom_item.AtomItem(first)
	second_item = bkchem_qt.canvas.items.atom_item.AtomItem(second)
	bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		for item in (first_item, second_item, bond_item):
			scene.addItem(item)
		document.undo_stack.push(bkchem_qt.undo.commands.RemoveAtomCommand(
			scene, molecule, first, first_item, [(bond, bond_item)],
		))
		was_pruned = not molecule.fragments
		document.undo_stack.undo()
		assert (
			was_pruned, molecule.fragments[0].atom_ids, molecule.fragments[0].bond_ids,
			bond.atom1 is first and bond.atom2 is second,
		) == (True, ("a1", "a2"), ("b1",), True)
