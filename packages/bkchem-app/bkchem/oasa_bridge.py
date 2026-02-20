#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------

import math

oasa_available = 1
try:
  import oasa
except ImportError:
  oasa_available = 0

import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib

from oasa import transform3d_lib as transform3d
from oasa import cdml_writer
from oasa.cdml_writer import CPK_COLORS

from bkchem.bond_lib import BkBond
from bkchem.atom_lib import BkAtom
from bkchem.molecule_lib import BkMolecule

from bkchem.singleton_store import Screen



def _get_codec( name):
  return oasa.codec_registry.get_codec( name)


def _read_codec_file_to_bkchem_mols( codec_name, file_obj, paper, **kwargs):
  codec = _get_codec( codec_name)
  mol = codec.read_file( file_obj, **kwargs)
  if mol is None:
    return []
  if not mol.is_connected():
    mols = mol.get_disconnected_subgraphs()
    return [oasa_mol_to_bkchem_mol( part, paper) for part in mols]
  return [oasa_mol_to_bkchem_mol( mol, paper)]


def _write_codec_file_from_bkchem_mol( codec_name, bkchem_mol, file_obj, **kwargs):
  codec = _get_codec( codec_name)
  oasa_mol = bkchem_mol_to_oasa_mol( bkchem_mol)
  codec.write_file( oasa_mol, file_obj, **kwargs)


def _write_codec_file_from_bkchem_paper( codec_name, paper, file_obj, **kwargs):
  oasa_mols = [bkchem_mol_to_oasa_mol( mol) for mol in paper.molecules]
  merged = oasa.molecule_utils.merge_molecules( oasa_mols)
  if merged is None:
    return
  codec = _get_codec( codec_name)
  codec.write_file( merged, file_obj, **kwargs)


def validate_selected_molecule( paper):
  conts, _unique = paper.selected_to_unique_top_levels()
  mols = [o for o in conts if getattr( o, "object_type", None) == "molecule"]
  if not mols:
    raise ValueError("No molecule selected.")
  if len( mols) > 1:
    raise ValueError(f"{len(mols)} molecules selected.")
  return mols[0]


def read_codec_file( codec_name, file_obj, paper, **kwargs):
  return _read_codec_file_to_bkchem_mols( codec_name, file_obj, paper, **kwargs)


def write_codec_file_from_paper( codec_name, paper, file_obj, **kwargs):
  _write_codec_file_from_bkchem_paper( codec_name, paper, file_obj, **kwargs)


def write_codec_file_from_selected_molecule( codec_name, paper, file_obj, **kwargs):
  selected = validate_selected_molecule( paper)
  _write_codec_file_from_bkchem_mol( codec_name, selected, file_obj, **kwargs)


def _calculate_coords( mol, bond_length=1.0, force=1):
  """Generate 2D coordinates using RDKit if available, then coords_generator2, else old generator."""
  try:
    from oasa.rdkit_bridge import calculate_coords_rdkit
    calculate_coords_rdkit( mol, bond_length=bond_length)
    return
  except ImportError:
    pass
  # prefer the improved 3-layer generator over the legacy one
  try:
    import oasa.coords_generator2
    oasa.coords_generator2.calculate_coords( mol, bond_length=bond_length, force=force)
  except ImportError:
    oasa.coords_generator.calculate_coords( mol, bond_length=bond_length, force=force)


def smiles_to_cdml_elements( smiles_text, paper):
  """Convert SMILES text to a list of CDML molecule DOM elements.

  Routes through the canonical CDML serialization path:
  SMILES -> OASA molecule -> 2D coords -> scale to cm -> CDML element.
  Handles disconnected SMILES (e.g. "CC.OO") by splitting into
  separate CDML elements, one per connected component.

  Args:
    smiles_text: SMILES or IsoSMILES string
    paper: BKChem paper object (provides standard bond length)

  Returns:
    list of xml.dom.minidom.Element, each a <molecule> element
  """
  if not smiles_text or not smiles_text.strip():
    raise ValueError("Empty SMILES string")
  # parse SMILES to OASA molecule
  codec = _get_codec( "smiles")
  mol = codec.read_text( smiles_text)
  # remove zero-order bonds so dot-disconnected components separate
  mol.remove_zero_order_bonds()
  # split disconnected components
  if not mol.is_connected():
    parts = mol.get_disconnected_subgraphs()
  else:
    parts = [mol]
  # convert each component to a CDML element
  elements = []
  for part in parts:
    element = _oasa_mol_to_cdml_element( part, paper)
    elements.append( element)
  return elements


def peptide_to_cdml_elements( sequence_text, paper):
  """Convert a peptide sequence to a list of CDML molecule DOM elements.

  Delegates all chemistry to OASA: peptide validation, SMILES generation,
  SMILES parsing, 2D coordinate layout, and CDML serialization.

  Args:
    sequence_text: single-letter amino acid sequence (e.g. 'ANKLE')
    paper: BKChem paper object (provides standard bond length)

  Returns:
    list of xml.dom.minidom.Element, each a <molecule> element
  """
  from oasa import peptide_utils
  # OASA handles validation and conversion to SMILES
  smiles_text = peptide_utils.sequence_to_smiles(sequence_text)
  # reuse the existing SMILES-to-CDML pipeline
  return smiles_to_cdml_elements( smiles_text, paper)


