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

"""Haworth projection ring layout and substituent placement."""

# Standard Library
import math


#============================================
PYRANOSE_TEMPLATE = [
	(-1.25, 0.00),
	(-0.45, -0.75),
	(0.45, -0.75),
	(1.25, 0.00),
	(0.55, 0.70),
	(-0.55, 0.70),
]

FURANOSE_TEMPLATE = [
	(-0.97, -0.26),
	(-0.49, 0.58),
	(0.49, 0.58),
	(0.97, -0.26),
	(0.00, -0.65),
]

PYRANOSE_O_INDEX = 2
FURANOSE_O_INDEX = 4
HAWORTH_EXPECTED_ORIENTATION = "ccw"


#============================================
def build_haworth(
		mol,
		mode="pyranose",
		ring_atoms=None,
		bond_length=30,
		front_style="haworth",
		back_style="n",
		front_count=None,
		series=None,
		stereo=None,
		substituent_map=None,
		substituent_length=None):
	"""Apply a Haworth-style ring layout and tag front edges.

	Args:
		mol: OASA molecule instance.
		mode: "pyranose" (6-member) or "furanose" (5-member).
		ring_atoms: Optional ordered or unordered ring atom list.
		bond_length: Target bond length in screen units.
		front_style: Bond type used for front edges (default "haworth").
			"haworth" assigns wedges on the side edges and a wide rectangle
			across the lowest front edge.
		back_style: Bond type for non-front ring edges (default "n").
		front_count: Optional count of front edges to tag.

	Returns:
		dict: {"ring_atoms": [...], "ring_bonds": [...], "front_bonds": [...]}
	"""
	if mode not in ("pyranose", "furanose"):
		raise ValueError("mode must be 'pyranose' or 'furanose'")
	ring_size = 6 if mode == "pyranose" else 5
	if ring_atoms is None:
		ring_atoms = _find_ring_atoms(mol, ring_size)
	ordered_atoms = _order_ring_atoms(mol, ring_atoms)
	coords = _ring_template(ring_size, bond_length=bond_length)
	ordered_atoms, coords = _normalize_orientation(ordered_atoms, coords, ring_size)
	ordered_atoms = _rotate_for_oxygen(ordered_atoms, ring_size)
	_center_ring_on_atoms(coords, ordered_atoms)
	_apply_coords(ordered_atoms, coords)
	ring_bonds = _ring_bonds(mol, ordered_atoms)
	front_bonds = _tag_front_edges(ordered_atoms, ring_bonds, coords,
									front_style=front_style,
									back_style=back_style,
									front_count=front_count)
	series = _normalize_series(series)
	stereo = _normalize_stereo(stereo)
	if stereo and not series:
		series = "D"
	if series or stereo or substituent_map:
		place_substituents(
			mol,
			ordered_atoms,
			series=series,
			stereo=stereo,
			substituent_map=substituent_map,
			bond_length=bond_length,
			substituent_length=substituent_length,
		)
	return {
		"ring_atoms": ordered_atoms,
		"ring_bonds": ring_bonds,
		"front_bonds": front_bonds,
	}


#============================================
def _find_ring_atoms(mol, ring_size):
	for ring in mol.get_smallest_independent_cycles():
		if len(ring) == ring_size:
			return list(ring)
	raise ValueError(f"No ring of size {ring_size} found")


#============================================
def _order_ring_atoms(mol, ring_atoms):
	ring_set = set(ring_atoms)
	ordered = []
	# Prefer starting at oxygen if exactly one O is in the ring
	oxygen_atoms = [a for a in ring_atoms if getattr(a, "symbol", None) == "O"]
	if len(oxygen_atoms) == 1:
		start = oxygen_atoms[0]
	else:
		start = min(ring_atoms, key=lambda a: mol.vertices.index(a))
	neighbors = [n for n in start.neighbors if n in ring_set]
	if len(neighbors) < 2:
		raise ValueError("Ring atom does not have two ring neighbors")
	next_atom = min(neighbors, key=lambda a: mol.vertices.index(a))
	ordered.append(start)
	ordered.append(next_atom)
	prev = start
	curr = next_atom
	while True:
		choices = [n for n in curr.neighbors if n in ring_set and n is not prev]
		if not choices:
			break
		nxt = choices[0]
		if nxt is start:
			break
		ordered.append(nxt)
		prev, curr = curr, nxt
		if len(ordered) > len(ring_atoms):
			break
	if len(ordered) != len(ring_atoms):
		raise ValueError("Failed to order ring atoms")
	return ordered


#============================================
def _rotate_for_oxygen(ordered_atoms, ring_size):
	target_index = _oxygen_target_index(ring_size)
	if target_index is None:
		return ordered_atoms
	oxygen_index = None
	for idx, atom in enumerate(ordered_atoms):
		if getattr(atom, "symbol", None) == "O":
			oxygen_index = idx
			break
	if oxygen_index is None:
		return ordered_atoms
	shift = (target_index - oxygen_index) % len(ordered_atoms)
	if shift == 0:
		return ordered_atoms
	return ordered_atoms[-shift:] + ordered_atoms[:-shift]


