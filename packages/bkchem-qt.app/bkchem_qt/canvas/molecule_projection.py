"""Build and install disposable molecule graphics projections."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.canvas.items.group_item


#============================================
def build_molecule_projections(
		molecules: list[object],
		) -> list[tuple[object, list[object]]]:
	"""Construct molecule graphics without changing a document or scene."""
	projections = []
	graphics_items = []
	try:
		for molecule_model in molecules:
			graphics_items = []
			for bond_model in molecule_model.bonds:
				item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
				item.molecule_model = molecule_model
				graphics_items.append(item)
			for atom_model in molecule_model.atoms:
				item = bkchem_qt.canvas.items.atom_item.AtomItem(atom_model)
				item.molecule_model = molecule_model
				graphics_items.append(item)
			for group_model in molecule_model.groups:
				item = bkchem_qt.canvas.items.group_item.GroupItem(group_model)
				item.molecule_model = molecule_model
				graphics_items.append(item)
			projections.append((molecule_model, graphics_items))
	except Exception:
		# A later wrapper can fail after earlier items have connected callbacks.
		# Retire both completed and current molecule items before preserving the
		# construction failure.
		items = [
			item
			for _molecule_model, molecule_items in projections
			for item in molecule_items
		]
		items.extend(graphics_items)
		bkchem_qt.canvas.document_projection.dispose_detached_items(items)
		raise
	return projections


#============================================
def install_molecule_projections(
		scene: PySide6.QtWidgets.QGraphicsScene,
		projections: list[tuple[object, list[object]]],
		) -> None:
	"""Install already-owned molecule graphics into one scene."""
	for _molecule_model, graphics_items in projections:
		for item in graphics_items:
			scene.addItem(item)


#============================================
def project_molecules_to_scene(
		scene: PySide6.QtWidgets.QGraphicsScene,
		molecules: list[object],
		) -> list[tuple[object, list[object]]]:
	"""Build and install molecules already owned by a loaded document."""
	projections = build_molecule_projections(molecules)
	install_molecule_projections(scene, projections)
	return projections
