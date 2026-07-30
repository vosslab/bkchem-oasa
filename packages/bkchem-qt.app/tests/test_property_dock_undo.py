"""One PropertyDock-to-canvas rendering behavior."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.main_window
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.document
import bkchem_qt.models.molecule_model
import bkchem_qt.widgets.property_dock
import tests.graphics_test_retirement


#============================================
def test_bond_order_dock_edit_rebuilds_selected_bond_rendering(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A dock bond-order edit propagates through the selected canvas item."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	first = bkchem_qt.models.atom_model.AtomModel(
		oasa_atom=oasa.atom_lib.Atom(symbol="C"),
	)
	second = bkchem_qt.models.atom_model.AtomModel(
		oasa_atom=oasa.atom_lib.Atom(symbol="C"),
	)
	first.set_xyz(20.0, 40.0, 0.0)
	second.set_xyz(120.0, 40.0, 0.0)
	bond = bkchem_qt.models.bond_model.BondModel(
		oasa_bond=oasa.bond_lib.Bond(order=1, type="n"),
	)
	molecule.add_atom(first)
	molecule.add_atom(second)
	molecule.add_bond(first, second, bond)
	bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond)
	dock = bkchem_qt.widgets.property_dock.PropertyDock(document)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		try:
			document.add_molecule(molecule, mark_dirty=False)
			scene.addItem(bond_item)
			scene.addItem(bkchem_qt.canvas.items.atom_item.AtomItem(first))
			scene.addItem(bkchem_qt.canvas.items.atom_item.AtomItem(second))
			bond_item.setSelected(True)
			dock.update_from_selection()
			initial_ops = bond_item._ops
			dock._bond_order_combo.setCurrentIndex(dock._bond_order_combo.findData(2))
			assert bond_item._ops is not initial_ops
		finally:
			dock.set_document(None)
			dock.close()
			assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, dock)
