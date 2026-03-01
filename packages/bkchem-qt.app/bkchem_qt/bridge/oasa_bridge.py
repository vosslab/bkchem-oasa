"""Bridge between OASA chemistry objects and BKChem-Qt model wrappers."""

# Standard Library
import math

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
import oasa.codec_registry
from oasa import coords_generator
from oasa import transform3d_lib
from oasa.cdml_writer import CPK_COLORS

import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.molecule_model

# default canvas center and bond length for initial display
DEFAULT_CENTER_X = 2000.0
DEFAULT_CENTER_Y = 1500.0
DEFAULT_BOND_LENGTH_PX = 40.0


#============================================
def oasa_mol_to_qt_mol(mol, bond_length_px=DEFAULT_BOND_LENGTH_PX):
	"""Convert an OASA molecule to a Qt MoleculeModel.

	Creates AtomModel and BondModel wrappers for every vertex and edge in
	the OASA molecule. When the atoms already carry coordinates, the
	molecule is rescaled so that the average bond length matches
	``bond_length_px`` and centered at (DEFAULT_CENTER_X, DEFAULT_CENTER_Y).

	Args:
		mol: OASA molecule object.
		bond_length_px: Target average bond length in scene pixels.

	Returns:
		MoleculeModel wrapping the converted atoms and bonds.
	"""
	mol_model = bkchem_qt.models.molecule_model.MoleculeModel(
		oasa_mol=oasa.molecule_lib.Molecule()
	)

	# check whether every atom already has valid coordinates
	has_coords = True
	for a in mol.vertices:
		if a.x is None or a.y is None:
			has_coords = False
			break

	# build a mapping from oasa vertex to AtomModel for bond wiring
	oasa_to_qt_atom = {}
	for a in mol.vertices:
		atom_model = oasa_atom_to_qt_atom(a)
		mol_model.add_atom(atom_model)
		oasa_to_qt_atom[id(a)] = atom_model

	# create bonds and wire them to the correct atom endpoints
	for b in mol.edges:
		bond_model = oasa_bond_to_qt_bond(b)
		v1, v2 = b.vertices
		atom1_model = oasa_to_qt_atom[id(v1)]
		atom2_model = oasa_to_qt_atom[id(v2)]
		mol_model.add_bond(atom1_model, atom2_model, bond_model)

	# rescale and center if coordinates are present
	if has_coords and mol_model.atoms:
		_rescale_and_center(mol_model, bond_length_px)

	return mol_model


#============================================
def _rescale_and_center(mol_model, bond_length_px):
	"""Rescale atom positions so avg bond length matches target, then center.

	Computes the average bond length from current positions, builds a
	Transform3d that scales to match ``bond_length_px``, and translates
	the centroid to (DEFAULT_CENTER_X, DEFAULT_CENTER_Y).

	Args:
		mol_model: MoleculeModel with positioned atoms.
		bond_length_px: Target average bond length in scene pixels.
	"""
	atoms = mol_model.atoms
	bonds = mol_model.bonds

	# measure current average bond length
	bond_lengths = []
	for bm in bonds:
		a1 = bm.atom1
		a2 = bm.atom2
		if a1 is None or a2 is None:
			continue
		dx = a1.x - a2.x
		dy = a1.y - a2.y
		length = math.sqrt(dx * dx + dy * dy)
		bond_lengths.append(length)
	avg_bl = sum(bond_lengths) / len(bond_lengths) if bond_lengths else 1.0
	# avoid division by zero for single-atom molecules
	if avg_bl < 1e-6:
		avg_bl = 1.0
	scale = bond_length_px / avg_bl

	# compute centroid of current positions
	xs = [am.x for am in atoms]
	ys = [am.y for am in atoms]
	cx = sum(xs) / len(xs)
	cy = sum(ys) / len(ys)

	# build transform: translate centroid to origin, scale, move to default center
	trans = transform3d_lib.Transform3d()
	trans.set_move(-cx, -cy, 0)
	trans.set_scaling(scale)
	trans.set_move(DEFAULT_CENTER_X, DEFAULT_CENTER_Y, 0)

	# apply transform to every atom
	for am in atoms:
		new_x, new_y, new_z = trans.transform_xyz(am.x, am.y, am.z)
		am.set_xyz(new_x, new_y, new_z)


