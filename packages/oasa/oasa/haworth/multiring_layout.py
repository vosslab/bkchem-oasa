"""Pure layout planning for direct glycosidic Haworth disaccharides.

This module deliberately produces an immutable plan rather than changing an
OASA molecule.  A caller can apply the plan through its own document and undo
boundary after it has decided that the narrowly supported topology is useful.
Coordinates use the existing Haworth screen-coordinate convention: positive
``y`` points down and ``bond_length`` is measured in drawing units.
"""

# Standard Library
import dataclasses
import math

# Local modules
import oasa.haworth.layout
import oasa.haworth.renderer_config


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthRingPlan:
	"""One canonical Haworth ring, addressed by stable molecule indexes."""

	ring_type: str
	vertex_indexes: tuple[int, ...]
	coordinates: tuple[tuple[float, float], ...]
	front_edge_index: int


#============================================
@dataclasses.dataclass(frozen=True)
class GlycosidicBridgePlan:
	"""One direct external oxygen bridge between the two planned rings."""

	oxygen_vertex_index: int
	left_attachment_vertex_index: int
	right_attachment_vertex_index: int
	coordinate: tuple[float, float]


#============================================
@dataclasses.dataclass(frozen=True)
class DirectGlycosidicDisaccharidePlan:
	"""Immutable layout result for one unchanged molecule vertex ordering.

	``vertex_indexes`` are positional references.  They remain valid only while
	the input molecule keeps the same vertex objects in the same order.  Callers
	can use :meth:`matches_positional_vertex_map` for that narrow check or
	:meth:`matches_molecule_topology` to include atom symbols and bond chemistry.
	"""

	left_ring: HaworthRingPlan
	right_ring: HaworthRingPlan
	bridge: GlycosidicBridgePlan
	vertex_identity_order_fingerprint: tuple[int, ...]
	vertex_symbol_fingerprint: tuple[str, ...]
	edge_chemistry_fingerprint: tuple[tuple[int, int, int, bool], ...]

	#============================================
	def matches_positional_vertex_map(self, mol: object) -> bool:
		"""Check only that positional vertex indexes still address the same objects."""
		result = tuple(id(atom) for atom in mol.vertices) == self.vertex_identity_order_fingerprint
		return result

	#============================================
	def matches_molecule_topology(self, mol: object) -> bool:
		"""Check positional vertices plus atom symbols and every bond's chemistry."""
		result = (
			self.matches_positional_vertex_map(mol)
			and tuple(atom.symbol for atom in mol.vertices) == self.vertex_symbol_fingerprint
			and _edge_chemistry_fingerprint(mol) == self.edge_chemistry_fingerprint)
		return result


#============================================
def plan_direct_glycosidic_disaccharide(
		mol: object,
		bond_length: float=30.0) -> DirectGlycosidicDisaccharidePlan:
	"""Plan two non-overlapping Haworth rings joined by one direct oxygen.

	Only two vertex-disjoint, all-single-bond 5/6-member C/O rings are accepted.
	The connection must be one degree-two oxygen directly bonded to one carbon in
	each ring.  In particular, an O-C exocyclic chain is not inferred as a 1->6
	linkage because this planner does not guess carbohydrate carbon numbering.
	"""
	if not math.isfinite(bond_length) or bond_length <= 0:
		raise ValueError("bond_length must be finite and positive")
	rings = _supported_rings(mol)
	left_ring, right_ring = _order_whole_rings(mol, rings)
	bridge_oxygen, left_attachment, right_attachment = _direct_bridge(
		mol, left_ring, right_ring)
	left_plan = _ring_plan(mol, left_ring, left_attachment, bond_length, side=1.0)
	right_plan = _ring_plan(mol, right_ring, right_attachment, bond_length, side=-1.0)
	bridge_coordinate = _bridge_midpoint(
		mol, left_plan, left_attachment, right_plan, right_attachment)
	bridge = GlycosidicBridgePlan(
		oxygen_vertex_index=mol.vertices.index(bridge_oxygen),
		left_attachment_vertex_index=mol.vertices.index(left_attachment),
		right_attachment_vertex_index=mol.vertices.index(right_attachment),
		coordinate=bridge_coordinate,
	)
	if not _bridge_segments_clear(left_plan, right_plan, bridge):
		raise ValueError("Direct disaccharide Haworth layout could not keep bridge bonds clear of nonincident ring edges")
	plan = DirectGlycosidicDisaccharidePlan(
		left_ring=left_plan,
		right_ring=right_plan,
		bridge=bridge,
		vertex_identity_order_fingerprint=tuple(id(atom) for atom in mol.vertices),
		vertex_symbol_fingerprint=tuple(atom.symbol for atom in mol.vertices),
		edge_chemistry_fingerprint=_edge_chemistry_fingerprint(mol),
	)
	return plan


