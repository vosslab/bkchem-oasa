#!/usr/bin/env python3
"""Build side-by-side HTML gallery comparing 2D coords from old, new, and RDKit generators.

For each test SMILES, renders atom positions from:
- OASA coords_generator (old)
- OASA coords_generator2 (new 3-layer)
- RDKit Compute2DCoords (if available)

Outputs an HTML gallery with SVG depictions for visual comparison.
"""

# Standard Library
import datetime
import html
import pathlib
import subprocess
import sys


#============================================
def get_repo_root() -> pathlib.Path:
	"""Return repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		raise RuntimeError("Could not detect repo root")
	return pathlib.Path(result.stdout.strip())


#============================================
def ensure_oasa_path(repo_root: pathlib.Path) -> None:
	"""Add OASA package to sys.path if needed."""
	oasa_path = str(repo_root / "packages" / "oasa")
	if oasa_path not in sys.path:
		sys.path.insert(0, oasa_path)


# test molecules: (name, SMILES)
TEST_MOLECULES = [
	("methane", "C"),
	("ethane", "CC"),
	("ethanol", "CCO"),
	("acetic acid", "CC(=O)O"),
	("propane", "CCC"),
	("butane", "CCCC"),
	("hexane", "CCCCCC"),
	("decane", "CCCCCCCCCC"),
	("cyclopentane", "C1CCCC1"),
	("benzene", "c1ccccc1"),
	("cyclohexane", "C1CCCCC1"),
	("toluene", "Cc1ccccc1"),
	("naphthalene", "c1ccc2ccccc2c1"),
	("anthracene", "c1ccc2cc3ccccc3cc2c1"),
	("phenanthrene", "c1ccc2c(c1)ccc3ccccc32"),
	("indane", "C1CC2CCCCC2C1"),
	("spiro[4.4]nonane", "C1CCC2(C1)CCCC2"),
	("acetylene", "C#C"),
	("propyne", "CC#C"),
	("isobutane", "CC(C)C"),
	("neopentane", "CC(C)(C)C"),
	("steroid skeleton", "C1CCC2C(C1)CCC3C2CCC4CCCC34"),
	("cubane", "C12C3C4C1C5C3C4C25"),
	("biphenyl", "c1ccc(-c2ccccc2)cc1"),
]


#============================================
def mol_to_svg(atoms_xy: list, bonds: list, width: int = 200,
	height: int = 200, label: str = "") -> str:
	"""Render atom coordinates as a simple SVG string.

	Args:
		atoms_xy: list of (x, y) tuples for each atom.
		bonds: list of (i, j) index pairs for bonds.
		width: SVG width.
		height: SVG height.
		label: text label for the SVG.
	"""
	if not atoms_xy or any(xy is None for xy in atoms_xy):
		return f"<svg width='{width}' height='{height}'><text x='10' y='20'>no coords</text></svg>"

	# find bounding box and scale
	xs = [xy[0] for xy in atoms_xy]
	ys = [xy[1] for xy in atoms_xy]
	min_x, max_x = min(xs), max(xs)
	min_y, max_y = min(ys), max(ys)
	dx = max_x - min_x if max_x != min_x else 1.0
	dy = max_y - min_y if max_y != min_y else 1.0
	margin = 20
	usable_w = width - 2 * margin
	usable_h = height - 2 * margin - 15  # room for label
	scale = min(usable_w / dx, usable_h / dy)

	# transform coords
	def tx(x: float) -> float:
		return margin + (x - min_x) * scale

	def ty(y: float) -> float:
		return margin + 15 + (y - min_y) * scale

	lines = []
	lines.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' "
		f"style='background:#fafafa;border:1px solid #ccc'>")
	if label:
		lines.append(f"<text x='{width // 2}' y='12' text-anchor='middle' "
			f"font-size='10' fill='#666'>{html.escape(label)}</text>")

	# draw bonds
	for i, j in bonds:
		x1, y1 = tx(atoms_xy[i][0]), ty(atoms_xy[i][1])
		x2, y2 = tx(atoms_xy[j][0]), ty(atoms_xy[j][1])
		lines.append(f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' "
			f"stroke='#333' stroke-width='1.5'/>")

	# draw atoms
	for x, y in atoms_xy:
		cx, cy = tx(x), ty(y)
		lines.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='3' fill='#2196F3'/>")

	lines.append("</svg>")
	return "\n".join(lines)


#============================================
def generate_old_coords(smiles_text: str) -> tuple:
	"""Generate coords using the old coords_generator."""
	import oasa.coords_generator as cg_old
	import oasa.smiles
	mol = oasa.smiles.text_to_mol(smiles_text, calc_coords=False)
	cg_old.calculate_coords(mol, bond_length=1.0, force=1)
	atoms_xy = []
	for a in mol.vertices:
		if a.x is not None and a.y is not None:
			atoms_xy.append((a.x, a.y))
		else:
			atoms_xy.append(None)
	# build bond index pairs
	bonds = []
	atom_list = list(mol.vertices)
	for b in mol.edges:
		a1, a2 = b.vertices
		bonds.append((atom_list.index(a1), atom_list.index(a2)))
	return atoms_xy, bonds


#============================================
def generate_new_coords(smiles_text: str) -> tuple:
	"""Generate coords using the new coords_generator2."""
	import oasa.coords_generator2 as cg_new
	import oasa.smiles
	mol = oasa.smiles.text_to_mol(smiles_text, calc_coords=False)
	cg_new.calculate_coords(mol, bond_length=1.0, force=1)
	atoms_xy = []
	for a in mol.vertices:
		if a.x is not None and a.y is not None:
			atoms_xy.append((a.x, a.y))
		else:
			atoms_xy.append(None)
	bonds = []
	atom_list = list(mol.vertices)
	for b in mol.edges:
		a1, a2 = b.vertices
		bonds.append((atom_list.index(a1), atom_list.index(a2)))
	return atoms_xy, bonds


#============================================
def generate_rdkit_coords(smiles_text: str) -> tuple:
	"""Generate coords using RDKit if available."""
	import rdkit.Chem
	import rdkit.Chem.AllChem
	mol = rdkit.Chem.MolFromSmiles(smiles_text)
	if mol is None:
		return None, None
	rdkit.Chem.AllChem.Compute2DCoords(mol)
	conf = mol.GetConformer()
	atoms_xy = []
	for i in range(mol.GetNumAtoms()):
		pos = conf.GetAtomPosition(i)
		atoms_xy.append((pos.x, pos.y))
	bonds = []
	for b in mol.GetBonds():
		bonds.append((b.GetBeginAtomIdx(), b.GetEndAtomIdx()))
	return atoms_xy, bonds


#============================================
def build_html(results: list, rdkit_available: bool) -> str:
	"""Build the HTML gallery page."""
	now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

	rows = []
	rows.append("<!DOCTYPE html>")
	rows.append("<html><head><meta charset='utf-8'>")
	rows.append("<title>2D Coords Comparison</title>")
	rows.append("<style>")
	rows.append("body { font-family: sans-serif; margin: 20px; }")
	rows.append("h1 { color: #333; }")
	rows.append("table { border-collapse: collapse; margin: 20px 0; }")
	rows.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }")
	rows.append("th { background: #f0f0f0; }")
	rows.append(".name { font-weight: bold; font-size: 13px; }")
	rows.append(".smiles { font-family: monospace; font-size: 11px; color: #666; }")
	rows.append("</style></head><body>")
	rows.append("<h1>2D Coordinate Generator Comparison</h1>")
	rows.append(f"<p>Generated {now}</p>")

	rows.append("<table>")
	header = "<tr><th>Molecule</th><th>Old (coords_generator)</th><th>New (coords_generator2)</th>"
	if rdkit_available:
		header += "<th>RDKit</th>"
	header += "</tr>"
	rows.append(header)

	for name, smiles_text, old_svg, new_svg, rdkit_svg in results:
		rows.append("<tr>")
		rows.append(f"<td><span class='name'>{html.escape(name)}</span><br>"
			f"<span class='smiles'>{html.escape(smiles_text)}</span></td>")
		rows.append(f"<td>{old_svg}</td>")
		rows.append(f"<td>{new_svg}</td>")
		if rdkit_available:
			rows.append(f"<td>{rdkit_svg}</td>")
		rows.append("</tr>")

	rows.append("</table></body></html>")
	return "\n".join(rows)


#============================================
def main():
	repo_root = get_repo_root()
	ensure_oasa_path(repo_root)

	# check RDKit availability
	rdkit_available = False
	try:
		__import__("rdkit.Chem")
		rdkit_available = True
	except ImportError:
		print("RDKit not available, skipping RDKit column")

	results = []
	for name, smiles_text in TEST_MOLECULES:
		print(f"  processing: {name} ({smiles_text})")

		# old generator
		try:
			old_xy, old_bonds = generate_old_coords(smiles_text)
			old_svg = mol_to_svg(old_xy, old_bonds, label="old")
		except Exception as exc:
			old_svg = f"<em>error: {html.escape(str(exc)[:60])}</em>"

		# new generator
		try:
			new_xy, new_bonds = generate_new_coords(smiles_text)
			new_svg = mol_to_svg(new_xy, new_bonds, label="new")
		except Exception as exc:
			new_svg = f"<em>error: {html.escape(str(exc)[:60])}</em>"

		# RDKit
		rdkit_svg = ""
		if rdkit_available:
			rdk_xy, rdk_bonds = generate_rdkit_coords(smiles_text)
			if rdk_xy:
				rdkit_svg = mol_to_svg(rdk_xy, rdk_bonds, label="RDKit")
			else:
				rdkit_svg = "<em>parse error</em>"

		results.append((name, smiles_text, old_svg, new_svg, rdkit_svg))

	# write output
	output_dir = repo_root / "output_smoke"
	output_dir.mkdir(exist_ok=True)
	output_path = output_dir / "coords_comparison.html"
	html_content = build_html(results, rdkit_available)
	with open(output_path, "w", encoding="utf-8") as fh:
		fh.write(html_content)
	print(f"Wrote: {output_path}")


#============================================
if __name__ == "__main__":
	main()
