#!/usr/bin/env python3
#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program
#
#--------------------------------------------------------------------------

# Standard Library
import argparse
import os

# local repo modules
import oasa


DEFAULT_SMILES = "C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)O)O)O)O)O"
DEFAULT_NAME = "alpha-d-glucopyranose"


#============================================
def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Render a SMILES string to a PNG using OASA.",
	)
	parser.add_argument(
		'-s', '--smiles',
		dest='smiles_text',
		default=DEFAULT_SMILES,
		help="SMILES string to render.",
	)
	parser.add_argument(
		'-o', '--output',
		dest='output_path',
		default="smoke.png",
		help="Output path for the rendered image.",
	)
	parser.add_argument(
		'-f', '--format',
		dest='output_format',
		choices=('png', 'pdf', 'svg'),
		help="Output format override (png, pdf, svg).",
	)
	args = parser.parse_args()
	return args


#============================================
def ensure_parent_dir(path):
	"""Create output directory if needed."""
	parent = os.path.dirname(os.path.abspath(path))
	if parent and not os.path.isdir(parent):
		os.makedirs(parent, exist_ok=True)


#============================================
def build_molecule(smiles_text):
	"""Convert SMILES to an OASA molecule with coordinates."""
	mol = oasa.smiles.text_to_mol(smiles_text, calc_coords=False)
	if not mol:
		raise ValueError("SMILES could not be parsed into a molecule.")
	oasa.coords_generator.calculate_coords(mol, force=1)
	mol.normalize_bond_length(30)
	mol.remove_unimportant_hydrogens()
	return mol


#============================================
def resolve_format(output_path, output_format):
	"""Infer format from the extension unless explicitly set."""
	if output_format:
		return output_format
	ext = os.path.splitext(output_path)[1].lower()
	if ext in ('.png', '.pdf', '.svg'):
		return ext[1:]
	return None


#============================================
def render_molecule(mol, output_path, output_format):
	"""Render the molecule using the cairo backend."""
	if not oasa.CAIRO_AVAILABLE:
		raise RuntimeError("Cairo backend not available. Install pycairo to render.")
	from oasa import cairo_out
	renderer = cairo_out.cairo_out(color_bonds=True, color_atoms=True)
	renderer.show_hydrogens_on_hetero = True
	renderer.font_size = 20
	mols = list(mol.get_disconnected_subgraphs())
	if output_format:
		renderer.mols_to_cairo(mols, output_path, format=output_format)
	else:
		renderer.mols_to_cairo(mols, output_path)


#============================================
def main():
	args = parse_args()
	ensure_parent_dir(args.output_path)
	mol = build_molecule(args.smiles_text)
	output_format = resolve_format(args.output_path, args.output_format)
	render_molecule(mol, args.output_path, output_format)
	print(f"Rendered {DEFAULT_NAME} to {args.output_path}")


if __name__ == '__main__':
	main()
