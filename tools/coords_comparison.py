#!/usr/bin/env python3
"""Build side-by-side HTML gallery comparing 2D coords from old, new, and RDKit generators.

For each test SMILES, renders atom positions from:
- OASA coords_generator (old)
- OASA coords_generator2 (new 3-layer)
- RDKit Compute2DCoords (if available)

Outputs an HTML gallery with SVG depictions and a quality metrics summary table.
"""

# Standard Library
import datetime
import html
import math
import pathlib
import random
import signal
import subprocess
import sys
import time


# per-molecule timeout in seconds for coordinate generation
MOLECULE_TIMEOUT = 5


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
	("cubane", "C12C3C4C1C5C4C3C25"),
	("biphenyl", "c1ccc(-c2ccccc2)cc1"),
	("caffeine", "Cn1c(=O)c2[nH]cnc2n(C)c1=O"),
	("aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
	("ibuprofen", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"),
	("indole", "c1ccc2[nH]ccc2c1"),
	("purine", "c1ncc2[nH]cnc2n1"),
	("azulene", "c1cc2cccccc2c1"),
	("fluorene", "c1ccc2c(c1)-c1ccccc1C2"),
	("terphenyl", "c1ccc(-c2ccc(-c3ccccc3)cc2)cc1"),
	("adamantane", "C1C2CC3CC1CC(C2)C3"),
	("norbornane", "C1CC2CCC1C2"),

	# biological molecules
	("GTP", "C1=NC2=C(N1[C@H]3[C@@H]([C@@H]([C@H](O3)COP(=O)(O)OP(=O)(O)OP(=O)(O)O)O)O)N=C(NC2=O)N"),
	("ATP", "C1=NC(=C2C(=N1)N(C=N2)[C@H]3[C@@H]([C@@H]([C@H](O3)COP(=O)(O)OP(=O)(O)OP(=O)(O)O)O)O)N"),
	("NAD+", "C1=CC(=C[N+](=C1)[C@H]2[C@@H]([C@@H]([C@H](O2)COP(=O)(O)OP(=O)(O)OC[C@@H]3[C@H]([C@H]([C@@H](O3)N4C=NC5=C(N=CN=C54)N)O)O)O)O)C(=O)N"),
	("sucrose", "C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)O[C@]2([C@H]([C@@H]([C@H](O2)CO)O)O)CO)O)O)O)O"),
	("raffinose", "C([C@@H]1[C@@H]([C@@H]([C@H]([C@H](O1)OC[C@@H]2[C@H]([C@@H]([C@H]([C@H](O2)O[C@]3([C@H]([C@@H]([C@H](O3)CO)O)O)CO)O)O)O)O)O)O)O"),
	("tetraglycine", "C(C(=O)NCC(=O)NCC(=O)NCC(=O)O)N"),
	("Val-Gly-Ser-Glu", "CC(C)[C@@H](C(=O)NCC(=O)N[C@@H](CO)C(=O)N[C@@H](CCC(=O)O)C(=O)O)N "),
	("tryptophan", "C1=CC=C2C(=C1)C(=CN2)C[C@@H](C(=O)O)N"),
	("Porphyrin", "C1=CC2=CC3=CC=C(N3)C=C4C=CC(=N4)C=C5C=CC(=N5)C=C1N2"),
	("dihydroporphyrin", "CC1=C(C2=CC3=C(C(=C(N3)C=C4C(C(=O)C(=N4)C=C5C(C(=O)C(=N5)C=C1N2)(C)CC(=O)O)(C)CC(=O)O)C)/C=C/C(=O)O)CCC(=O)O"),
	("cholesterol", "C[C@H](CCCC(C)C)[C@H]1CC[C@@H]2[C@@]1(CC[C@H]3[C@H]2CC=C4[C@@]3(CC[C@@H](C4)O)C)C"),
	("testosterone", "C[C@]12CC[C@H]3[C@H]([C@@H]1CC[C@@H]2O)CCC4=CC(=O)CC[C@]34C"),
	("27-Hydroxycholesterol-d6", "[2H]C([2H])([2H])C([2H])(CCC[C@@H](C)[C@H]1CC[C@@H]2[C@@]1(CC[C@H]3[C@H]2CC=C4[C@@]3(CC[C@@H](C4)O)C)C)C([2H])([2H])O"),
]


# all 76 templates from ring_templates.py CXSMILES list
# each is (template_index, SMILES) extracted from the registered templates
TEMPLATE_MOLECULES = []


#============================================
def compute_bond_lengths(atoms_xy: list, bonds: list) -> list:
	"""Compute the Euclidean length of each bond.

	Args:
		atoms_xy: list of (x, y) tuples for each atom.
		bonds: list of (i, j) index pairs.

	Returns:
		List of bond length floats.
	"""
	lengths = []
	for i, j in bonds:
		dx = atoms_xy[i][0] - atoms_xy[j][0]
		dy = atoms_xy[i][1] - atoms_xy[j][1]
		dist = math.sqrt(dx * dx + dy * dy)
		lengths.append(dist)
	return lengths


#============================================
def compute_bond_length_variance(atoms_xy: list, bonds: list) -> float:
	"""Compute bond length variance: std dev / mean of all bond lengths.

	Args:
		atoms_xy: list of (x, y) tuples for each atom.
		bonds: list of (i, j) index pairs.

	Returns:
		Coefficient of variation (std/mean), or -1.0 if not enough bonds.
	"""
	lengths = compute_bond_lengths(atoms_xy, bonds)
	if len(lengths) < 2:
		return -1.0
	mean_len = sum(lengths) / len(lengths)
	if mean_len < 1e-9:
		return -1.0
	# compute std dev
	variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
	std_dev = math.sqrt(variance)
	return std_dev / mean_len


#============================================
def find_rings_from_bonds(bonds: list, num_atoms: int) -> list:
	"""Find small rings (size 3-8) using DFS-based cycle detection.

	Args:
		bonds: list of (i, j) index pairs.
		num_atoms: total number of atoms.

	Returns:
		List of rings, each ring is a list of atom indices in order.
	"""
	# build adjacency list
	adj = {}
	for i in range(num_atoms):
		adj[i] = []
	for a, b in bonds:
		adj[a].append(b)
		adj[b].append(a)

	rings = []
	# for each edge, try to find shortest path that completes a ring
	for start, end in bonds:
		# BFS from end to start, not using the direct edge
		visited = {end: None}
		queue = [end]
		found = False
		while queue and not found:
			next_queue = []
			for node in queue:
				for neighbor in adj[node]:
					if neighbor == start and node != end:
						# found a ring, trace back
						ring = [start]
						trace = node
						while trace is not None:
							ring.append(trace)
							trace = visited[trace]
						# only keep small rings (3-8 atoms)
						if 3 <= len(ring) <= 8:
							# normalize ring for deduplication
							min_idx = ring.index(min(ring))
							normalized = tuple(ring[min_idx:] + ring[:min_idx])
							rings.append(normalized)
						found = True
						break
					if neighbor not in visited and neighbor != start:
						visited[neighbor] = node
						next_queue.append(neighbor)
			queue = next_queue
			# limit BFS depth to ring size 8
			if len(visited) > num_atoms:
				break

	# deduplicate rings
	unique_rings = list(set(rings))
	return [list(r) for r in unique_rings]


#============================================
def compute_ring_regularity(atoms_xy: list, bonds: list) -> float:
	"""Compute ring regularity: max angle deviation from ideal for any ring.

	For each ring found, compute internal angles and compare to ideal
	angle of 180*(n-2)/n degrees. Return the max deviation in degrees.

	Args:
		atoms_xy: list of (x, y) tuples for each atom.
		bonds: list of (i, j) index pairs.

	Returns:
		Max angle deviation in degrees, or -1.0 if no rings found.
	"""
	num_atoms = len(atoms_xy)
	rings = find_rings_from_bonds(bonds, num_atoms)
	if not rings:
		return -1.0

	max_deviation = 0.0
	for ring in rings:
		n = len(ring)
		# ideal internal angle for a regular n-gon
		ideal_angle = 180.0 * (n - 2) / n
		for idx in range(n):
			# three consecutive atoms in the ring
			prev_atom = ring[(idx - 1) % n]
			curr_atom = ring[idx]
			next_atom = ring[(idx + 1) % n]

			# vectors from curr to prev and curr to next
			v1x = atoms_xy[prev_atom][0] - atoms_xy[curr_atom][0]
			v1y = atoms_xy[prev_atom][1] - atoms_xy[curr_atom][1]
			v2x = atoms_xy[next_atom][0] - atoms_xy[curr_atom][0]
			v2y = atoms_xy[next_atom][1] - atoms_xy[curr_atom][1]

			# compute angle using dot product
			dot = v1x * v2x + v1y * v2y
			mag1 = math.sqrt(v1x * v1x + v1y * v1y)
			mag2 = math.sqrt(v2x * v2x + v2y * v2y)
			if mag1 < 1e-9 or mag2 < 1e-9:
				continue
			cos_angle = dot / (mag1 * mag2)
			# clamp to [-1, 1] for numerical safety
			cos_angle = max(-1.0, min(1.0, cos_angle))
			angle_deg = math.degrees(math.acos(cos_angle))
			deviation = abs(angle_deg - ideal_angle)
			if deviation > max_deviation:
				max_deviation = deviation
	return max_deviation


#============================================
def compute_overlap_count(atoms_xy: list, bonds: list) -> int:
	"""Count non-bonded atom pairs closer than 0.4 * mean_bond_length.

	Args:
		atoms_xy: list of (x, y) tuples for each atom.
		bonds: list of (i, j) index pairs.

	Returns:
		Number of overlapping non-bonded atom pairs.
	"""
	lengths = compute_bond_lengths(atoms_xy, bonds)
	if not lengths:
		return 0
	mean_len = sum(lengths) / len(lengths)
	threshold = 0.4 * mean_len

	# build set of bonded pairs for quick lookup
	bonded = set()
	for i, j in bonds:
		bonded.add((min(i, j), max(i, j)))

	n = len(atoms_xy)
	count = 0
	for i in range(n):
		for j in range(i + 1, n):
			# skip bonded pairs
			pair = (i, j)
			if pair in bonded:
				continue
			dx = atoms_xy[i][0] - atoms_xy[j][0]
			dy = atoms_xy[i][1] - atoms_xy[j][1]
			dist = math.sqrt(dx * dx + dy * dy)
			if dist < threshold:
				count += 1
	return count


#============================================
def compute_quality_metrics(atoms_xy: list, bonds: list) -> dict:
	"""Compute all quality metrics for a set of coordinates.

	Args:
		atoms_xy: list of (x, y) tuples for each atom.
		bonds: list of (i, j) index pairs.

	Returns:
		Dict with keys: bond_var, ring_reg, overlaps.
		Values are None if coords are missing.
	"""
	if not atoms_xy or any(xy is None for xy in atoms_xy):
		return {"bond_var": None, "ring_reg": None, "overlaps": None}
	bond_var = compute_bond_length_variance(atoms_xy, bonds)
	ring_reg = compute_ring_regularity(atoms_xy, bonds)
	overlaps = compute_overlap_count(atoms_xy, bonds)
	return {"bond_var": bond_var, "ring_reg": ring_reg, "overlaps": overlaps}


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
class TimeoutError(Exception):
	"""Raised when a coordinate generation exceeds the time limit."""
	pass


#============================================
def _timeout_handler(signum: int, frame) -> None:
	"""Signal handler for SIGALRM timeout."""
	raise TimeoutError("coordinate generation timed out")


#============================================
def generate_old_coords(smiles_text: str) -> tuple:
	"""Generate coords using the old coords_generator.

	Returns:
		Tuple of (atoms_xy, bonds, elapsed_seconds).
	"""
	import oasa.coords_generator as cg_old
	import oasa.smiles_lib
	mol = oasa.smiles_lib.text_to_mol(smiles_text, calc_coords=False)
	t0 = time.time()
	signal.signal(signal.SIGALRM, _timeout_handler)
	signal.alarm(MOLECULE_TIMEOUT)
	cg_old.calculate_coords(mol, bond_length=1.0, force=1)
	signal.alarm(0)
	elapsed = time.time() - t0
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
	return atoms_xy, bonds, elapsed


#============================================
def generate_new_coords(smiles_text: str) -> tuple:
	"""Generate coords using the new coords_generator2.

	Returns:
		Tuple of (atoms_xy, bonds, elapsed_seconds).
	"""
	import oasa.coords_generator2 as cg_new
	import oasa.smiles_lib
	mol = oasa.smiles_lib.text_to_mol(smiles_text, calc_coords=False)
	t0 = time.time()
	signal.signal(signal.SIGALRM, _timeout_handler)
	signal.alarm(MOLECULE_TIMEOUT)
	cg_new.calculate_coords(mol, bond_length=1.0, force=1)
	signal.alarm(0)
	elapsed = time.time() - t0
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
	return atoms_xy, bonds, elapsed


#============================================
def generate_rdkit_coords(smiles_text: str) -> tuple:
	"""Generate coords using RDKit if available.

	Returns:
		Tuple of (atoms_xy, bonds, elapsed_seconds) or (None, None, 0).
	"""
	import rdkit.Chem
	import rdkit.Chem.AllChem
	mol = rdkit.Chem.MolFromSmiles(smiles_text)
	if mol is None:
		return None, None, 0.0
	t0 = time.time()
	# enable ring templates so RDKit uses its gold standard path
	# for cage molecules (cubane, adamantane, etc.)
	rdkit.Chem.AllChem.Compute2DCoords(mol, useRingTemplates=True)
	elapsed = time.time() - t0
	conf = mol.GetConformer()
	atoms_xy = []
	for i in range(mol.GetNumAtoms()):
		pos = conf.GetAtomPosition(i)
		atoms_xy.append((pos.x, pos.y))
	bonds = []
	for b in mol.GetBonds():
		bonds.append((b.GetBeginAtomIdx(), b.GetEndAtomIdx()))
	return atoms_xy, bonds, elapsed


#============================================
def format_metric_cell(value: float, is_overlap: bool = False) -> str:
	"""Format a single metric value for the summary table.

	Args:
		value: the metric value.
		is_overlap: True if this is an overlap count (integer).

	Returns:
		HTML string for the table cell content.
	"""
	if value is None:
		return "N/A"
	if value < 0:
		# -1 means not applicable (e.g., no rings or not enough bonds)
		return "-"
	if is_overlap:
		return str(int(value))
	return f"{value:.3f}"


#============================================
def format_time_cell(value: float) -> str:
	"""Format a render time value for the summary table.

	Args:
		value: elapsed time in seconds, or None if timed out / errored.

	Returns:
		HTML string for the table cell content.
	"""
	if value is None:
		return "<span style='color:red'>timeout</span>"
	if value < 0.001:
		return "<0.001"
	return f"{value:.3f}"


#============================================
def cell_color(bond_var: float, ring_reg: float, overlaps: int) -> str:
	"""Determine cell background color based on quality thresholds.

	Green if bond_var < 0.1 and ring_reg < 10 and overlaps == 0.
	Red otherwise. Returns empty string if metrics are unavailable.

	Args:
		bond_var: bond length coefficient of variation.
		ring_reg: max ring angle deviation in degrees.
		overlaps: number of overlapping atom pairs.

	Returns:
		CSS background-color string or empty string.
	"""
	if bond_var is None:
		return ""
	# treat -1 (not applicable) as passing for that metric
	bv_ok = (bond_var < 0 or bond_var < 0.1)
	rr_ok = (ring_reg < 0 or ring_reg < 10)
	ov_ok = (overlaps is not None and overlaps == 0)
	if bv_ok and rr_ok and ov_ok:
		return "background-color: #c8e6c9;"  # light green
	return "background-color: #ffcdd2;"  # light red


#============================================
def build_summary_table(results: list, rdkit_available: bool) -> str:
	"""Build the HTML summary metrics table.

	Args:
		results: list of result tuples from main processing.
		rdkit_available: whether RDKit column should be included.

	Returns:
		HTML string for the summary table.
	"""
	rows = []
	rows.append("<h2>Quality Metrics Summary</h2>")
	rows.append("<table>")

	# header row
	header = "<tr>"
	header += "<th rowspan='2'>Molecule</th>"
	header += "<th rowspan='2'>SMILES</th>"
	header += "<th colspan='4'>Old (coords_generator)</th>"
	header += "<th colspan='4'>New (coords_generator2)</th>"
	if rdkit_available:
		header += "<th colspan='4'>RDKit</th>"
	header += "</tr>"
	rows.append(header)

	# sub-header row with metric names
	sub_header = "<tr>"
	sub_header += "<th>bond_var</th><th>ring_reg</th><th>overlaps</th><th>time(s)</th>"
	sub_header += "<th>bond_var</th><th>ring_reg</th><th>overlaps</th><th>time(s)</th>"
	if rdkit_available:
		sub_header += "<th>bond_var</th><th>ring_reg</th><th>overlaps</th><th>time(s)</th>"
	sub_header += "</tr>"
	rows.append(sub_header)

	# data rows
	for entry in results:
		name = entry["name"]
		smiles_text = entry["smiles"]
		old_m = entry["old_metrics"]
		new_m = entry["new_metrics"]
		rdk_m = entry.get("rdkit_metrics", {})

		row = "<tr>"
		row += f"<td class='name'>{html.escape(name)}</td>"
		row += f"<td class='smiles'>{html.escape(smiles_text)}</td>"

		# old metrics cells
		old_color = cell_color(old_m.get("bond_var"), old_m.get("ring_reg"), old_m.get("overlaps"))
		style_attr = f" style='{old_color}'" if old_color else ""
		row += f"<td{style_attr}>{format_metric_cell(old_m.get('bond_var'))}</td>"
		row += f"<td{style_attr}>{format_metric_cell(old_m.get('ring_reg'))}</td>"
		row += f"<td{style_attr}>{format_metric_cell(old_m.get('overlaps'), is_overlap=True)}</td>"
		row += f"<td>{format_time_cell(entry.get('old_time'))}</td>"

		# new metrics cells
		new_color = cell_color(new_m.get("bond_var"), new_m.get("ring_reg"), new_m.get("overlaps"))
		style_attr = f" style='{new_color}'" if new_color else ""
		row += f"<td{style_attr}>{format_metric_cell(new_m.get('bond_var'))}</td>"
		row += f"<td{style_attr}>{format_metric_cell(new_m.get('ring_reg'))}</td>"
		row += f"<td{style_attr}>{format_metric_cell(new_m.get('overlaps'), is_overlap=True)}</td>"
		row += f"<td>{format_time_cell(entry.get('new_time'))}</td>"

		# rdkit metrics cells
		if rdkit_available:
			rdk_color = cell_color(rdk_m.get("bond_var"), rdk_m.get("ring_reg"), rdk_m.get("overlaps"))
			style_attr = f" style='{rdk_color}'" if rdk_color else ""
			row += f"<td{style_attr}>{format_metric_cell(rdk_m.get('bond_var'))}</td>"
			row += f"<td{style_attr}>{format_metric_cell(rdk_m.get('ring_reg'))}</td>"
			row += f"<td{style_attr}>{format_metric_cell(rdk_m.get('overlaps'), is_overlap=True)}</td>"
			row += f"<td>{format_time_cell(entry.get('rdkit_time'))}</td>"

		row += "</tr>"
		rows.append(row)

	rows.append("</table>")
	return "\n".join(rows)


#============================================
def build_svg_gallery(results: list, rdkit_available: bool) -> str:
	"""Build the HTML SVG gallery table.

	Args:
		results: list of result dicts from main processing.
		rdkit_available: whether RDKit column should be included.

	Returns:
		HTML string for the SVG gallery table.
	"""
	rows = []
	rows.append("<h2>SVG Gallery</h2>")
	rows.append("<table>")
	header = "<tr><th>Molecule</th><th>Old (coords_generator)</th><th>New (coords_generator2)</th>"
	if rdkit_available:
		header += "<th>RDKit</th>"
	header += "</tr>"
	rows.append(header)

	for entry in results:
		name = entry["name"]
		smiles_text = entry["smiles"]
		old_svg = entry["old_svg"]
		new_svg = entry["new_svg"]
		rdkit_svg = entry.get("rdkit_svg", "")

		rows.append("<tr>")
		rows.append(f"<td><span class='name'>{html.escape(name)}</span><br>"
			f"<span class='smiles'>{html.escape(smiles_text)}</span></td>")
		rows.append(f"<td>{old_svg}</td>")
		rows.append(f"<td>{new_svg}</td>")
		if rdkit_available:
			rows.append(f"<td>{rdkit_svg}</td>")
		rows.append("</tr>")

	rows.append("</table>")
	return "\n".join(rows)


#============================================
def build_html(results: list, rdkit_available: bool) -> str:
	"""Build the full HTML page with summary table and SVG gallery.

	Args:
		results: list of result dicts from main processing.
		rdkit_available: whether RDKit column should be included.

	Returns:
		Complete HTML page as a string.
	"""
	now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

	rows = []
	rows.append("<!DOCTYPE html>")
	rows.append("<html><head><meta charset='utf-8'>")
	rows.append("<title>2D Coords Comparison</title>")
	rows.append("<style>")
	rows.append("body { font-family: sans-serif; margin: 20px; }")
	rows.append("h1 { color: #333; }")
	rows.append("h2 { color: #555; margin-top: 30px; }")
	rows.append("table { border-collapse: collapse; margin: 20px 0; }")
	rows.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }")
	rows.append("th { background: #f0f0f0; }")
	rows.append(".name { font-weight: bold; font-size: 13px; }")
	rows.append(".smiles { font-family: monospace; font-size: 11px; color: #666; }")
	rows.append("</style></head><body>")
	rows.append("<h1>2D Coordinate Generator Comparison</h1>")
	rows.append(f"<p>Generated {now}</p>")

	# summary metrics table at top
	rows.append(build_summary_table(results, rdkit_available))

	# SVG gallery below
	rows.append(build_svg_gallery(results, rdkit_available))

	rows.append("</body></html>")
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

	# build template molecule list from ring_templates CXSMILES entries
	import oasa.coords_gen.ring_templates as rt
	subtemplates = random.sample(rt._TEMPLATES, 10)
	for idx, tmpl in enumerate(subtemplates):
		smiles_text = tmpl["name"]
		label = f"template {idx + 1}: {smiles_text[:40]}"
		TEMPLATE_MOLECULES.append((label, smiles_text))

	# combine both molecule lists
	all_molecules = list(TEST_MOLECULES) + list(TEMPLATE_MOLECULES)

	results = []
	for name, smiles_text in all_molecules:
		print(f"  processing: {name} ({smiles_text})")
		entry = {"name": name, "smiles": smiles_text}

		# old generator
		old_xy = None
		old_bonds = []
		try:
			old_xy, old_bonds, old_time = generate_old_coords(smiles_text)
			entry["old_svg"] = mol_to_svg(old_xy, old_bonds, label="old")
			entry["old_metrics"] = compute_quality_metrics(old_xy, old_bonds)
			entry["old_time"] = old_time
		except Exception as exc:
			signal.alarm(0)
			entry["old_svg"] = f"<em>error: {html.escape(str(exc)[:60])}</em>"
			entry["old_metrics"] = {"bond_var": None, "ring_reg": None, "overlaps": None}
			entry["old_time"] = None

		# new generator
		new_xy = None
		new_bonds = []
		try:
			new_xy, new_bonds, new_time = generate_new_coords(smiles_text)
			entry["new_svg"] = mol_to_svg(new_xy, new_bonds, label="new")
			entry["new_metrics"] = compute_quality_metrics(new_xy, new_bonds)
			entry["new_time"] = new_time
		except Exception as exc:
			signal.alarm(0)
			entry["new_svg"] = f"<em>error: {html.escape(str(exc)[:60])}</em>"
			entry["new_metrics"] = {"bond_var": None, "ring_reg": None, "overlaps": None}
			entry["new_time"] = None

		# RDKit
		if rdkit_available:
			rdk_xy, rdk_bonds, rdk_time = generate_rdkit_coords(smiles_text)
			if rdk_xy:
				entry["rdkit_svg"] = mol_to_svg(rdk_xy, rdk_bonds, label="RDKit")
				entry["rdkit_metrics"] = compute_quality_metrics(rdk_xy, rdk_bonds)
				entry["rdkit_time"] = rdk_time
			else:
				entry["rdkit_svg"] = "<em>parse error</em>"
				entry["rdkit_metrics"] = {"bond_var": None, "ring_reg": None, "overlaps": None}
				entry["rdkit_time"] = None
		else:
			entry["rdkit_svg"] = ""
			entry["rdkit_metrics"] = {}
			entry["rdkit_time"] = None

		results.append(entry)

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
