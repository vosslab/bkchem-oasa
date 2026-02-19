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


# local repo modules
from .atom import atom
from .bond import bond
from .molecule import molecule
from . import smiles
from . import coords_generator
from . import coords_optimizer
from . import molfile
from . import inchi
from . import cdml
from . import cdml_bond_io
from . import cdml_writer
from . import codec_registry
from . import bond_semantics
from . import safe_xml
from . import graph
from . import linear_formula
from . import periodic_table
from . import config
from .query_atom import query_atom
from .chem_vertex import chem_vertex
from . import oasa_exceptions
from . import atom_colors
from . import dom_extensions
from . import svg_out
from . import render_geometry
from . import render_ops
from . import render_out
from . import wedge_geometry
from . import haworth
from . import sugar_code
from . import sugar_code_smiles
from . import haworth_spec
from . import haworth_renderer
from . import sugar_code_names
from . import smiles_to_sugar_code
from . import stereochemistry
from . import geometry
from . import hex_grid
from . import molecule_utils
from . import transform3d
from . import transform
from . import known_groups

_EXPORTED_MODULES = [
	atom,
	bond,
	molecule,
	smiles,
	coords_generator,
	coords_optimizer,
	molfile,
	inchi,
	cdml,
	cdml_bond_io,
	cdml_writer,
	codec_registry,
	bond_semantics,
	safe_xml,
	graph,
	linear_formula,
	periodic_table,
	config,
	query_atom,
	chem_vertex,
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
	stereochemistry,
	geometry,
	hex_grid,
	molecule_utils,
	transform3d,
	transform,
	known_groups,
]

allNames = ['atom', 'bond', 'chem_vertex', 'coords_generator', 'config',
	'coords_optimizer', 'geometry', 'graph', 'inchi', 'known_groups',
	'linear_formula', 'molecule', 'molfile',
	'oasa_exceptions', 'periodic_table', 'query_atom', 'smiles',
	'stereochemistry', 'svg_out', 'transform',
	'transform3d']
allNames.extend([
	"atom_colors",
	"bond_semantics",
	"cdml_bond_io",
	"codec_registry",
	"dom_extensions",
	"safe_xml",
	"render_geometry",
	"render_ops",
	"render_out",
	"wedge_geometry",
	"sugar_code",
	"sugar_code_smiles",
	"haworth_spec",
	"haworth_renderer",
	"sugar_code_names",
	"smiles_to_sugar_code",
	"molecule_utils",
])
allNames.append("cdml_writer")
allNames.append("hex_grid")
allNames.append("__version__")

try:
	from . import cairo_out
except ImportError:
	CAIRO_AVAILABLE = False
else:
	allNames.append("cairo_out")
	_EXPORTED_MODULES.append(cairo_out)
	CAIRO_AVAILABLE = True

# inchi_key
try:
	from . import inchi_key
except Exception:
	INCHI_KEY_AVAILABLE = False
else:
	allNames.append("inchi_key")
	_EXPORTED_MODULES.append(inchi_key)
	INCHI_KEY_AVAILABLE = True

# pybel
try:
	from . import pybel_bridge
except Exception:
	PYBEL_AVAILABLE = False
else:
	allNames.append("pybel_bridge")
	_EXPORTED_MODULES.append(pybel_bridge)
	PYBEL_AVAILABLE = True


__all__ = allNames
