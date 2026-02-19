#!/usr/bin/env python3

"""Build parallel and antiparallel beta-sheet molecules and render to SVG/CDML.

Writes bkchem-compatible CDML directly (not through oasa.cdml_writer) to
produce proper element types: <atom>, <query>, <group>, <text>.  Also builds
oasa.molecule objects for SVG rendering via render_out.render_to_svg().
"""

# Standard Library
import math
import os
import subprocess
import sys
import xml.dom.minidom as minidom


#============================================
# Geometry constants in cm (from bkchem reference template)
BOND_LENGTH_CM = 0.700
DX_CM = BOND_LENGTH_CM * math.cos(math.radians(30))
DY_CM = BOND_LENGTH_CM * math.sin(math.radians(30))
SIDE_OFFSET_CM = BOND_LENGTH_CM
# Conversion factor: 1 cm = 72/2.54 points
POINTS_PER_CM = 72.0 / 2.54
# Vertical separation between strand baselines (cm)
STRAND_SEP_CM = 3.0
# Starting position for first Ca atom (cm)
X_START_CM = 4.600
Y_BASE1_CM = 2.500
Y_BASE2_CM = Y_BASE1_CM + STRAND_SEP_CM
# Residues per strand
NUM_RESIDUES = 4


#============================================
def _get_repo_root() -> str:
	"""Return the repository root directory."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
	)
	if result.returncode == 0:
		return result.stdout.strip()
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


#============================================
def _ensure_sys_path(repo_root: str):
	"""Add oasa package directory to sys.path."""
	oasa_dir = os.path.join(repo_root, "packages", "oasa")
	if oasa_dir not in sys.path:
		sys.path.insert(0, oasa_dir)


#============================================
def _ensure_dir(path: str):
	"""Create directory if it does not exist."""
	if not os.path.isdir(path):
		os.makedirs(path, exist_ok=True)


#============================================
def _build_strand_atoms(x_start: float, y_base: float,
	num_residues: int, direction: int = 1,
	id_offset: int = 0) -> tuple:
	"""Compute coordinate dicts for one strand's atoms and side groups.

	Backbone per residue is Ca - C'(=O) - N, repeating left-to-right (or
	right-to-left for direction=-1).  Terminal labels are direction-aware:
	for direction=1 use H3N+/COO-, for direction=-1 use NH3+/-OOC.

	Args:
		x_start: x coordinate of first Ca atom (cm)
		y_base: baseline y coordinate for UP zigzag atoms (cm)
		num_residues: number of amino acid residues
		direction: +1 for left-to-right, -1 for right-to-left
		id_offset: starting atom ID counter

	Returns:
		tuple of (atoms_list, bonds_list, final_id_counter)
	"""
	atoms = []
	bonds = []
	atom_counter = id_offset
	# 10 backbone atoms for 4 residues: Ca-C'-N-Ca-C'-N-Ca-C'-N-Ca
	backbone_count = (num_residues - 1) * 3 + 1
	backbone_ids = []

	for i in range(backbone_count):
		atom_counter += 1
		# zigzag: even indices UP (y_base), odd indices DOWN (y_base + dy)
		if i % 2 == 0:
			y = y_base
		else:
			y = y_base + DY_CM
		x = x_start + i * direction * DX_CM

		# atom type by position within each residue triplet
		local = i % 3
		if local == 0:
			# Ca (alpha carbon)
			symbol = 'C'
			pos = None
			valency = 4
		elif local == 1:
			# C' (carbonyl carbon)
			symbol = 'C'
			pos = None
			valency = 4
		else:
			# N (backbone nitrogen)
			symbol = 'N'
			pos = 'center-first'
			valency = 3

		aid = "a%d" % atom_counter
		atoms.append({
			'id': aid, 'kind': 'atom', 'name': symbol,
			'symbol': symbol, 'x': x, 'y': y,
			'pos': pos, 'valency': valency,
			'label': None, 'ftext': None,
		})
		backbone_ids.append(aid)

		# side group on Ca: R query element
		if local == 0:
			atom_counter += 1
			# extends away from zigzag center
			if i % 2 == 0:
				r_y = y - SIDE_OFFSET_CM
			else:
				r_y = y + SIDE_OFFSET_CM
			r_aid = "a%d" % atom_counter
			atoms.append({
				'id': r_aid, 'kind': 'query', 'name': 'R',
				'symbol': 'C', 'x': x, 'y': r_y,
				'pos': 'center-first', 'valency': None,
				'label': 'R', 'ftext': None,
			})
			bonds.append({
				'start': aid, 'end': r_aid,
				'type': 'n1', 'center': False,
			})

		# side group on C': carbonyl O with double bond
		elif local == 1:
			atom_counter += 1
			# extends away from zigzag center (same direction as C')
			if i % 2 == 0:
				o_y = y - SIDE_OFFSET_CM
			else:
				o_y = y + SIDE_OFFSET_CM
			o_aid = "a%d" % atom_counter
			atoms.append({
				'id': o_aid, 'kind': 'atom', 'name': 'O',
				'symbol': 'O', 'x': x, 'y': o_y,
				'pos': 'center-first', 'valency': 2,
				'label': None, 'ftext': None,
			})
			bonds.append({
				'start': aid, 'end': o_aid,
				'type': 'n2', 'center': True,
			})

	# backbone bonds between consecutive backbone atoms
	for i in range(len(backbone_ids) - 1):
		bonds.append({
			'start': backbone_ids[i], 'end': backbone_ids[i + 1],
			'type': 'n1', 'center': False,
		})

	# N-terminus text element with circled plus mark, one step behind Ca1.
	# Reverse strands use NH3 so the C->N read direction is left-to-right.
	atom_counter += 1
	h3n_x = x_start - direction * DX_CM
	# virtual index -1 is odd -> DOWN position
	h3n_y = y_base + DY_CM
	h3n_aid = "a%d" % atom_counter
	if direction == 1:
		n_term_name = 'H3N'
		n_term_ftext = 'H<sub>3</sub>N'
		n_term_pos = 'center-last'
	else:
		n_term_name = 'NH3'
		n_term_ftext = 'NH<sub>3</sub>'
		n_term_pos = 'center-first'
	# charge rendered via bkchem circled mark, not text
	# mark offset: slight right, away from backbone (down for DOWN atom)
	atoms.append({
		'id': h3n_aid, 'kind': 'text', 'name': n_term_name,
		'symbol': 'N', 'x': h3n_x, 'y': h3n_y,
		'pos': n_term_pos, 'valency': None,
		'charge': 1,
		'label': n_term_ftext,
		'ftext': n_term_ftext,
		'marks': [{'type': 'plus', 'x': h3n_x + 0.107, 'y': h3n_y + 0.398}],
	})
	bonds.append({
		'start': h3n_aid, 'end': backbone_ids[0],
		'type': 'n1', 'center': False,
	})

	# C-terminus text element with circled minus mark, one step ahead of last Ca.
	# Reverse strands use OOC with a leading minus (-OOC).
	atom_counter += 1
	last_bb_idx = backbone_count - 1
	last_x = x_start + last_bb_idx * direction * DX_CM
	coo_x = last_x + direction * DX_CM
	# virtual index = backbone_count: zigzag alternates from last atom
	if backbone_count % 2 == 0:
		coo_y = y_base
		# mark goes above for UP atom
		mark_dy = -0.398
	else:
		coo_y = y_base + DY_CM
		# mark goes below for DOWN atom
		mark_dy = 0.398
	coo_aid = "a%d" % atom_counter
	if direction == 1:
		c_term_name = 'COO'
		c_term_ftext = 'COO'
		c_term_pos = 'center-first'
		mark_dx = 0.107
	else:
		c_term_name = 'OOC'
		c_term_ftext = 'OOC'
		c_term_pos = 'center-last'
		mark_dx = -0.107
	# charge rendered via bkchem circled mark, not text
	atoms.append({
		'id': coo_aid, 'kind': 'text', 'name': c_term_name,
		'symbol': 'C', 'x': coo_x, 'y': coo_y,
		'pos': c_term_pos, 'valency': None,
		'charge': -1,
		'label': c_term_ftext,
		'ftext': c_term_ftext,
		'marks': [{'type': 'minus', 'x': coo_x + mark_dx, 'y': coo_y + mark_dy}],
	})
	bonds.append({
		'start': backbone_ids[-1], 'end': coo_aid,
		'type': 'n1', 'center': False,
	})

	return atoms, bonds, atom_counter


#============================================
def _write_cdml_strand(doc, mol_el, atoms: list, bonds: list,
	bond_offset: int = 0) -> int:
	"""Write bkchem CDML XML elements for one strand into a molecule element.

	Args:
		doc: xml.dom.minidom Document
		mol_el: molecule Element to append to
		atoms: list of atom dicts from _build_strand_atoms
		bonds: list of bond dicts from _build_strand_atoms
		bond_offset: starting bond ID counter

	Returns:
		updated bond counter after all bonds written
	"""
	for atom in atoms:
		kind = atom['kind']
		if kind == 'text':
			# bkchem <text> element with <ftext> child for markup labels
			el = doc.createElement('text')
			el.setAttribute('id', atom['id'])
			if atom['pos']:
				el.setAttribute('pos', atom['pos'])
			ftext_el = doc.createElement('ftext')
			# minidom escapes <sub> to &lt;sub&gt; automatically
			ftext_el.appendChild(doc.createTextNode(atom['ftext']))
			el.appendChild(ftext_el)
		elif kind == 'query':
			# bkchem <query> element for R groups
			el = doc.createElement('query')
			el.setAttribute('id', atom['id'])
			if atom['pos']:
				el.setAttribute('pos', atom['pos'])
			el.setAttribute('name', atom['name'])
		elif kind == 'group':
			# bkchem <group> element for builtin groups like COOH
			el = doc.createElement('group')
			el.setAttribute('id', atom['id'])
			if atom['pos']:
				el.setAttribute('pos', atom['pos'])
			el.setAttribute('group-type', 'builtin')
			el.setAttribute('name', atom['name'])
		else:
			# standard <atom> element for C, N, O backbone atoms
			el = doc.createElement('atom')
			el.setAttribute('id', atom['id'])
			if atom['pos']:
				el.setAttribute('pos', atom['pos'])
			el.setAttribute('name', atom['name'])
			if atom['valency'] is not None:
				el.setAttribute('valency', str(atom['valency']))

		# <point> child with cm coordinates
		pt = doc.createElement('point')
		pt.setAttribute('x', '%.3fcm' % atom['x'])
		pt.setAttribute('y', '%.3fcm' % atom['y'])
		el.appendChild(pt)

		# <mark> children for charge marks (circled +/-)
		for mark_data in atom.get('marks', []):
			mk = doc.createElement('mark')
			mk.setAttribute('type', mark_data['type'])
			mk.setAttribute('x', '%.3fcm' % mark_data['x'])
			mk.setAttribute('y', '%.3fcm' % mark_data['y'])
			mk.setAttribute('auto', '1')
			mk.setAttribute('size', '10')
			mk.setAttribute('draw_circle', 'yes')
			el.appendChild(mk)

		mol_el.appendChild(el)

	# bond elements matching bkchem template attributes
	for i, bond in enumerate(bonds):
		bond_id = bond_offset + i + 1
		bel = doc.createElement('bond')
		bel.setAttribute('type', bond['type'])
		bel.setAttribute('start', bond['start'])
		bel.setAttribute('end', bond['end'])
		bel.setAttribute('id', 'b%d' % bond_id)
		bel.setAttribute('line_width', '1.0')
		bel.setAttribute('double_ratio', '0.75')
		if bond['center']:
			bel.setAttribute('bond_width', '6.0')
			bel.setAttribute('center', 'yes')
		mol_el.appendChild(bel)

	return bond_offset + len(bonds)


#============================================
def _write_cdml_file(strand_data: list, path: str):
	"""Write full bkchem CDML document with multiple strands.

	Produces proper bkchem CDML with <standard>, <paper>, <viewport>
	boilerplate matching the reference template geometry.

	Args:
		strand_data: list of (atoms, bonds) tuples, one per strand
		path: output CDML file path
	"""
	doc = minidom.Document()

	# root <cdml> element
	root = doc.createElement('cdml')
	root.setAttribute('version', '26.02')
	root.setAttribute('xmlns', 'http://www.freesoftware.fsf.org/bkchem/cdml')
	doc.appendChild(root)

	# <info> block
	info_el = doc.createElement('info')
	author_el = doc.createElement('author_program')
	author_el.setAttribute('version', '26.02')
	author_el.appendChild(doc.createTextNode('BKChem'))
	info_el.appendChild(author_el)
	root.appendChild(info_el)

	# <metadata> block
	meta_el = doc.createElement('metadata')
	doc_el = doc.createElement('doc')
	doc_el.setAttribute('href',
		'https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md')
	meta_el.appendChild(doc_el)
	root.appendChild(meta_el)

	# <paper> element
	paper_el = doc.createElement('paper')
	for key, val in [('type', 'A4'), ('orientation', 'portrait'),
		('crop_svg', '0'), ('crop_margin', '10'),
		('use_real_minus', '0'), ('replace_minus', '0')]:
		paper_el.setAttribute(key, val)
	root.appendChild(paper_el)

	# <viewport> element
	vp_el = doc.createElement('viewport')
	vp_el.setAttribute('viewport', '0.000000 0.000000 640.000000 480.000000')
	root.appendChild(vp_el)

	# <standard> element with bond/arrow/atom defaults
	std_el = doc.createElement('standard')
	for key, val in [('line_width', '1px'), ('font_size', '12'),
		('font_family', 'helvetica'), ('line_color', '#000'),
		('area_color', ''), ('paper_type', 'A4'),
		('paper_orientation', 'portrait'), ('paper_crop_svg', '0'),
		('paper_crop_margin', '10')]:
		std_el.setAttribute(key, val)
	# bond defaults
	bond_std = doc.createElement('bond')
	for key, val in [('length', '0.7cm'), ('width', '6px'),
		('wedge-width', '5px'), ('double-ratio', '0.75'),
		('min_wedge_angle', '0.39269908169872414')]:
		bond_std.setAttribute(key, val)
	std_el.appendChild(bond_std)
	# arrow default
	arrow_std = doc.createElement('arrow')
	arrow_std.setAttribute('length', '1.6cm')
	std_el.appendChild(arrow_std)
	# atom default
	atom_std = doc.createElement('atom')
	atom_std.setAttribute('show_hydrogens', '0')
	std_el.appendChild(atom_std)
	root.appendChild(std_el)

	# one <molecule> per strand
	bond_counter = 0
	for strand_idx, (atoms, bonds) in enumerate(strand_data):
		mol_el = doc.createElement('molecule')
		mol_el.setAttribute('id', 'molecule%d' % (strand_idx + 1))
		bond_counter = _write_cdml_strand(
			doc, mol_el, atoms, bonds, bond_counter)
		root.appendChild(mol_el)

	# serialize XML to file
	xml_str = doc.toxml('utf-8').decode('utf-8')
	with open(path, 'w', encoding='utf-8') as handle:
		handle.write(xml_str)
		handle.write('\n')


#============================================
def _build_oasa_strand(mol, atoms: list, bonds: list) -> dict:
	"""Add oasa atoms and bonds to molecule for one strand.

	Args:
		mol: oasa.molecule to add atoms/bonds to
		atoms: list of atom dicts from _build_strand_atoms
		bonds: list of bond dicts from _build_strand_atoms

	Returns:
		dict mapping atom ID strings to oasa.atom objects
	"""
	import oasa

	atom_map = {}
	for atom_data in atoms:
		a = oasa.Atom(symbol=atom_data['symbol'])
		# convert cm coordinates to points for oasa rendering
		a.x = atom_data['x'] * POINTS_PER_CM
		a.y = atom_data['y'] * POINTS_PER_CM
		# set label property for non-standard display
		if atom_data['label']:
			a.properties_["label"] = atom_data['label']
		# set charge (vertex_label_text appends +/- to display text)
		if atom_data.get('charge'):
			a.charge = atom_data['charge']
		# store mark data for circled charge rendering
		if atom_data.get('marks'):
			a.properties_["marks"] = [
				{
					'type': m['type'],
					'x': m['x'] * POINTS_PER_CM,
					'y': m['y'] * POINTS_PER_CM,
				}
				for m in atom_data['marks']
			]
		mol.add_vertex(a)
		atom_map[atom_data['id']] = a

	for bond_data in bonds:
		order = 2 if bond_data['type'] == 'n2' else 1
		b = oasa.Bond(order=order, type='n')
		start_atom = atom_map[bond_data['start']]
		end_atom = atom_map[bond_data['end']]
		mol.add_edge(start_atom, end_atom, b)

	return atom_map


#============================================
def _build_oasa_molecule(strand_data: list, name: str):
	"""Assemble complete oasa.molecule from strand coordinate data.

	Args:
		strand_data: list of (atoms, bonds) tuples
		name: molecule name

	Returns:
		oasa.molecule with all strands
	"""
	import oasa

	mol = oasa.Molecule()
	mol.name = name
	for atoms, bonds in strand_data:
		_build_oasa_strand(mol, atoms, bonds)
	return mol


#============================================
def _render_svg(mol, path: str):
	"""Render molecule to SVG using the render_out pipeline.

	Args:
		mol: oasa.molecule to render
		path: output SVG file path
	"""
	import oasa.render_out

	oasa.render_out.render_to_svg(
		mol,
		path,
		show_hydrogens_on_hetero=False,
		show_carbon_symbol=False,
		margin=20,
		scaling=1.5,
	)


#============================================
def main():
	"""Generate beta-sheet SVG renders and CDML fixtures."""
	repo_root = _get_repo_root()
	_ensure_sys_path(repo_root)

	# output directories
	svg_dir = os.path.join(repo_root, "output_smoke", "oasa_generic_renders")
	cdml_dir = os.path.join(repo_root, "tests", "fixtures", "oasa_generic")
	_ensure_dir(svg_dir)
	_ensure_dir(cdml_dir)

	# backbone atom count for coordinate calculation
	backbone_count = (NUM_RESIDUES - 1) * 3 + 1

	# === parallel beta-sheet (both strands left-to-right) ===
	s1_atoms, s1_bonds, s1_count = _build_strand_atoms(
		X_START_CM, Y_BASE1_CM, NUM_RESIDUES, direction=1, id_offset=0)
	s2_atoms, s2_bonds, _ = _build_strand_atoms(
		X_START_CM, Y_BASE2_CM, NUM_RESIDUES, direction=1, id_offset=s1_count)
	parallel_strands = [(s1_atoms, s1_bonds), (s2_atoms, s2_bonds)]

	# write parallel CDML fixture
	parallel_cdml = os.path.join(cdml_dir, "parallel_beta_sheet.cdml")
	_write_cdml_file(parallel_strands, parallel_cdml)
	print("Parallel CDML: %s" % parallel_cdml)

	# render parallel SVG
	parallel_mol = _build_oasa_molecule(parallel_strands, "parallel_beta_sheet")
	parallel_svg = os.path.join(svg_dir, "parallel_beta_sheet.svg")
	_render_svg(parallel_mol, parallel_svg)
	print("Parallel SVG: %s" % parallel_svg)

	# === antiparallel beta-sheet (strand 2 runs right-to-left) ===
	a1_atoms, a1_bonds, a1_count = _build_strand_atoms(
		X_START_CM, Y_BASE1_CM, NUM_RESIDUES, direction=1, id_offset=0)
	# strand 2 starts at the right edge of strand 1's backbone
	x_right = X_START_CM + (backbone_count - 1) * DX_CM
	a2_atoms, a2_bonds, _ = _build_strand_atoms(
		x_right, Y_BASE2_CM, NUM_RESIDUES, direction=-1, id_offset=a1_count)
	antiparallel_strands = [(a1_atoms, a1_bonds), (a2_atoms, a2_bonds)]

	# write antiparallel CDML fixture
	anti_cdml = os.path.join(cdml_dir, "antiparallel_beta_sheet.cdml")
	_write_cdml_file(antiparallel_strands, anti_cdml)
	print("Antiparallel CDML: %s" % anti_cdml)

	# render antiparallel SVG
	anti_mol = _build_oasa_molecule(
		antiparallel_strands, "antiparallel_beta_sheet")
	anti_svg = os.path.join(svg_dir, "antiparallel_beta_sheet.svg")
	_render_svg(anti_mol, anti_svg)
	print("Antiparallel SVG: %s" % anti_svg)

	# summary
	for label, strands in [("Parallel", parallel_strands),
		("Antiparallel", antiparallel_strands)]:
		total_atoms = sum(len(a) for a, _b in strands)
		total_bonds = sum(len(b) for _a, b in strands)
		print("%s: %d atoms, %d bonds" % (label, total_atoms, total_bonds))


if __name__ == "__main__":
	main()