#============================================
def _supported_rings(mol: object) -> tuple[tuple[object, ...], tuple[object, ...]]:
	"""Validate and return the only two cycle-basis rings this slice supports."""
	cycles = list(mol.get_smallest_independent_cycles())
	if len(cycles) != 2:
		raise ValueError("Direct disaccharide Haworth layout requires exactly two cycle-basis rings")
	rings = tuple(tuple(cycle) for cycle in cycles)
	if set(rings[0]) & set(rings[1]):
		raise ValueError("Direct disaccharide Haworth layout requires vertex-disjoint rings; fused, spiro, and cage topologies are unsupported")
	for ring in rings:
		_validate_ring(mol, ring)
	return rings


#============================================
def _validate_ring(mol: object, ring: tuple[object, ...]) -> None:
	"""Reject non-Haworth ring chemistry before any placement calculation."""
	if len(ring) not in (5, 6):
		raise ValueError("Direct disaccharide Haworth layout supports only 5- or 6-member rings")
	if sum(atom.symbol == "O" for atom in ring) != 1:
		raise ValueError("Each supported Haworth ring must contain exactly one oxygen")
	if any(atom.symbol not in ("C", "O") for atom in ring):
		raise ValueError("Supported Haworth rings may contain only carbon and oxygen")
	for atom in ring:
		ring_neighbors = [neighbor for neighbor in atom.neighbors if neighbor in ring]
		if len(ring_neighbors) != 2:
			raise ValueError("Each supported Haworth ring must be a simple cycle")
	for index, atom in enumerate(ring):
		for neighbor in ring[index + 1:]:
			bond = mol.get_edge_between(atom, neighbor)
			if bond is not None and not _is_single_non_aromatic(bond):
				raise ValueError("Supported Haworth ring edges must be single and non-aromatic")


#============================================
def _order_whole_rings(
		mol: object,
		rings: tuple[tuple[object, ...], tuple[object, ...]]) -> tuple[tuple[object, ...], tuple[object, ...]]:
	"""Choose whole-ring left/right order from existing x coordinates, if usable."""
	left_ring, right_ring = rings
	if _has_coordinates(left_ring) and _has_coordinates(right_ring):
		left_x = _mean_x(left_ring)
		right_x = _mean_x(right_ring)
		if right_x < left_x:
			left_ring, right_ring = right_ring, left_ring
		elif right_x == left_x and _first_vertex_index(mol, right_ring) < _first_vertex_index(mol, left_ring):
			left_ring, right_ring = right_ring, left_ring
	elif _first_vertex_index(mol, right_ring) < _first_vertex_index(mol, left_ring):
		left_ring, right_ring = right_ring, left_ring
	return left_ring, right_ring


#============================================
def _has_coordinates(ring: tuple[object, ...]) -> bool:
	"""Return whether a complete ring has usable existing x/y coordinates."""
	result = all(_finite_coordinate(atom.x) and _finite_coordinate(atom.y) for atom in ring)
	return result


#============================================
def _finite_coordinate(value: object) -> bool:
	"""Accept only finite numeric coordinates for optional whole-ring ordering."""
	if not isinstance(value, (int, float)):
		return False
	result = math.isfinite(float(value))
	return result


#============================================
def _mean_x(ring: tuple[object, ...]) -> float:
	"""Return the already placed ring center used only for whole-ring ordering."""
	value = sum(float(atom.x) for atom in ring) / len(ring)
	return value


#============================================
def _first_vertex_index(mol: object, ring: tuple[object, ...]) -> int:
	"""Return the deterministic vertex-order tie breaker for a ring."""
	index = min(mol.vertices.index(atom) for atom in ring)
	return index