def _oasa_mol_to_cdml_element( mol, paper):
  """Convert a single connected OASA molecule to a CDML DOM element.

  Generates 2D coordinates, rescales to match the paper standard bond
  length in cm, centers the molecule, and serializes to CDML.

  Args:
    mol: OASA molecule object (must be connected)
    paper: BKChem paper object

  Returns:
    xml.dom.minidom.Element for a <molecule>
  """
  # generate 2D coordinates (abstract units, avg bond ~ 1.0)
  _calculate_coords( mol, bond_length=1.0, force=1)
  # compute average bond length from generated coords
  bond_lengths = []
  for b in mol.edges:
    v1, v2 = b.vertices
    dx = v1.x - v2.x
    dy = v1.y - v2.y
    bond_lengths.append( math.sqrt( dx * dx + dy * dy))
  avg_bl = sum( bond_lengths) / len( bond_lengths) if bond_lengths else 1.0
  # compute desired bond length in screen pixels from paper standard
  bond_length_px = Screen.any_to_px( paper.standard.bond_length)
  # scale and center at (320, 240) pixels, matching oasa_mol_to_bkchem_mol
  scale = bond_length_px / avg_bl
  # compute centroid of generated coords
  xs = [a.x for a in mol.vertices]
  ys = [a.y for a in mol.vertices]
  cx = sum( xs) / len( xs)
  cy = sum( ys) / len( ys)
  # apply transform: center at origin, scale, move to (320, 240)
  trans = transform3d.transform3d()
  trans.set_move( -cx, -cy, 0)
  trans.set_scaling( scale)
  trans.set_move( 320, 240, 0)
  for a in mol.vertices:
    a.x, a.y, a.z = trans.transform_xyz( a.x, a.y, a.z)
  # serialize to CDML element with coordinates in cm via Screen
  element = cdml_writer.write_cdml_molecule_element(
    mol, coord_to_text=Screen.px_to_text_with_unit)
  return element


def mol_to_smiles( mol):
  codec = _get_codec( "smiles")
  m = bkchem_mol_to_oasa_mol( mol)
  m.remove_unimportant_hydrogens()
  text = codec.write_text( m)
  return text


def read_inchi( text, paper):
  codec = _get_codec( "inchi")
  mol = codec.read_text( text, calc_coords=1, include_hydrogens=False)
  m = oasa_mol_to_bkchem_mol( mol, paper)
  return m


def mol_to_inchi( mol, program):
  m = bkchem_mol_to_oasa_mol( mol)
  # we do not use mol_to_text because generate_inchi_and_inchikey returns extra warning messages
  _inchi, _key, _warnings = oasa.inchi_lib.generate_inchi_and_inchikey( m, program=program, fixed_hs=False)
  return (_inchi, _key, _warnings)


def read_molfile( file, paper):
  return _read_codec_file_to_bkchem_mols( "molfile", file, paper)


def write_molfile( mol, file):
  _write_codec_file_from_bkchem_mol( "molfile", mol, file)


def read_cml( file_obj, paper, version=1):
  codec_name = "cml2" if int( version) == 2 else "cml"
  return _read_codec_file_to_bkchem_mols( codec_name, file_obj, paper)


def write_cml( mol, file_obj, version=1):
  del mol, file_obj, version
  raise ValueError("CML export is not supported. Legacy CML is import-only.")


def write_cml_from_paper( paper, file_obj, version=1):
  del paper, file_obj, version
  raise ValueError("CML export is not supported. Legacy CML is import-only.")


def read_cdxml( file_obj, paper):
  return _read_codec_file_to_bkchem_mols( "cdxml", file_obj, paper)


def write_cdxml( mol, file_obj):
  _write_codec_file_from_bkchem_mol( "cdxml", mol, file_obj)


def write_cdxml_from_paper( paper, file_obj):
  _write_codec_file_from_bkchem_paper( "cdxml", paper, file_obj)