#============================================
def oasa_atom_to_qt_atom(oasa_atom):
	"""Convert an OASA atom to an AtomModel.

	Copies coordinates, element symbol, charge, isotope, valency, and
	multiplicity. Applies CPK color for non-carbon heteroatoms.

	Args:
		oasa_atom: OASA atom object.

	Returns:
		AtomModel with chemistry and display properties populated.
	"""
	atom_model = bkchem_qt.models.atom_model.AtomModel(
		oasa_atom=oasa.atom_lib.Atom(symbol=oasa_atom.symbol)
	)

	# copy coordinates (may be None for unpositioned atoms)
	x = oasa_atom.x if oasa_atom.x is not None else 0.0
	y = oasa_atom.y if oasa_atom.y is not None else 0.0
	z = oasa_atom.z if oasa_atom.z is not None else 0.0
	atom_model.set_xyz(x, y, z)

	# copy chemistry properties
	atom_model.charge = oasa_atom.charge
	atom_model.valency = oasa_atom.valency
	atom_model.multiplicity = oasa_atom.multiplicity
	if oasa_atom.isotope is not None:
		atom_model.isotope = oasa_atom.isotope

	# apply CPK color for non-carbon heteroatoms
	symbol = oasa_atom.symbol
	cpk_color = CPK_COLORS.get(symbol)
	if cpk_color and symbol != "C":
		atom_model.line_color = cpk_color

	return atom_model


#============================================
def oasa_bond_to_qt_bond(oasa_bond):
	"""Convert an OASA bond to a BondModel.

	Copies bond order and type. Endpoint atoms are wired separately by
	the molecule-level converter.

	Args:
		oasa_bond: OASA bond object.

	Returns:
		BondModel with chemistry properties populated.
	"""
	bond_model = bkchem_qt.models.bond_model.BondModel(
		oasa_bond=oasa.bond_lib.Bond(
			order=oasa_bond.order,
			type=oasa_bond.type,
		)
	)
	return bond_model


#============================================
def qt_mol_to_oasa_mol(mol_model):
	"""Convert a Qt MoleculeModel back to a pure OASA molecule.

	Creates new OASA atom and bond objects suitable for format export
	through OASA codecs or CDML serialization.

	Args:
		mol_model: MoleculeModel to convert.

	Returns:
		oasa.molecule_lib.Molecule with atoms and bonds.
	"""
	oasa_mol = oasa.molecule_lib.Molecule()

	# build mapping from AtomModel id to OASA atom for bond wiring
	qt_to_oasa_atom = {}
	for am in mol_model.atoms:
		oasa_atom = oasa.atom_lib.Atom(symbol=am.symbol)
		oasa_atom.x = am.x
		oasa_atom.y = am.y
		oasa_atom.z = am.z
		oasa_atom.charge = am.charge
		oasa_atom.valency = am.valency
		oasa_atom.multiplicity = am.multiplicity
		if am.isotope is not None:
			oasa_atom.isotope = am.isotope
		oasa_mol.add_vertex(oasa_atom)
		qt_to_oasa_atom[id(am)] = oasa_atom

	# create bonds
	for bm in mol_model.bonds:
		oasa_bond = oasa.bond_lib.Bond(order=bm.order, type=bm.type)
		a1 = bm.atom1
		a2 = bm.atom2
		if a1 is None or a2 is None:
			continue
		v1 = qt_to_oasa_atom.get(id(a1))
		v2 = qt_to_oasa_atom.get(id(a2))
		if v1 is None or v2 is None:
			continue
		oasa_mol.add_edge(v1, v2, e=oasa_bond)

	return oasa_mol


#============================================
def read_codec_file(codec_name, file_obj, **kwargs):
	"""Read a chemistry file via OASA codec and return MoleculeModel list.

	Uses the OASA codec registry to parse the file into an OASA molecule,
	splits disconnected components into separate MoleculeModel instances,
	and generates 2D coordinates if needed.

	Args:
		codec_name: OASA codec name (e.g. 'molfile', 'smiles', 'cdxml').
		file_obj: Open file object to read from.
		**kwargs: Additional keyword arguments passed to the codec.

	Returns:
		List of MoleculeModel instances, one per connected component.
	"""
	codec = oasa.codec_registry.get_codec(codec_name)
	mol = codec.read_file(file_obj, **kwargs)
	if mol is None:
		return []

	# generate 2D coords if not present
	coords_generator.calculate_coords(mol, bond_length=1.0, force=0)

	# split disconnected components
	if not mol.is_connected():
		parts = mol.get_disconnected_subgraphs()
	else:
		parts = [mol]

	# convert each part to a MoleculeModel
	results = []
	for part in parts:
		mol_model = oasa_mol_to_qt_mol(part)
		results.append(mol_model)
	return results


#============================================
def write_codec_file(codec_name, mol_model, file_obj, **kwargs):
	"""Write a MoleculeModel to a file via OASA codec.

	Converts the MoleculeModel back to a pure OASA molecule and delegates
	serialization to the named OASA codec.

	Args:
		codec_name: OASA codec name (e.g. 'molfile', 'smiles', 'cdxml').
		mol_model: MoleculeModel to export.
		file_obj: Open file object to write to.
		**kwargs: Additional keyword arguments passed to the codec.
	"""
	codec = oasa.codec_registry.get_codec(codec_name)
	oasa_mol = qt_mol_to_oasa_mol(mol_model)
	codec.write_file(oasa_mol, file_obj, **kwargs)