#============================================
def _oxygen_target_index(ring_size):
	if ring_size == 6:
		return PYRANOSE_O_INDEX
	if ring_size == 5:
		return FURANOSE_O_INDEX
	return None


#============================================
def _normalize_orientation(ordered_atoms, coords, ring_size):
	area = _signed_area(coords)
	if _orientation_matches(area):
		return ordered_atoms, coords
	ordered_atoms = list(reversed(ordered_atoms))
	ordered_atoms = _rotate_for_oxygen(ordered_atoms, ring_size)
	return ordered_atoms, coords


#============================================
def _signed_area(points):
	if len(points) < 3:
		return 0.0
	area = 0.0
	for i in range(len(points)):
		x1, y1 = points[i]
		x2, y2 = points[(i + 1) % len(points)]
		area += (x1 * y2) - (x2 * y1)
	return area / 2.0


#============================================
def _orientation_matches(area):
	if HAWORTH_EXPECTED_ORIENTATION == "ccw":
		return area < 0
	if HAWORTH_EXPECTED_ORIENTATION == "cw":
		return area > 0
	return True


#============================================
def _ring_template(ring_size, bond_length=30):
	if ring_size == 6:
		points = list(PYRANOSE_TEMPLATE)
	elif ring_size == 5:
		points = list(FURANOSE_TEMPLATE)
	else:
		raise ValueError("ring_size must be 5 or 6")
	mean_len = _mean_edge_length(points)
	if mean_len:
		scale = bond_length / mean_len
	else:
		scale = bond_length
	return [(x * scale, y * scale) for x, y in points]


#============================================
def _mean_edge_length(points):
	if len(points) < 2:
		return None
	total = 0.0
	for i in range(len(points)):
		x1, y1 = points[i]
		x2, y2 = points[(i + 1) % len(points)]
		total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
	return total / len(points)


#============================================
def _center_ring_on_atoms(points, atoms):
	if not atoms:
		return
	avg_x = sum(a.x for a in atoms) / len(atoms)
	avg_y = sum(a.y for a in atoms) / len(atoms)
	px = sum(p[0] for p in points) / len(points)
	py = sum(p[1] for p in points) / len(points)
	dx = avg_x - px
	dy = avg_y - py
	for idx, (x, y) in enumerate(points):
		points[idx] = (x + dx, y + dy)


#============================================
def _apply_coords(atoms, points):
	for atom, (x, y) in zip(atoms, points):
		atom.x = x
		atom.y = y


#============================================
def _ring_bonds(mol, atoms):
	bonds = []
	for i in range(len(atoms)):
		v1 = atoms[i]
		v2 = atoms[(i + 1) % len(atoms)]
		bond = mol.get_edge_between(v1, v2)
		if bond is None:
			raise ValueError("Ring atoms are not connected by a bond")
		bond.set_vertices((v1, v2))
		bonds.append(bond)
	return bonds


#============================================
def _tag_front_edges(atoms, bonds, points, front_style="haworth", back_style="n", front_count=None):
	edge_midpoints = []
	midpoint_map = {}
	for i in range(len(points)):
		x1, y1 = points[i]
		x2, y2 = points[(i + 1) % len(points)]
		mid_x = (x1 + x2) / 2.0
		mid_y = (y1 + y2) / 2.0
		edge_midpoints.append((i, mid_x, mid_y))
		midpoint_map[i] = (mid_x, mid_y)

	front_idx = None
	if front_style == "haworth":
		front_indices, front_styles, front_idx = _haworth_front_indices(edge_midpoints, len(atoms))
	else:
		if front_count is None:
			front_count = 2 if len(atoms) >= 5 else 1
		center_x = sum(p[0] for p in points) / len(points)
		edge_midpoints.sort(key=lambda item: item[2], reverse=True)
		front_edges = edge_midpoints[:front_count]
		front_indices = {idx for idx, _x, _y in front_edges}
		front_styles = {}
		for idx, mid_x, _mid_y in front_edges:
			front_styles[idx] = _resolve_front_style(front_style, mid_x, center_x)
	front_vertices = None
	if front_idx is not None:
		front_vertices = set(bonds[front_idx].vertices)
	front_bonds = []
	for i, bond in enumerate(bonds):
		if i in front_indices:
			style = front_styles.get(i, "q")
			bond.type = style
			bond.properties_['haworth_position'] = 'front'
			if style == "w":
				_orient_wedge(bond, front_vertices)
				if front_idx is not None:
					bond.properties_['haworth_front_bond'] = bonds[front_idx]
			front_bonds.append(bond)
		else:
			bond.type = back_style
			bond.properties_['haworth_position'] = 'back'
	return front_bonds


#============================================
def _resolve_front_style(front_style, edge_x, center_x):
	return front_style


#============================================
def _haworth_front_indices(edge_midpoints, ring_size):
	if not edge_midpoints:
		return set(), {}, None
	front_idx = max(edge_midpoints, key=lambda item: item[2])[0]
	left_idx = (front_idx - 1) % ring_size
	right_idx = (front_idx + 1) % ring_size
	front_indices = {front_idx, left_idx, right_idx}
	styles = {
		front_idx: "q",
		left_idx: "w",
		right_idx: "w",
	}
	return front_indices, styles, front_idx