#============================================
def _direct_bridge(
		mol: object,
		left_ring: tuple[object, ...],
		right_ring: tuple[object, ...]) -> tuple[object, object, object]:
	"""Find the unique external oxygen directly linking non-oxygen ring atoms."""
	left_set = set(left_ring)
	right_set = set(right_ring)
	candidates = []
	for atom in mol.vertices:
		if atom in left_set or atom in right_set:
			continue
		if atom.symbol != "O" or atom.degree != 2:
			continue
		left_neighbors = [neighbor for neighbor in atom.neighbors if neighbor in left_set and neighbor.symbol != "O"]
		right_neighbors = [neighbor for neighbor in atom.neighbors if neighbor in right_set and neighbor.symbol != "O"]
		if len(left_neighbors) == 1 and len(right_neighbors) == 1:
			left_bond = mol.get_edge_between(atom, left_neighbors[0])
			right_bond = mol.get_edge_between(atom, right_neighbors[0])
			if _is_single_non_aromatic(left_bond) and _is_single_non_aromatic(right_bond):
				candidates.append((atom, left_neighbors[0], right_neighbors[0]))
	if len(candidates) != 1:
		raise ValueError("Direct disaccharide Haworth layout requires exactly one external degree-two oxygen directly bonded to one non-oxygen atom in each ring")
	bridge = candidates[0]
	return bridge


#============================================
def _ring_plan(
		mol: object,
		ring: tuple[object, ...],
		attachment: object,
		bond_length: float,
		side: float) -> HaworthRingPlan:
	"""Create a canonical ring whose attachment faces the bridge at the origin."""
	ordered_atoms = oasa.haworth.layout._order_ring_atoms(mol, list(ring))
	ring_type = _ring_type(ordered_atoms)
	oxygen_index = oasa.haworth.renderer_config.RING_RENDER_CONFIG[ring_type]["oxygen_index"]
	ordered_atoms = _rotate_to_index(ordered_atoms, oxygen_index)
	coordinates = _template_coordinates(tuple(ordered_atoms), bond_length)
	attachment_index = ordered_atoms.index(attachment)
	translated = _place_attachment_facing_bridge(coordinates, attachment_index, bond_length, side)
	front_edge_index = oasa.haworth.renderer_config.RING_RENDER_CONFIG[ring_type]["front_edge_index"]
	plan = HaworthRingPlan(
		ring_type=ring_type,
		vertex_indexes=tuple(mol.vertices.index(atom) for atom in ordered_atoms),
		coordinates=translated,
		front_edge_index=front_edge_index,
	)
	return plan


#============================================
def _place_attachment_facing_bridge(
		coordinates: tuple[tuple[float, float], ...],
		attachment_index: int,
		bond_length: float,
		side: float) -> tuple[tuple[float, float], ...]:
	"""Rotate and translate a convex template so its attachment faces the bridge.

	``side=1`` makes the attachment the right-facing extremum of the left ring;
	``side=-1`` makes it the left-facing extremum of the right ring.  The bridge
	then lies at the origin and each attachment is exactly one bond length away.
	"""
	outward_x, outward_y = _attachment_outward_vector(coordinates, attachment_index)
	target_x = side
	target_y = 0.0
	cosine = (outward_x * target_x) + (outward_y * target_y)
	sine = (outward_x * target_y) - (outward_y * target_x)
	rotated = tuple(
		((x * cosine) - (y * sine), (x * sine) + (y * cosine))
		for x, y in coordinates)
	attachment_x, attachment_y = rotated[attachment_index]
	target_attachment_x = -bond_length if side == 1.0 else bond_length
	translated = tuple(
		(x + target_attachment_x - attachment_x, y - attachment_y)
		for x, y in rotated)
	return translated


#============================================
def _attachment_outward_vector(
		coordinates: tuple[tuple[float, float], ...],
		attachment_index: int) -> tuple[float, float]:
	"""Return a supporting outward vector at one convex template vertex."""
	attachment_x, attachment_y = coordinates[attachment_index]
	previous_x, previous_y = coordinates[(attachment_index - 1) % len(coordinates)]
	next_x, next_y = coordinates[(attachment_index + 1) % len(coordinates)]
	previous_dx, previous_dy = _unit_vector(previous_x - attachment_x, previous_y - attachment_y)
	next_dx, next_dy = _unit_vector(next_x - attachment_x, next_y - attachment_y)
	outward_x, outward_y = _unit_vector(-(previous_dx + next_dx), -(previous_dy + next_dy))
	return outward_x, outward_y


#============================================
def _unit_vector(dx: float, dy: float) -> tuple[float, float]:
	"""Normalize one non-zero template edge vector."""
	length = math.hypot(dx, dy)
	if length == 0:
		raise ValueError("Haworth template has a zero-length edge")
	vector = (dx / length, dy / length)
	return vector


#============================================
def _ring_type(ring: list[object]) -> str:
	"""Map supported ring size to the renderer's canonical ring configuration."""
	if len(ring) == 6:
		result = "pyranose"
	elif len(ring) == 5:
		result = "furanose"
	else:
		raise ValueError("Supported Haworth ring must have five or six members")
	return result