# ==================================================
# OASA -> BKCHEM
# Chemistry properties set via public API (at.x, at.charge, bo.type, etc.);
# after Wave 2, these delegate to _chem_atom/_chem_bond internally.
def oasa_mol_to_bkchem_mol( mol, paper):
  m = BkMolecule( paper)
  if None in (j for i in ((a.x, a.y) for a in mol.atoms)
                  for j in i):
    calc_position = 0
  else:
    calc_position = 1

  minx = None
  maxx = None
  miny = None
  maxy = None
  # atoms
  for a in mol.vertices:
    a2 = oasa_atom_to_bkchem_atom( a, paper, m)
    m.insert_atom( a2)
    if calc_position:
      # data for rescaling
      if not maxx or a2.x > maxx:
        maxx = a2.x
      if not minx or a2.x < minx:
        minx = a2.x
      if not miny or a2.y < miny:
        miny = a2.y
      if not maxy or a2.y > maxy:
        maxy = a2.y
  # bonds
  bond_lengths = []
  for b in mol.edges:
    b2 = oasa_bond_to_bkchem_bond( b, paper)
    aa1, aa2 = b.vertices
    atom1 = m.atoms[ mol.vertices.index( aa1)]
    atom2 = m.atoms[ mol.vertices.index( aa2)]
    m.add_edge( atom1, atom2, b2)
    b2.molecule = m
    if calc_position:
      bond_lengths.append( math.sqrt( (b2.atom1.x-b2.atom2.x)**2 + (b2.atom1.y-b2.atom2.y)**2))
  # rescale
  if calc_position:
    bl = sum( bond_lengths) / len( bond_lengths)
    scale = Screen.any_to_px( paper.standard.bond_length) / bl
    movex = (maxx+minx)/2
    movey = (maxy+miny)/2
    trans = transform3d.transform3d()
    trans.set_move( -movex, -movey, 0)
    trans.set_scaling( scale)
    trans.set_move( 320, 240, 0)
    for a in m.atoms:
      a.x, a.y, a.z = trans.transform_xyz( a.x, a.y, a.z)
  return m


def oasa_atom_to_bkchem_atom( a, paper, m):
  """Convert an OASA atom to a BKChem atom.

  Sets BKChem atom properties through the public API; after Wave 2
  these property setters delegate to _chem_atom internally.

  Note: a.properties_ is accessed on the source OASA atom (not a
  BKChem atom), so no composition-layer change applies here.

  Args:
    a: OASA atom object
    paper: BKChem paper object
    m: BKChem molecule that will own the atom

  Returns:
    BKChem atom instance
  """
  at = BkAtom( standard=paper.standard, molecule=m)
  # coordinates set through property setters (delegate to _chem_atom after Wave 2)
  at.x = a.x
  at.y = a.y
  at.z = a.z
  at.set_name( a.symbol, interpret=1)
  # apply CPK color for non-carbon heteroatoms (InChI path bypasses CDML)
  cpk_color = CPK_COLORS.get(a.symbol)
  if cpk_color and a.symbol != 'C':
    at.line_color = cpk_color
  # chemistry properties set through public API
  at.charge = a.charge
  # inchi_number read from pure OASA atom properties_, not BKChem composition
  at.number = a.properties_.get( 'inchi_number', None)
  at.show_number = False
  at.isotope = a.isotope
  at.valency = a.valency
  at.multiplicity = a.multiplicity
  return at


def oasa_bond_to_bkchem_bond( b, paper):
  """Convert an OASA bond to a BKChem bond.

  Sets bond properties through the public API; after Wave 2 these
  property setters delegate to _chem_bond internally.

  Args:
    b: OASA bond object
    paper: BKChem paper object

  Returns:
    BKChem bond instance
  """
  bo = BkBond( standard=paper.standard)
  # type and order set through property setters (delegate to _chem_bond after Wave 2)
  bo.type = b.type
  bo.order = b.order
  return bo


# ==================================================
# BKCHEM -> OASA
# Reading BKChem properties (a.symbol, a.charge, b.order, b.atoms, etc.);
# after Wave 2, these read from _chem_atom/_chem_bond internally.
def bkchem_mol_to_oasa_mol( mol):
  m = oasa.molecule_lib.Molecule()
  for a in mol.atoms:
    m.add_vertex( bkchem_atom_to_oasa_atom( a))
  for b in mol.bonds:
    b2 = bkchem_bond_to_oasa_bond( b)
    # b.atoms returns bond vertex refs; after Wave 2 uses _bond_vertices property
    aa1, aa2 = b.atoms
    v1 = m.vertices[ mol.atoms.index( aa1)]
    v2 = m.vertices[ mol.atoms.index( aa2)]
    b2.vertices = (v1, v2)
    m.add_edge( v1, v2, b2)
  return m


def bkchem_atom_to_oasa_atom( a):
  """Convert a BKChem atom to an OASA atom.

  Reads BKChem atom properties through the public API; after Wave 2
  these property getters read from _chem_atom internally.

  Args:
    a: BKChem atom object

  Returns:
    OASA atom instance
  """
  # a.symbol reads from _chem_atom after Wave 2
  s = a.symbol
  ret = oasa.atom_lib.Atom( symbol=s)
  # coordinates read through public API (delegate to _chem_atom after Wave 2)
  x, y, z = a.get_xyz()
  ret.x = x
  ret.y = y
  ret.z = z
  # chemistry properties read through public API
  ret.charge = a.charge
  ret.multiplicity = a.multiplicity
  ret.valency = a.valency
  if hasattr(a,'isotope'):
    ret.isotope = a.isotope
  return ret


def bkchem_bond_to_oasa_bond( b):
  """Convert a BKChem bond to an OASA bond.

  Reads BKChem bond properties through the public API; after Wave 2
  these property getters read from _chem_bond internally.

  Args:
    b: BKChem bond object

  Returns:
    OASA bond instance
  """
  # b.order and b.type read from _chem_bond after Wave 2
  ret = oasa.bond_lib.Bond( order=b.order, type=b.type)
  return ret


### TODO

# coordinates transformations
