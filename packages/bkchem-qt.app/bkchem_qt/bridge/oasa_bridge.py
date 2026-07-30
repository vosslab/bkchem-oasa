"""Bridge between OASA chemistry objects and BKChem-Qt model wrappers."""

# Standard Library
import math

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
import oasa.codec_registry
import oasa.cdml_bond_io
import oasa.cdml_document
from oasa import coords_generator
from oasa import transform3d_lib
from oasa.cdml_writer import CPK_COLORS

import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.molecule_model

# default canvas center and bond length for initial display
DEFAULT_CENTER_X = 2000.0
DEFAULT_CENTER_Y = 1500.0
DEFAULT_BOND_LENGTH_PT = 40.0


#============================================
def paper_catalog() -> dict[str, list[float] | None]:
	"""Return OASA's plain CDML paper catalog for Qt display adapters."""
	return oasa.cdml_document.paper_catalog()


#============================================
def oasa_mol_to_qt_mol(
		mol: oasa.molecule_lib.Molecule,
		bond_length_pt: float | None = DEFAULT_BOND_LENGTH_PT,
		) -> bkchem_qt.models.molecule_model.MoleculeModel:
	"""Convert an OASA molecule to a Qt MoleculeModel.

	Creates AtomModel and BondModel wrappers for every vertex and edge in
	the OASA molecule. When the atoms already carry coordinates, the
	molecule is rescaled so that the average bond length matches a numeric
	``bond_length_pt`` and centered at (DEFAULT_CENTER_X, DEFAULT_CENTER_Y).
	Passing ``None`` preserves the input coordinate system for native CDML.

	Args:
		mol: OASA molecule object.
		bond_length_pt: Target average bond length in scene-space points.

	Returns:
		MoleculeModel wrapping the converted atoms and bonds.
	"""
	mol_model = bkchem_qt.models.molecule_model.MoleculeModel(
		oasa_mol=oasa.molecule_lib.Molecule()
	)
	mol_model.mol_id = str(getattr(mol, "id", "") or "")
	mol_model.name = str(getattr(mol, "name", "") or "")

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
	if has_coords and mol_model.atoms and bond_length_pt is not None:
		_rescale_and_center(mol_model, bond_length_pt)

	return mol_model


#============================================
def _rescale_and_center(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		bond_length_pt: float,
		) -> None:
	"""Rescale atom positions so avg bond length matches target, then center.

	Computes the average bond length from current positions, builds a
	Transform3d that scales to match ``bond_length_pt``, and translates
	the centroid to (DEFAULT_CENTER_X, DEFAULT_CENTER_Y).

	Args:
		mol_model: MoleculeModel with positioned atoms.
		bond_length_pt: Target average bond length in scene-space points.
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
	scale = bond_length_pt / avg_bl

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
def oasa_atom_to_qt_atom(
		oasa_atom: oasa.atom_lib.Atom,
		) -> bkchem_qt.models.atom_model.AtomModel:
	"""Convert an OASA atom to an AtomModel.

	Copies coordinates, element symbol, charge, isotope, valency,
	multiplicity, free sites, and explicit hydrogens. Applies CPK color
	for non-carbon heteroatoms.

	Args:
		oasa_atom: OASA atom object.

	Returns:
		AtomModel with chemistry and display properties populated.
	"""
	atom_model = bkchem_qt.models.atom_model.AtomModel(
		oasa_atom=oasa.atom_lib.Atom(symbol=oasa_atom.symbol)
	)
	atom_id = getattr(oasa_atom, "id", None)
	if atom_id:
		atom_model._chem_atom.id = str(atom_id)

	# copy coordinates (may be None for unpositioned atoms)
	x = oasa_atom.x if oasa_atom.x is not None else 0.0
	y = oasa_atom.y if oasa_atom.y is not None else 0.0
	z = oasa_atom.z if oasa_atom.z is not None else 0.0
	atom_model.set_xyz(x, y, z)

	# copy chemistry properties
	atom_model.charge = oasa_atom.charge
	atom_model.valency = oasa_atom.valency
	atom_model.multiplicity = oasa_atom.multiplicity
	atom_model.free_sites = oasa_atom.free_sites
	atom_model.explicit_hydrogens = oasa_atom.explicit_hydrogens
	if oasa_atom.isotope is not None:
		atom_model.isotope = oasa_atom.isotope
	_display_atom_properties_to_qt(oasa_atom, atom_model)

	# apply CPK color for non-carbon heteroatoms
	symbol = oasa_atom.symbol
	cpk_color = CPK_COLORS.get(symbol)
	if cpk_color and symbol != "C" and "line_color" not in atom_model._cdml_display_fields:
		atom_model._line_color = cpk_color

	return atom_model


#============================================
def _display_atom_properties_to_qt(
		oasa_atom: oasa.atom_lib.Atom,
		atom_model: bkchem_qt.models.atom_model.AtomModel,
		) -> None:
	"""Copy supported CDML atom depiction fields into the Qt atom model."""
	properties = oasa_atom.properties_
	if "show" in properties:
		atom_model.show = properties["show"] == "yes"
	if "show_hydrogens" in properties:
		atom_model.show_hydrogens = properties["show_hydrogens"] == "on"
	if "font_size" in properties:
		atom_model.font_size = int(properties["font_size"])
	if "font_family" in properties:
		atom_model.font_family = properties["font_family"]
	if "line_color" in properties:
		atom_model.line_color = properties["line_color"]


#============================================
def oasa_bond_to_qt_bond(
		oasa_bond: oasa.bond_lib.Bond,
		) -> bkchem_qt.models.bond_model.BondModel:
	"""Convert an OASA bond to a BondModel.

	Copies bond chemistry and all supported CDML depiction fields. Endpoint
	atoms are wired separately by the molecule-level converter.

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
	# Haworth layout owns these semantic depiction tags. Keep the scalar tag
	# alongside the ``q``/``w`` bond types without retaining OASA references.
	haworth_position = oasa_bond.properties_.get("haworth_position")
	if haworth_position:
		bond_model._chem_bond.properties_["haworth_position"] = haworth_position
	bond_id = getattr(oasa_bond, "id", None)
	if bond_id:
		bond_model._chem_bond.id = str(bond_id)
	_display_bond_properties_to_qt(oasa_bond, bond_model)
	return bond_model