#============================================
def _orient_wedge(bond, front_vertices=None):
	v1, v2 = bond.vertices
	if front_vertices:
		if v1 in front_vertices and v2 not in front_vertices:
			bond.set_vertices((v2, v1))
			return
		if v2 in front_vertices and v1 not in front_vertices:
			return
	if v1.y > v2.y:
		bond.set_vertices((v2, v1))


#============================================
def place_substituents(
		mol,
		ring_atoms,
		series=None,
		stereo=None,
		substituent_map=None,
		bond_length=30,
		substituent_length=None):
	series = _normalize_series(series)
	stereo = _normalize_stereo(stereo)
	if stereo and not series:
		series = "D"
	orientation_map = _build_substituent_orientations(
		ring_atoms,
		series=series,
		stereo=stereo,
		substituent_map=substituent_map,
	)
	if not orientation_map:
		return []
	if substituent_length is None:
		substituent_length = bond_length * 0.7
	ring_set = set(ring_atoms)
	moved = set()
	for ring_atom in ring_atoms:
		orientation = orientation_map.get(ring_atom)
		if not orientation:
			continue
		for neighbor in ring_atom.neighbors:
			if neighbor in ring_set:
				continue
			group = _collect_substituent_group(neighbor, ring_set)
			if any(atom in moved for atom in group):
				continue
			length = _distance(ring_atom.x, ring_atom.y, neighbor.x, neighbor.y)
			if not length:
				length = substituent_length
			target_x, target_y = _substituent_target(ring_atom, orientation, length)
			_shift_substituent_group(group, neighbor, target_x, target_y)
			moved.update(group)
	return list(moved)


#============================================
def _normalize_series(series):
	if not series:
		return None
	text = str(series).strip().upper()
	if text in ("D", "L"):
		return text
	return None


#============================================
def _normalize_stereo(stereo):
	if not stereo:
		return None
	text = str(stereo).strip().lower()
	if text in ("alpha", "a"):
		return "alpha"
	if text in ("beta", "b"):
		return "beta"
	return None


#============================================
def _build_substituent_orientations(ring_atoms, series=None, stereo=None, substituent_map=None):
	orientations = {}
	_apply_substituent_map(orientations, ring_atoms, substituent_map)
	if not series and not stereo:
		return orientations
	oxygen_index = _ring_oxygen_index(ring_atoms)
	if oxygen_index is None:
		return orientations
	ring_size = len(ring_atoms)
	reference_index = (oxygen_index - 1) % ring_size
	reference_orientation = None
	if series == "D":
		reference_orientation = "up"
	elif series == "L":
		reference_orientation = "down"
	if reference_orientation:
		orientations[ring_atoms[reference_index]] = reference_orientation
	if stereo:
		anomeric_index = (oxygen_index + 1) % ring_size
		if reference_orientation:
			if stereo == "alpha":
				anomeric_orientation = "down" if reference_orientation == "up" else "up"
			else:
				anomeric_orientation = reference_orientation
			orientations[ring_atoms[anomeric_index]] = anomeric_orientation
	return orientations


#============================================
def _apply_substituent_map(orientations, ring_atoms, substituent_map):
	if not substituent_map:
		return
	for key, value in substituent_map.items():
		orientation = _normalize_orientation_text(value)
		if not orientation:
			continue
		if isinstance(key, int):
			if 0 <= key < len(ring_atoms):
				orientations[ring_atoms[key]] = orientation
			continue
		orientations[key] = orientation


#============================================
def _normalize_orientation_text(value):
	if not value:
		return None
	text = str(value).strip().lower()
	if text in ("up", "u", "above"):
		return "up"
	if text in ("down", "d", "below"):
		return "down"
	return None


#============================================
def _ring_oxygen_index(ring_atoms):
	for idx, atom in enumerate(ring_atoms):
		if getattr(atom, "symbol", None) == "O":
			return idx
	return None


#============================================
def _collect_substituent_group(start_atom, ring_set):
	group = []
	stack = [start_atom]
	seen = set()
	while stack:
		atom = stack.pop()
		if atom in seen or atom in ring_set:
			continue
		seen.add(atom)
		group.append(atom)
		for neighbor in atom.neighbors:
			if neighbor not in seen and neighbor not in ring_set:
				stack.append(neighbor)
	return group


#============================================
def _substituent_target(ring_atom, orientation, length):
	if orientation == "up":
		return ring_atom.x, ring_atom.y - length
	return ring_atom.x, ring_atom.y + length


#============================================
def _shift_substituent_group(group, anchor_atom, target_x, target_y):
	dx = target_x - anchor_atom.x
	dy = target_y - anchor_atom.y
	if dx == 0 and dy == 0:
		return
	for atom in group:
		atom.x += dx
		atom.y += dy


#============================================
def _distance(x1, y1, x2, y2):
	return math.hypot(x2 - x1, y2 - y1)
