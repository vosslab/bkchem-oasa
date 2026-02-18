#!/usr/bin/env python3

"""Render an OASA molecule to multiple formats for smoke testing."""

# Standard Library
import argparse
import os
import tempfile

import oasa


DEFAULT_SMILES = "C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)O)O)O)O)O"
DEFAULT_NAME = "alpha-d-glucopyranose"


#============================================
def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Render a SMILES string to SVG, PDF, and PNG formats using OASA."
	)
	parser.add_argument(
		'-s', '--smiles',
		dest='smiles_text',
		default=DEFAULT_SMILES,
		help="SMILES string to render.",
	)
	parser.add_argument(
		'-o', '--output-dir',
		dest='output_dir',
		default=None,
		help="Output directory for rendered files.",
	)
	parser.add_argument(
		'--low-scale',
		dest='low_scale',
		type=float,
		default=1.0,
		help="Scaling factor for low-resolution PNG.",
	)
	parser.add_argument(
		'--high-scale',
		dest='high_scale',
		type=float,
		default=3.0,
		help="Scaling factor for high-resolution PNG.",
	)
	args = parser.parse_args()
	return args


#============================================
def ensure_dir(path):
	"""Ensure output directory exists."""
	if not os.path.isdir(path):
		os.makedirs(path, exist_ok=True)


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
def render_format(mols, output_path, file_format, scale):
	"""Render molecules to a single output file."""
	if not oasa.CAIRO_AVAILABLE:
		raise RuntimeError("Cairo backend not available. Install pycairo to render.")
	from oasa import cairo_out
	renderer = cairo_out.cairo_out(color_bonds=True, color_atoms=True, scaling=scale)
	renderer.show_hydrogens_on_hetero = True
	renderer.font_size = 20
	renderer.mols_to_cairo(mols, output_path, format=file_format)


#============================================
def main():
	args = parse_args()
	output_dir = args.output_dir
	if output_dir is None:
		output_dir = tempfile.mkdtemp(prefix="oasa_smoke_")
	ensure_dir(output_dir)

	mol = build_molecule(args.smiles_text)
	mols = list(mol.get_disconnected_subgraphs())

	outputs = [
		("svg", os.path.join(output_dir, "oasa_smoke.svg"), 1.0),
		("pdf", os.path.join(output_dir, "oasa_smoke.pdf"), 1.0),
		("png", os.path.join(output_dir, "oasa_smoke_low.png"), args.low_scale),
		("png", os.path.join(output_dir, "oasa_smoke_high.png"), args.high_scale),
	]

	for file_format, output_path, scale in outputs:
		render_format(mols, output_path, file_format, scale)
		if not os.path.isfile(output_path):
			raise RuntimeError(f"Missing output file: {output_path}")
		if os.path.getsize(output_path) == 0:
			raise RuntimeError(f"Empty output file: {output_path}")

	print(f"Rendered {DEFAULT_NAME} to {output_dir}")


if __name__ == '__main__':
	main()