#============================================
def _display_bond_properties_to_qt(
		oasa_bond: oasa.bond_lib.Bond,
		bond_model: bkchem_qt.models.bond_model.BondModel,
		) -> None:
	"""Copy supported CDML depiction fields from OASA to a Qt bond model."""
	depiction = oasa.cdml_bond_io.resolve_bond_depiction(oasa_bond)
	bond_model.install_projected_depiction(depiction)


#============================================
def qt_mol_to_oasa_mol(
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		) -> oasa.molecule_lib.Molecule:
	"""Convert a Qt MoleculeModel back to a pure OASA molecule.

	Creates new OASA atom and bond objects suitable for format export
	through OASA codecs or CDML serialization.

	Args:
		mol_model: MoleculeModel to convert.

	Returns:
		oasa.molecule_lib.Molecule with atoms and bonds.
	"""
	oasa_mol = oasa.molecule_lib.Molecule()
	if mol_model.mol_id:
		oasa_mol.id = mol_model.mol_id
	if mol_model.name:
		oasa_mol.name = mol_model.name

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
		oasa_atom.free_sites = am.free_sites
		oasa_atom.explicit_hydrogens = am.explicit_hydrogens
		_display_atom_properties_to_oasa(am, oasa_atom)
		atom_id = getattr(am._chem_atom, "id", None)
		if atom_id:
			oasa_atom.id = str(atom_id)
		if am.isotope is not None:
			oasa_atom.isotope = am.isotope
		oasa_mol.add_vertex(oasa_atom)
		qt_to_oasa_atom[id(am)] = oasa_atom

	# create bonds
	for bm in mol_model.bonds:
		oasa_bond = oasa.bond_lib.Bond(order=bm.order, type=bm.type)
		if "haworth_position" in bm._chem_bond.properties_:
			oasa_bond.properties_["haworth_position"] = (
				bm._chem_bond.properties_["haworth_position"]
			)
		_display_bond_properties_to_oasa(bm, oasa_bond)
		bond_id = getattr(bm._chem_bond, "id", None)
		if bond_id:
			oasa_bond.id = str(bond_id)
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
def _display_atom_properties_to_oasa(
		atom_model: bkchem_qt.models.atom_model.AtomModel,
		oasa_atom: oasa.atom_lib.Atom,
		) -> None:
	"""Copy explicit Qt atom display edits into OASA's CDML property carrier."""
	properties = oasa_atom.properties_
	fields = atom_model._cdml_display_fields
	if "show" in fields:
		properties["show"] = "yes" if atom_model.show else "no"
	if "show_hydrogens" in fields:
		properties["show_hydrogens"] = "on" if atom_model.show_hydrogens else "off"
	if "font_size" in fields:
		properties["font_size"] = str(atom_model.font_size)
	if "font_family" in fields:
		properties["font_family"] = atom_model.font_family
	if "line_color" in fields:
		properties["line_color"] = atom_model.line_color


#============================================
def _display_bond_properties_to_oasa(
		bond_model: bkchem_qt.models.bond_model.BondModel,
		oasa_bond: oasa.bond_lib.Bond,
		) -> None:
	"""Copy supported Qt depiction fields into OASA/CDML writer fields."""
	bond_model._sync_chem_bond_depiction()
	source = bond_model._chem_bond
	depiction = oasa.cdml_bond_io.resolve_bond_depiction(source)
	oasa_bond.line_color = depiction.color
	oasa_bond.wavy_style = depiction.wavy_style
	oasa_bond.center = depiction.center
	oasa_bond.line_width = bond_model.line_width
	oasa_bond.bond_width = bond_model.bond_width
	oasa_bond.wedge_width = bond_model.wedge_width
	oasa_bond.double_length_ratio = depiction.double_ratio
	oasa_bond.auto_bond_sign = depiction.auto_sign
	oasa_bond.equithick = int(depiction.equithick)
	oasa_bond.simple_double = int(depiction.simple_double)
	for name in depiction.explicit_fields:
		if name in source.properties_:
			oasa_bond.properties_[name] = source.properties_[name]
	if "color" in depiction.explicit_fields and "line_color" in source.properties_:
		oasa_bond.properties_["line_color"] = source.properties_["line_color"]
	haworth_position = source.properties_.get("haworth_position")
	if haworth_position:
		oasa_bond.properties_["haworth_position"] = haworth_position
	oasa.cdml_bond_io.set_cdml_bond_explicit_fields(
		oasa_bond, depiction.explicit_fields,
	)


#============================================
def read_codec_file(
		codec_name: str,
		file_obj: object,
		**kwargs,
		) -> list[bkchem_qt.models.molecule_model.MoleculeModel]:
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
def write_codec_file(
		codec_name: str,
		mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
		file_obj: object,
		**kwargs,
		) -> None:
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
