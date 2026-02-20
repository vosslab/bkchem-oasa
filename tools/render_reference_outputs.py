#!/usr/bin/env python3

"""Render reference SVG/PNG outputs for Haworth."""

# Standard Library
import argparse
import os
import subprocess
import sys


def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Render reference SVG/PNG outputs for Haworth."
	)
	parser.add_argument(
		'-o', '--output-dir',
		dest='output_dir',
		default=None,
		help="Output directory for reference files.",
	)
	args = parser.parse_args()
	return args


#============================================
def _get_repo_root():
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
	)
	if result.returncode == 0:
		return result.stdout.strip()
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


#============================================
def _ensure_sys_path(repo_root):
	oasa_dir = os.path.join(repo_root, "packages", "oasa")
	if oasa_dir not in sys.path:
		sys.path.insert(0, oasa_dir)


#============================================
def _ensure_dir(path):
	if not os.path.isdir(path):
		os.makedirs(path, exist_ok=True)


#============================================
def _build_ring(size, oxygen_index=None):
	import oasa
	import oasa.atom_lib
	import oasa.bond_lib
	import oasa.molecule_lib

	mol = oasa.molecule_lib.Molecule()
	atoms = []
	for idx in range(size):
		symbol = 'C'
		if oxygen_index is not None and idx == oxygen_index:
			symbol = 'O'
		atom = oasa.atom_lib.Atom(symbol=symbol)
		atom.x = idx * 20
		atom.y = 0
		mol.add_vertex(atom)
		atoms.append(atom)
	for idx in range(size):
		bond = oasa.bond_lib.Bond(order=1, type='n')
		v1 = atoms[idx]
		v2 = atoms[(idx + 1) % size]
		bond.vertices = (v1, v2)
		mol.add_edge(v1, v2, bond)
	return mol


#============================================
def _build_haworth_reference():
	from oasa.haworth import layout as haworth_layout

	pyranose = _build_ring(6, oxygen_index=0)
	haworth_layout.build_haworth(pyranose, mode="pyranose")

	furanose = _build_ring(5, oxygen_index=0)
	haworth_layout.build_haworth(furanose, mode="furanose")

	max_x = max(atom.x for atom in pyranose.vertices)
	min_x = min(atom.x for atom in pyranose.vertices)
	offset = (max_x - min_x) + 50.0
	for atom in furanose.vertices:
		atom.x += offset
	pyranose.insert_a_graph(furanose)
	return pyranose


#============================================
def _render_svg(mol, path):
	import oasa.svg_out

	renderer = oasa.svg_out.svg_out()
	doc = renderer.mol_to_svg(mol)
	with open(path, "wb") as handle:
		handle.write(doc.toxml("utf-8"))


#============================================
def _render_png(mol, path, scaling=3.0):
	import oasa.cairo_out

	oasa.cairo_out.mol_to_cairo(mol, path, format="png", scaling=scaling)


#============================================
def _flip_y(mol):
	for atom in mol.vertices:
		atom.y = -atom.y


#============================================
def render_reference_outputs(output_dir):
	# Haworth reference output
	haworth_svg = os.path.join(output_dir, "haworth_reference.svg")
	haworth_png = os.path.join(output_dir, "haworth_reference.png")
	haworth_mol = _build_haworth_reference()
	_render_svg(haworth_mol, haworth_svg)
	haworth_png_mol = _build_haworth_reference()
	_flip_y(haworth_png_mol)
	_render_png(haworth_png_mol, haworth_png)


#============================================
def main():
	args = parse_args()
	repo_root = _get_repo_root()
	_ensure_sys_path(repo_root)
	output_dir = args.output_dir or os.path.join(repo_root, "docs", "reference_outputs")
	_ensure_dir(output_dir)
	render_reference_outputs(output_dir)
	print("Reference outputs written to %s" % output_dir)


if __name__ == "__main__":
	main()
