"""RDKit bridge for OASA molecule conversion and 2D coordinate generation.

Provides functions to convert between OASA and RDKit molecule representations,
and to generate 2D coordinates using RDKit's Compute2DCoords algorithm as an
alternative to OASA's native coords_generator.
"""

# Standard Library
import math

# PIP3 modules
import rdkit.Chem
import rdkit.Chem.AllChem

# local repo modules
from oasa.atom_lib import Atom as atom
from oasa.bond_lib import Bond as bond
from oasa.molecule_lib import Molecule as molecule
from oasa.periodic_table import periodic_table as PT


# map atomic number -> element symbol for reverse lookup
_NUM_TO_SYMBOL = {v['ord']: k for k, v in PT.items()}

# OASA bond order -> RDKit bond type
_OASA_TO_RDKIT_BOND = {
	1: rdkit.Chem.BondType.SINGLE,
	2: rdkit.Chem.BondType.DOUBLE,
	3: rdkit.Chem.BondType.TRIPLE,
	4: rdkit.Chem.BondType.AROMATIC,
}

# RDKit bond type -> OASA bond order
_RDKIT_TO_OASA_BOND = {v: k for k, v in _OASA_TO_RDKIT_BOND.items()}


#============================================
def oasa_to_rdkit_mol(omol) -> tuple:
	"""Convert an OASA molecule to an RDKit RWMol.

	Args:
		omol: OASA molecule object.

	Returns:
		Tuple of (rdkit.Chem.RWMol, dict mapping OASA atom -> RDKit atom index).
	"""
	rmol = rdkit.Chem.RWMol()
	oatom_to_ridx = {}

	# add atoms
	for oatom in omol.atoms:
		atomic_num = PT[oatom.symbol]['ord']
		ratom = rdkit.Chem.Atom(atomic_num)
		ratom.SetFormalCharge(oatom.charge)
		ridx = rmol.AddAtom(ratom)
		oatom_to_ridx[oatom] = ridx

	# add bonds
	for obond in omol.bonds:
		oa1, oa2 = obond.vertices
		ridx1 = oatom_to_ridx[oa1]
		ridx2 = oatom_to_ridx[oa2]
		bond_type = _OASA_TO_RDKIT_BOND.get(obond.order, rdkit.Chem.BondType.SINGLE)
		rmol.AddBond(ridx1, ridx2, bond_type)

	return rmol, oatom_to_ridx


#============================================
def rdkit_to_oasa_mol(rmol) -> tuple:
	"""Convert an RDKit mol to an OASA molecule.

	Args:
		rmol: RDKit Mol object.

	Returns:
		Tuple of (OASA molecule, dict mapping RDKit atom index -> OASA atom).
	"""
	omol = molecule()
	ridx_to_oatom = {}

	# add atoms
	for ratom in rmol.GetAtoms():
		ridx = ratom.GetIdx()
		symbol = _NUM_TO_SYMBOL.get(ratom.GetAtomicNum(), 'C')
		oatom = atom(symbol=symbol, charge=ratom.GetFormalCharge())
		# copy 2D coordinates if available
		conf = rmol.GetConformer(0) if rmol.GetNumConformers() > 0 else None
		if conf is not None:
			pos = conf.GetAtomPosition(ridx)
			oatom.x = pos.x
			oatom.y = pos.y
		omol.add_vertex(oatom)
		ridx_to_oatom[ridx] = oatom

	# add bonds
	for rbond in rmol.GetBonds():
		ridx1 = rbond.GetBeginAtomIdx()
		ridx2 = rbond.GetEndAtomIdx()
		order = _RDKIT_TO_OASA_BOND.get(rbond.GetBondType(), 1)
		obond = bond(order=order)
		oa1 = ridx_to_oatom[ridx1]
		oa2 = ridx_to_oatom[ridx2]
		omol.add_edge(oa1, oa2, obond)

	return omol, ridx_to_oatom


#============================================
def calculate_coords_rdkit(omol, bond_length: float = 1.0):
	"""Generate 2D coordinates for an OASA molecule using RDKit.

	Converts the OASA molecule to RDKit, computes 2D coordinates via
	AllChem.Compute2DCoords, straightens the depiction, and copies
	the coordinates back into the OASA atom .x and .y attributes.

	Args:
		omol: OASA molecule object (modified in place).
		bond_length: Target bond length for the output coordinates.

	Returns:
		The modified OASA molecule with coordinates set.
	"""
	rmol, oatom_to_ridx = oasa_to_rdkit_mol(omol)
	# compute 2D layout
	rdkit.Chem.AllChem.Compute2DCoords(rmol)
	# straighten the depiction for cleaner output
	rdkit.Chem.AllChem.StraightenDepiction(rmol)

	# get the conformer with computed coordinates
	conf = rmol.GetConformer(0)

	# measure average bond length in the RDKit output for scaling
	rdkit_bond_lengths = []
	for rbond in rmol.GetBonds():
		pos1 = conf.GetAtomPosition(rbond.GetBeginAtomIdx())
		pos2 = conf.GetAtomPosition(rbond.GetEndAtomIdx())
		dx = pos1.x - pos2.x
		dy = pos1.y - pos2.y
		rdkit_bond_lengths.append(math.sqrt(dx * dx + dy * dy))

	# compute scale factor from RDKit coords to desired bond_length
	if rdkit_bond_lengths:
		avg_rdkit_bl = sum(rdkit_bond_lengths) / len(rdkit_bond_lengths)
		scale = bond_length / avg_rdkit_bl if avg_rdkit_bl > 1e-9 else 1.0
	else:
		scale = 1.0

	# copy scaled coordinates back into OASA atoms
	for oatom, ridx in oatom_to_ridx.items():
		pos = conf.GetAtomPosition(ridx)
		oatom.x = pos.x * scale
		oatom.y = pos.y * scale

	return omol