#============================================
def _rotate_to_index(atoms: list[object], target_index: int) -> list[object]:
	"""Put the unique ring oxygen in the canonical renderer slot."""
	oxygen_index = next(index for index, atom in enumerate(atoms) if atom.symbol == "O")
	shift = (target_index - oxygen_index) % len(atoms)
	rotated = atoms[-shift:] + atoms[:-shift] if shift else list(atoms)
	return rotated


#============================================
def _template_coordinates(ring: tuple[object, ...], bond_length: float) -> tuple[tuple[float, float], ...]:
	"""Scale the existing renderer template without altering the input molecule."""
	coordinates = oasa.haworth.layout._ring_template(len(ring), bond_length=bond_length)
	result = tuple((float(x), float(y)) for x, y in coordinates)
	return result


#============================================
def _bridge_midpoint(
		mol: object,
		left_plan: HaworthRingPlan,
		left_attachment: object,
		right_plan: HaworthRingPlan,
		right_attachment: object) -> tuple[float, float]:
	"""Place the external oxygen at the midpoint of its two direct attachments."""
	left_vertex_index = mol.vertices.index(left_attachment)
	right_vertex_index = mol.vertices.index(right_attachment)
	left_index = left_plan.vertex_indexes.index(left_vertex_index)
	right_index = right_plan.vertex_indexes.index(right_vertex_index)
	left_x, left_y = left_plan.coordinates[left_index]
	right_x, right_y = right_plan.coordinates[right_index]
	coordinate = ((left_x + right_x) / 2.0, (left_y + right_y) / 2.0)
	return coordinate


#============================================
def _is_single_non_aromatic(bond: object) -> bool:
	"""Return whether one required bridge or ring bond has supported chemistry."""
	result = bond is not None and bond.order == 1 and not bond.aromatic
	return result


#============================================
def _edge_chemistry_fingerprint(mol: object) -> tuple[tuple[int, int, int, bool], ...]:
	"""Encode graph connectivity and bond chemistry using current vertex indexes."""
	records = []
	for bond in mol.edges:
		first, second = bond.vertices
		first_index = mol.vertices.index(first)
		second_index = mol.vertices.index(second)
		low_index, high_index = sorted((first_index, second_index))
		records.append((low_index, high_index, int(bond.order), bool(bond.aromatic)))
	fingerprint = tuple(sorted(records))
	return fingerprint


#============================================
def _bridge_segments_clear(
		left_ring: HaworthRingPlan,
		right_ring: HaworthRingPlan,
		bridge: GlycosidicBridgePlan) -> bool:
	"""Return whether neither bridge segment properly crosses a ring edge."""
	left_clear = _bridge_segment_clear_for_ring(
		left_ring, bridge.left_attachment_vertex_index, bridge.coordinate)
	right_clear = _bridge_segment_clear_for_ring(
		right_ring, bridge.right_attachment_vertex_index, bridge.coordinate)
	result = left_clear and right_clear
	return result


#============================================
def _bridge_segment_clear_for_ring(
		ring: HaworthRingPlan,
		attachment_vertex_index: int,
		bridge_coordinate: tuple[float, float]) -> bool:
	"""Check one attachment-to-bridge segment against nonincident ring edges."""
	attachment_index = ring.vertex_indexes.index(attachment_vertex_index)
	attachment = ring.coordinates[attachment_index]
	for index, start in enumerate(ring.coordinates):
		end_index = (index + 1) % len(ring.coordinates)
		if index == attachment_index or end_index == attachment_index:
			continue
		end = ring.coordinates[end_index]
		if _properly_intersects(attachment, bridge_coordinate, start, end):
			return False
	return True


#============================================
def _properly_intersects(
		first_start: tuple[float, float],
		first_end: tuple[float, float],
		second_start: tuple[float, float],
		second_end: tuple[float, float]) -> bool:
	"""Return whether two non-collinear segments have a proper intersection."""
	first_a = _orientation(first_start, first_end, second_start)
	first_b = _orientation(first_start, first_end, second_end)
	second_a = _orientation(second_start, second_end, first_start)
	second_b = _orientation(second_start, second_end, first_end)
	result = (first_a * first_b < 0.0) and (second_a * second_b < 0.0)
	return result


#============================================
def _orientation(
		start: tuple[float, float],
		end: tuple[float, float],
		point: tuple[float, float]) -> float:
	"""Return the signed area predicate for one segment and point."""
	start_x, start_y = start
	end_x, end_y = end
	point_x, point_y = point
	value = ((end_x - start_x) * (point_y - start_y)) - ((end_y - start_y) * (point_x - start_x))
	return value
