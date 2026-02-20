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

# Standard Library
import os
import sys

MIN_PYTHON = (3, 10)
if sys.version_info < MIN_PYTHON:
	min_version = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
	raise ImportError(f"Python {min_version}+ is required for OASA")

def _read_repo_version( key, fallback):
	version_path = os.path.abspath( os.path.join( os.path.dirname( __file__), "..", "..", "..", "version.txt"))
	if not os.path.isfile( version_path):
		return fallback
	with open( version_path, "r") as handle:
		for line in handle:
			text = line.strip()
			if not text or text.startswith( "#"):
				continue
			if "=" not in text:
				continue
			name, value = [part.strip() for part in text.split( "=", 1)]
			if name.lower() == "version" and value:
				return value
			if name.lower() == key.lower() and value:
				return value
	return fallback

__version__ = _read_repo_version( "oasa", "26.02")


# CamelCase class imports from renamed modules
from oasa.atom_lib import Atom
from oasa.bond_lib import Bond
from oasa.molecule_lib import Molecule
from oasa.query_atom import QueryAtom
from oasa.chem_vertex import ChemVertex

# module imports (renamed modules)
from oasa import smiles_lib
from oasa import molfile_lib
from oasa import inchi_lib
from oasa import stereochemistry_lib
from oasa import transform_lib
from oasa import transform3d_lib
from oasa import reaction_lib
from oasa import plugin_lib

# non-renamed module imports
from oasa import oasa_utils
from oasa import coords_generator
from oasa import coords_optimizer
from oasa import cdml
from oasa import cdml_bond_io
from oasa import cdml_writer
from oasa import codec_registry
from oasa import bond_semantics
from oasa import safe_xml
from oasa import graph
from oasa import linear_formula
from oasa import periodic_table
from oasa import oasa_config
from oasa import oasa_exceptions
from oasa import atom_colors
from oasa import dom_extensions
from oasa import svg_out
from oasa import render_geometry
from oasa import render_ops
from oasa import render_out
from oasa import wedge_geometry
from oasa import haworth
from oasa import sugar_code
from oasa import sugar_code_smiles
from oasa import haworth_spec
from oasa import haworth_renderer
from oasa import sugar_code_names
from oasa import smiles_to_sugar_code
from oasa import geometry
from oasa import hex_grid
from oasa import molecule_utils
from oasa import known_groups

_EXPORTED_MODULES = [
	Atom,
	Bond,
	Molecule,
	QueryAtom,
	ChemVertex,
	smiles_lib,
	molfile_lib,
	inchi_lib,
	stereochemistry_lib,
	transform_lib,
	transform3d_lib,
	reaction_lib,
	plugin_lib,
	oasa_utils,
	coords_generator,
	coords_optimizer,
	cdml,
	cdml_bond_io,
	cdml_writer,
	codec_registry,
	bond_semantics,
	safe_xml,
	graph,
	linear_formula,
	periodic_table,
	oasa_config,
	oasa_exceptions,
	atom_colors,
	dom_extensions,
	svg_out,
	render_geometry,
	render_ops,
	render_out,
	wedge_geometry,
	haworth,
	sugar_code,
	sugar_code_smiles,
	haworth_spec,
	haworth_renderer,
	sugar_code_names,
	smiles_to_sugar_code,
	geometry,
	hex_grid,
	molecule_utils,
	known_groups,
]

allNames = [
	'Atom', 'Bond', 'ChemVertex', 'Molecule', 'QueryAtom',
	'smiles_lib', 'molfile_lib', 'inchi_lib', 'stereochemistry_lib',
	'transform_lib', 'transform3d_lib', 'reaction_lib', 'plugin_lib',
	'oasa_utils', 'oasa_config', 'oasa_exceptions',
	'coords_generator', 'coords_optimizer',
	'cdml', 'cdml_bond_io', 'cdml_writer',
	'codec_registry', 'bond_semantics', 'safe_xml',
	'graph', 'linear_formula', 'periodic_table',
	'atom_colors', 'dom_extensions', 'svg_out',
	'render_geometry', 'render_ops', 'render_out',
	'wedge_geometry', 'geometry',
	'haworth', 'sugar_code', 'sugar_code_smiles',
	'haworth_spec', 'haworth_renderer',
	'sugar_code_names', 'smiles_to_sugar_code',
	'hex_grid', 'molecule_utils', 'known_groups',
	'__version__',
]

try:
	from oasa import cairo_out
except ImportError:
	CAIRO_AVAILABLE = False
else:
	allNames.append("cairo_out")
	_EXPORTED_MODULES.append(cairo_out)
	CAIRO_AVAILABLE = True

# inchi_key
try:
	from oasa import inchi_key
except Exception:
	INCHI_KEY_AVAILABLE = False
else:
	allNames.append("inchi_key")
	_EXPORTED_MODULES.append(inchi_key)
	INCHI_KEY_AVAILABLE = True

# pybel
try:
	from oasa import pybel_bridge
except Exception:
	PYBEL_AVAILABLE = False
else:
	allNames.append("pybel_bridge")
	_EXPORTED_MODULES.append(pybel_bridge)
	PYBEL_AVAILABLE = True


__all__ = allNames
