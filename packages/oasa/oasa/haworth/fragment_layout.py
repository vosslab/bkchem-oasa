#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Bridge between substituent label strings and 2D-positioned atom groups.

Uses coords_generator2 to compute atom positions for complex multi-atom
substituents (chain-like labels and two-carbon tails), then returns
group-level layout data for the Haworth renderer.

For the CH(OH)CH2OH two-carbon tail, visually-tuned branch angles are used
instead of raw coords_generator2 output, matching the Haworth projection
conventions (120-degree lattice, side-aware "down" orientation).
"""

# Standard Library
import re
import math
import dataclasses

# local repo modules
from oasa import smiles_lib as smiles_module
from oasa import coords_generator2


#============================================
@dataclasses.dataclass
class FragmentAtom:
	"""One display group in a laid-out substituent fragment.

	Attributes:
		label: display text for this group (e.g. "OH", "CH2OH", "" for junction).
		x: positioned x coordinate.
		y: positioned y coordinate.
		parent_index: index of parent atom in the fragment list (-1 for root).
		bond_style: "solid" or "hashed".
	"""
	label: str
	x: float
	y: float
	parent_index: int
	bond_style: str


#============================================
def _smiles_for_label(label: str) -> str | None:
	"""Return the SMILES string for a substituent label, or None if unknown.

	Only handles complex multi-atom substituents that need 2D layout.
	Simple labels (OH, H, F, CH2OH, CH3) are NOT handled here.
	"""
	# CH(OH)CH2OH is a two-carbon branched tail: C(O)CO
	if label == "CH(OH)CH2OH":
		return "C(O)CO"
	# CHAIN<N>: N-1 CHOH segments + 1 CH2OH terminal
	# Each CHOH backbone is C(O) in SMILES, terminal CH2OH is CO
	match = re.match(r"^CHAIN(\d+)$", label or "")
	if match:
		count = int(match.group(1))
		if count >= 2:
			# CHAIN2 = C(O)CO, CHAIN3 = C(O)C(O)CO, etc.
			return "C(O)" * (count - 1) + "CO"
	return None


#============================================
def _implicit_h_count(atom_obj) -> int:
	"""Count implicit hydrogens on an OASA atom (valency - occupied bonds)."""
	return max(0, atom_obj.valency - atom_obj.occupied_valency)


#============================================
def _terminal_carbon_label(atom_obj) -> str:
	"""Build display label for a terminal carbon from its implicit H and O neighbors."""
	implicit_h = _implicit_h_count(atom_obj)
	oxygen_neighbors = [n for n in atom_obj.neighbors if n.symbol == "O"]
	if implicit_h >= 2 and oxygen_neighbors:
		return "CH2OH"
	if implicit_h >= 1 and oxygen_neighbors:
		return "CHOH"
	if implicit_h >= 3:
		return "CH3"
	if implicit_h >= 2:
		return "CH2"
	if implicit_h >= 1:
		return "CH"
	return "C"


#============================================
def _build_molecule(smiles_text: str):
	"""Parse SMILES into an OASA molecule with 2D coordinates."""
	mol = smiles_module.text_to_mol(smiles_text, calc_coords=0)
	coords_generator2.calculate_coords(mol, bond_length=1.0, force=1)
	return mol


#============================================
def _identify_fragment_groups(mol) -> list[dict]:
	"""Walk the molecule and identify display groups.

	Terminal carbons absorb their oxygen children into a single group label
	(e.g. C + O -> "CH2OH"). Junction carbons (with C children) are bare
	connector vertices. Standalone oxygens on junctions become "OH" groups.

	Returns:
		list of group dicts with keys:
			atoms: list of atom objects in this group
			primary: the primary atom for positioning
			label: display text
			parent_group_index: index of parent group (-1 for root)
	"""
	atoms = list(mol.vertices)
	if not atoms:
		return []
	# The first atom (index 0 from SMILES parse) is the attachment atom
	root = atoms[0]

	# Build BFS tree from root
	visited = set()
	parent_map = {}
	order = []
	queue = [root]
	visited.add(root)
	parent_map[root] = None
	while queue:
		current = queue.pop(0)
		order.append(current)
		for neighbor in current.neighbors:
			if neighbor not in visited:
				visited.add(neighbor)
				parent_map[neighbor] = current
				queue.append(neighbor)

	# Build children map from BFS tree
	children_map = {atom_obj: [] for atom_obj in order}
	for atom_obj in order:
		par = parent_map[atom_obj]
		if par is not None:
			children_map[par].append(atom_obj)

	# Group atoms into display groups
	groups = []
	atom_to_group = {}

	for atom_obj in order:
		if atom_obj in atom_to_group:
			continue
		children = children_map[atom_obj]
		# Terminal carbon: all children are oxygen (no carbon children)
		has_carbon_child = any(c.symbol == "C" for c in children)
		if atom_obj.symbol == "C" and not has_carbon_child:
			# Terminal carbon absorbs oxygen children into label
			group_atoms = [atom_obj] + [c for c in children if c.symbol == "O"]
			label = _terminal_carbon_label(atom_obj)
		elif atom_obj.symbol == "O":
			# Standalone oxygen on a junction carbon
			group_atoms = [atom_obj]
			label = "OH"
		elif atom_obj.symbol == "C":
			# Junction carbon with carbon children
			group_atoms = [atom_obj]
			label = ""
		else:
			group_atoms = [atom_obj]
			label = atom_obj.symbol

		group_index = len(groups)
		for a in group_atoms:
			atom_to_group[a] = group_index

		# Determine parent group index
		par = parent_map[atom_obj]
		parent_group_index = atom_to_group[par] if par is not None else -1
		groups.append({
			"atoms": group_atoms,
			"primary": atom_obj,
			"label": label,
			"parent_group_index": parent_group_index,
		})

	return groups


#============================================
def _unit_vector_from_degrees(angle_degrees: float) -> tuple[float, float]:
	"""Return unit vector for an angle in degrees (screen coordinates)."""
	radians = math.radians(angle_degrees)
	return (math.cos(radians), math.sin(radians))


#============================================
def _two_carbon_tail_fragment(
		bond_length: float,
		attachment_point: tuple[float, float],
		direction: tuple[float, float],
		up_or_down: str,
		ring_center: tuple[float, float] | None,
		branch_length: float | None = None) -> list[FragmentAtom]:
	"""Build FragmentAtom list for CH(OH)CH2OH using visually-tuned angles.

	Uses the same branch-angle profiles as the legacy renderer to preserve
	the Haworth projection conventions (120-degree lattice alignment,
	side-aware down-direction orientation).

	Args:
		bond_length: trunk distance from attachment point to branch point.
		branch_length: distance from branch point to each branch label.
			Defaults to bond_length when not specified.
	"""
	# Use separate branch arm length when provided (avoids over-extension
	# when the trunk is boosted for clearance)
	arm_length = branch_length if branch_length is not None else bond_length
	# Branch point at one bond_length from vertex along direction
	bx = attachment_point[0] + direction[0] * bond_length
	by = attachment_point[1] + direction[1] * bond_length

	# Determine branch angles from the Haworth profile
	if up_or_down == "up":
		# OH at 210 deg screen (left-up), CH2OH at 330 deg (right-up)
		ho_dx, ho_dy = _unit_vector_from_degrees(210.0)
		ch2_dx, ch2_dy = _unit_vector_from_degrees(330.0)
		ho_style = "solid"
		ch2_style = "hashed"
	else:
		# "down" direction: side-dependent orientation
		is_left_side = True
		if ring_center is not None:
			is_left_side = attachment_point[0] <= ring_center[0]
		if is_left_side:
			ho_dx, ho_dy = _unit_vector_from_degrees(210.0)
			ch2_dx, ch2_dy = _unit_vector_from_degrees(120.0)
		else:
			ho_dx, ho_dy = _unit_vector_from_degrees(150.0)
			ch2_dx, ch2_dy = _unit_vector_from_degrees(240.0)
		ho_style = "hashed"
		ch2_style = "solid"

	# Position OH and CH2OH at arm_length from branch point
	ho_x = bx + ho_dx * arm_length
	ho_y = by + ho_dy * arm_length
	ch2_x = bx + ch2_dx * arm_length
	ch2_y = by + ch2_dy * arm_length

	return [
		FragmentAtom(label="", x=bx, y=by, parent_index=-1, bond_style="solid"),
		FragmentAtom(label="OH", x=ho_x, y=ho_y, parent_index=0, bond_style=ho_style),
		FragmentAtom(label="CH2OH", x=ch2_x, y=ch2_y, parent_index=0, bond_style=ch2_style),
	]


#============================================
def _bond_style_for_group(
		group_index: int,
		parent_index: int,
		label: str,
		up_or_down: str,
		groups: list[dict]) -> str:
	"""Determine solid vs hashed bond style for one fragment group.

	For CH(OH)CH2OH: one branch gets hashed to show stereochemistry.
	- "up" direction: CH2OH arm is hashed, OH arm is solid
	- "down" direction: OH arm is hashed, CH2OH arm is solid
	"""
	if parent_index == -1:
		return "solid"
	if label != "CH(OH)CH2OH":
		# Only two-carbon tails use hashed bonds
		return "solid"
	# CH(OH)CH2OH: group 0 = junction C, children are OH and CH2OH
	group_label = groups[group_index]["label"]
	is_oh_branch = (group_label == "OH")
	if up_or_down == "up":
		# CH2OH arm is hashed, OH is solid
		return "solid" if is_oh_branch else "hashed"
	# down: OH arm is hashed, CH2OH is solid
	return "hashed" if is_oh_branch else "solid"


#============================================
def layout_fragment(
		label: str,
		bond_length: float,
		attachment_point: tuple[float, float],
		direction: tuple[float, float],
		up_or_down: str = "up",
		ring_center: tuple[float, float] | None = None,
		branch_length: float | None = None) -> list[FragmentAtom] | None:
	"""Lay out a complex substituent fragment in 2D coordinates.

	The root group (index 0) is positioned at one bond_length from the
	attachment_point along direction. The attachment_point itself is the
	ring vertex; the caller draws a connector from the vertex to group 0.

	For CH(OH)CH2OH, uses visually-tuned branch angles matching the Haworth
	projection conventions. For other complex labels, uses coords_generator2.

	Args:
		label: substituent label (e.g. "CH(OH)CH2OH", "CHAIN3").
		bond_length: trunk distance from attachment point to branch point.
		attachment_point: (x, y) ring vertex where the substituent originates.
		direction: (dx, dy) unit vector pointing away from the ring.
		up_or_down: "up" or "down", affects hashed bond assignment for
			stereochemistry in branched fragments.
		ring_center: (x, y) center of the ring, used to orient "down"
			branches away from the ring body.
		branch_length: distance from branch point to each branch label.
			Defaults to bond_length when not specified.

	Returns:
		list of FragmentAtom positioned in renderer coordinates,
		or None if the label is not recognized as a complex fragment.
	"""
	smiles_text = _smiles_for_label(label)
	if smiles_text is None:
		return None

	# CH(OH)CH2OH uses visually-tuned angles for Haworth rendering
	if label == "CH(OH)CH2OH":
		return _two_carbon_tail_fragment(
			bond_length=bond_length,
			attachment_point=attachment_point,
			direction=direction,
			up_or_down=up_or_down,
			ring_center=ring_center,
			branch_length=branch_length,
		)

	# General case: use coords_generator2 for 2D layout
	mol = _build_molecule(smiles_text)
	if len(mol.vertices) < 2:
		return None

	# Identify display groups from molecular topology
	groups = _identify_fragment_groups(mol)
	if not groups:
		return None

	# Extract raw positions (use primary atom coordinates)
	raw_positions = [(g["primary"].x, g["primary"].y) for g in groups]
	root_pos = raw_positions[0]

	# Compute the inferred incoming-bond direction at the root atom.
	child_angles = []
	for index, group in enumerate(groups):
		if group["parent_group_index"] == 0:
			cdx = raw_positions[index][0] - root_pos[0]
			cdy = raw_positions[index][1] - root_pos[1]
			child_angles.append(math.atan2(cdy, cdx))
	if not child_angles:
		return None
	# Average outgoing angle, then incoming is 180 degrees opposite
	avg_sin = sum(math.sin(a) for a in child_angles) / len(child_angles)
	avg_cos = sum(math.cos(a) for a in child_angles) / len(child_angles)
	avg_outgoing = math.atan2(avg_sin, avg_cos)
	incoming_mol_angle = avg_outgoing + math.pi

	# Align the molecule's incoming bond with the renderer's
	incoming_renderer_angle = math.atan2(-direction[1], -direction[0])
	rotation = incoming_renderer_angle - incoming_mol_angle
	cos_r = math.cos(rotation)
	sin_r = math.sin(rotation)

	# Scale: coords_generator2 uses bond_length=1.0
	scale = bond_length

	# Root is offset by one bond_length from attachment_point (ring vertex)
	origin_x = attachment_point[0] + direction[0] * bond_length
	origin_y = attachment_point[1] + direction[1] * bond_length

	# Transform all group positions: rotate, scale, translate
	positioned = []
	for index, group in enumerate(groups):
		# Offset from root in molecule coordinates
		rx = raw_positions[index][0] - root_pos[0]
		ry = raw_positions[index][1] - root_pos[1]
		# Rotate
		rotated_x = cos_r * rx - sin_r * ry
		rotated_y = sin_r * rx + cos_r * ry
		# Scale and translate (root is at origin_x, origin_y)
		final_x = origin_x + rotated_x * scale
		final_y = origin_y + rotated_y * scale
		# Bond style (solid or hashed)
		bond_style = _bond_style_for_group(
			group_index=index,
			parent_index=group["parent_group_index"],
			label=label,
			up_or_down=up_or_down,
			groups=groups,
		)
		positioned.append(FragmentAtom(
			label=group["label"],
			x=final_x,
			y=final_y,
			parent_index=group["parent_group_index"],
			bond_style=bond_style,
		))

	return positioned
