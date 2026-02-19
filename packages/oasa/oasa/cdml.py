#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program

#--------------------------------------------------------------------------




from oasa import cdml_writer
from oasa import dom_extensions as dom_ext
from oasa import safe_xml
from oasa.coords_generator import calculate_coords



def read_cdml( text):
  """returns the last molecule for now"""
  doc = safe_xml.parse_dom_from_string( text)
  #if doc.childNodes()[0].nodeName == 'svg':
  #  path = "/svg/cdml/molecule"
  #else:
  #  path = "/cdml/molecule"
  path = "//molecule"
  for mol_el in dom_ext.simpleXPathSearch( doc, path):
    mol = cdml_writer.read_cdml_molecule_element( mol_el)
    if mol is None:
      continue
    if mol.is_connected():
      # this is here to handle diborane and similar weird things
      yield mol
    else:
      for comp in mol.get_disconnected_subgraphs():
        yield comp


def cm_to_float_coord( x):
  if not x:
    return 0
  if x[-2:] == 'cm':
    return float( x[:-2])*72/2.54
  else:
    return float( x)


##################################################
# MODULE INTERFACE

reads_text = 1
reads_files = 1
writes_text = 0
writes_files = 0

def file_to_mol( f):
  return text_to_mol( f.read())

def text_to_mol( text):
  gen = read_cdml( text)
  try:
    mol = next(gen)
  except StopIteration:
    return None
  calculate_coords( mol, bond_length=-1)
  return mol

#
##################################################


##################################################
# DEMO

if __name__ == '__main__':

  import sys

  if len( sys.argv) < 1:
    print("you must supply a filename")
    sys.exit()

  # parsing of the file

  file_name = sys.argv[1]
  with open(file_name, 'r') as f:
    mol = file_to_mol(f)

  import time

  t = time.time()
  lens = sorted(map(len, mol.get_all_cycles()))
  print(lens)
  print(time.time() - t)
  print("total %d rings" % len( lens))

##     mring = mol.get_new_induced_subgraph( ring, mol.vertex_subgraph_to_edge_subgraph( ring))
##     if not mring.is_connected():
##       print(map( len, [a for a in mring.get_connected_components()]))
##       for vs in mring.get_connected_components():
##         print([a.symbol for a in vs])
      #import molfile
      #print(molfile.mol_to_text( mring))


  #calculate_coords( mol, bond_length=-1)

  #for a in mol.vertices:
  #  print(a.x, a.y)

  print(mol)
  #print(smiles.mol_to_text( mol))
