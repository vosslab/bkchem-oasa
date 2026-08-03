"""Complete detached Haworth preparation for direct glycosidic disaccharides.

The planner in :mod:`oasa.haworth.multiring_layout` owns the narrow topology
profile.  This module turns one unchanged planned graph into a complete,
validated coordinate proposal.  It intentionally describes a drawing
convention only; the q/w/n records do not recover tetrahedral stereochemistry.
"""

# Standard Library
import math

# Local modules
import oasa.haworth.multiring_layout
import oasa.smiles_lib


GEOMETRY_RELATIVE_TOLERANCE = 0.08
"""Relative target-length tolerance for direct glycosidic bridge bonds."""

NONBONDED_CLEARANCE_RATIO = 0.35
"""Minimum nonbonded atom clearance, relative to requested bond length."""


#============================================
def prepare_direct_glycosidic_haworth(
		smiles: str, bond_length: float=30.0) -> object:
	"""Return a detached complete Haworth depiction from one compatible SMILES.

	Args:
		smiles: One structural SMILES with exactly two supported directly linked
			pyranose or furanose rings.
		bond_length: Positive finite drawing-unit length for the planned rings.

	Raises:
		ValueError: If the input is malformed or outside the direct-glycosidic
			production profile.
	"""
	if not isinstance(smiles, str) or not smiles.strip():
		raise ValueError("Direct disaccharide Haworth SMILES must be non-empty text")
	if not _finite_positive(bond_length):
		raise ValueError("Direct disaccharide Haworth bond_length must be finite and positive")
	try:
		molecule = oasa.smiles_lib.text_to_mol(smiles, calc_coords=1)
	except (ArithmeticError, RuntimeError, TypeError, ValueError) as error:
		raise ValueError("Direct disaccharide Haworth SMILES could not be parsed") from error
	if molecule is None or not molecule.vertices:
		raise ValueError("Direct disaccharide Haworth SMILES could not be parsed")
	plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(
		molecule, bond_length=bond_length,
	)
	apply_direct_glycosidic_haworth(molecule, plan, bond_length=bond_length)
	return molecule


#============================================
def apply_direct_glycosidic_haworth(
		molecule: object,
		plan: oasa.haworth.multiring_layout.DirectGlycosidicDisaccharidePlan,
		bond_length: float=30.0) -> None:
	"""Apply one exact complete plan atomically to a detached OASA molecule.

	All coordinates, bond endpoint ordering, styles, and property records are
	validated before the final assignment loop.  Rejection therefore leaves the
	caller-owned candidate unchanged.
	"""
	if not isinstance(plan, oasa.haworth.multiring_layout.DirectGlycosidicDisaccharidePlan):
		raise ValueError("Direct disaccharide Haworth plan is invalid")
	if not _finite_positive(bond_length):
		raise ValueError("Direct disaccharide Haworth bond_length must be finite and positive")
	if not plan.matches_molecule_topology(molecule):
		raise ValueError("Direct disaccharide Haworth plan does not match the unchanged molecule")
	_source_coordinates(molecule)
	coordinates = _complete_coordinates(molecule, plan)
	styles = _ring_styles(molecule, plan)
	_validate_complete_geometry(molecule, plan, coordinates, bond_length)
	_validate_styles(molecule, plan, styles)
	_apply_complete_candidate(molecule, coordinates, styles)


#============================================
def _finite_positive(value: object) -> bool:
	"""Return whether one drawing scalar is a finite strictly positive number."""
	result = type(value) in (int, float) and math.isfinite(float(value)) and value > 0
	return result


#============================================
def _source_coordinates(molecule: object) -> dict[object, tuple[float, float]]:
	"""Return the complete finite RDKit-backed source coordinate baseline."""
	coordinates = {}
	for atom in molecule.vertices:
		if not _finite_coordinate(atom.x) or not _finite_coordinate(atom.y):
			raise ValueError("Direct disaccharide Haworth requires finite RDKit source coordinates")
		coordinates[atom] = (float(atom.x), float(atom.y))
	return coordinates


#============================================
def _finite_coordinate(value: object) -> bool:
	"""Return whether one coordinate is a finite builtin scalar."""
	result = type(value) in (int, float) and math.isfinite(float(value))
	return result


#============================================
def _complete_coordinates(
		molecule: object,
		plan: oasa.haworth.multiring_layout.DirectGlycosidicDisaccharidePlan,
		) -> dict[object, tuple[float, float]]:
	"""Build all ring, bridge, and exterior-component coordinates without mutation."""
	source = _source_coordinates(molecule)
	left_atoms = tuple(molecule.vertices[index] for index in plan.left_ring.vertex_indexes)
	right_atoms = tuple(molecule.vertices[index] for index in plan.right_ring.vertex_indexes)
	ring_sets = (set(left_atoms), set(right_atoms))
	bridge = molecule.vertices[plan.bridge.oxygen_vertex_index]
	coordinates = dict(source)
	for ring, atoms in ((plan.left_ring, left_atoms), (plan.right_ring, right_atoms)):
		for atom, coordinate in zip(atoms, ring.coordinates, strict=True):
			coordinates[atom] = coordinate
	coordinates[bridge] = plan.bridge.coordinate
	transforms = []
	for ring_plan in (plan.left_ring, plan.right_ring):
		transform = _best_similarity_transform(
			tuple(source[atom] for atom in (molecule.vertices[index] for index in ring_plan.vertex_indexes)),
			ring_plan.coordinates,
		)
		transforms.append(transform)
	for component in _exterior_components(molecule, ring_sets, bridge):
		owner_index = _component_owner(component, ring_sets, bridge)
		for atom in component:
			coordinates[atom] = _apply_similarity(source[atom], transforms[owner_index])
	return coordinates


#============================================
def _exterior_components(
		molecule: object, ring_sets: tuple[set[object], set[object]], bridge: object,
		) -> tuple[tuple[object, ...], ...]:
	"""Partition non-ring, non-bridge atoms into deterministic connected components."""
	excluded = ring_sets[0] | ring_sets[1] | {bridge}
	remaining = set(molecule.vertices) - excluded
	components = []
	while remaining:
		start = min(remaining, key=molecule.vertices.index)
		stack = [start]
		component = []
		remaining.remove(start)
		while stack:
			atom = stack.pop()
			component.append(atom)
			for neighbor in atom.neighbors:
				if neighbor in remaining:
					remaining.remove(neighbor)
					stack.append(neighbor)
		components.append(tuple(component))
	return tuple(components)


#============================================
def _component_owner(
		component: tuple[object, ...], ring_sets: tuple[set[object], set[object]], bridge: object,
		) -> int:
	"""Return a component's unique ring owner or reject unsupported attachment."""
	attachments = set()
	for atom in component:
		for neighbor in atom.neighbors:
			if neighbor is bridge:
				raise ValueError("Direct disaccharide Haworth does not support bridge substituents")
			for index, ring_atoms in enumerate(ring_sets):
				if neighbor in ring_atoms:
					attachments.add((index, neighbor))
	if len(attachments) != 1:
		raise ValueError("Direct disaccharide Haworth exterior component has ambiguous ring ownership")
	owner_index, _attachment = attachments.pop()
	return owner_index


#============================================
def _best_similarity_transform(
		source: tuple[tuple[float, float], ...], target: tuple[tuple[float, float], ...],
		) -> tuple[complex, complex, bool]:
	"""Return the lower-residual finite similarity, allowing one reflection."""
	if len(source) != len(target) or len(source) < 2:
		raise ValueError("Direct disaccharide Haworth ring correspondence is invalid")
	candidates = (
		_fit_similarity(source, target, reflected=False),
		_fit_similarity(source, target, reflected=True),
	)
	finite = [candidate for candidate in candidates if candidate is not None]
	if not finite:
		raise ValueError("Direct disaccharide Haworth source ring is degenerate")
	best = min(finite, key=lambda candidate: _similarity_residual(source, target, candidate))
	return best


#============================================
def _fit_similarity(
		source: tuple[tuple[float, float], ...], target: tuple[tuple[float, float], ...], reflected: bool,
		) -> tuple[complex, complex, bool] | None:
	"""Fit target = offset + factor * source, optionally after reflection."""
	source_values = [complex(x, y) for x, y in source]
	target_values = [complex(x, y) for x, y in target]
	if reflected:
		source_values = [value.conjugate() for value in source_values]
	source_center = sum(source_values) / len(source_values)
	target_center = sum(target_values) / len(target_values)
	denominator = sum(abs(value - source_center) ** 2 for value in source_values)
	if denominator <= 0.0 or not math.isfinite(denominator):
		return None
	factor = sum(
		(target_value - target_center) * (source_value - source_center).conjugate()
		for source_value, target_value in zip(source_values, target_values, strict=True)
	) / denominator
	offset = target_center - (factor * source_center)
	if not all(math.isfinite(value) for value in (factor.real, factor.imag, offset.real, offset.imag)):
		return None
	result = (factor, offset, reflected)
	return result


#============================================
def _similarity_residual(
		source: tuple[tuple[float, float], ...], target: tuple[tuple[float, float], ...],
		transform: tuple[complex, complex, bool],
		) -> float:
	"""Return the squared positional residual for one candidate transform."""
	value = sum(
		_distance_squared(_apply_similarity(point, transform), target_point)
		for point, target_point in zip(source, target, strict=True)
	)
	return value


#============================================
def _apply_similarity(
		coordinate: tuple[float, float], transform: tuple[complex, complex, bool],
		) -> tuple[float, float]:
	"""Apply one prevalidated similarity to a complete exterior component."""
	factor, offset, reflected = transform
	value = complex(coordinate[0], coordinate[1])
	if reflected:
		value = value.conjugate()
	result = factor * value + offset
	coordinate_result = (float(result.real), float(result.imag))
	return coordinate_result


#============================================
def _ring_styles(
		molecule: object,
		plan: oasa.haworth.multiring_layout.DirectGlycosidicDisaccharidePlan,
		) -> tuple[tuple[object, object, object, str, str], ...]:
	"""Build deterministic q/w/n styles with directed narrow ends on the q edge."""
	styles = []
	for ring in (plan.left_ring, plan.right_ring):
		atoms = tuple(molecule.vertices[index] for index in ring.vertex_indexes)
		bonds = tuple(
			molecule.get_edge_between(atom, atoms[(index + 1) % len(atoms)])
			for index, atom in enumerate(atoms)
		)
		if any(bond is None for bond in bonds):
			raise ValueError("Direct disaccharide Haworth ring edge is absent")
		q_index = ring.front_edge_index % len(bonds)
		q_start = atoms[q_index]
		q_end = atoms[(q_index + 1) % len(atoms)]
		for index, bond in enumerate(bonds):
			if index == q_index:
				styles.append((bond, q_start, q_end, "q", "front"))
			elif index in ((q_index - 1) % len(bonds), (q_index + 1) % len(bonds)):
				first = atoms[index]
				second = atoms[(index + 1) % len(atoms)]
				shared = ({first, second} & {q_start, q_end}).pop()
				outer = second if first is shared else first
				styles.append((bond, outer, shared, "w", "front"))
			else:
				styles.append((bond, atoms[index], atoms[(index + 1) % len(atoms)], "n", "back"))
	return tuple(styles)


#============================================
def _validate_complete_geometry(
		molecule: object,
		plan: oasa.haworth.multiring_layout.DirectGlycosidicDisaccharidePlan,
		coordinates: dict[object, tuple[float, float]], bond_length: float,
		) -> None:
	"""Validate the complete candidate before any coordinate or style mutation."""
	if len(coordinates) != len(molecule.vertices) or any(
		not _finite_coordinate(value) for coordinate in coordinates.values() for value in coordinate
	):
		raise ValueError("Direct disaccharide Haworth candidate coordinates must be complete and finite")
	for bond in molecule.edges:
		first, second = bond.vertices
		if _distance(coordinates[first], coordinates[second]) <= 0.0:
			raise ValueError("Direct disaccharide Haworth candidate has a zero-length bond")
	bridge = molecule.vertices[plan.bridge.oxygen_vertex_index]
	for index in (plan.bridge.left_attachment_vertex_index, plan.bridge.right_attachment_vertex_index):
		length = _distance(coordinates[bridge], coordinates[molecule.vertices[index]])
		if not _relative_close(length, bond_length, GEOMETRY_RELATIVE_TOLERANCE):
			raise ValueError("Direct disaccharide Haworth bridge bond did not meet target scale")
	_clear_nonincident_crossings(molecule, coordinates)
	_clear_nonbonded_atoms(molecule, coordinates, bond_length)


#============================================
def _relative_close(value: float, target: float, tolerance: float) -> bool:
	"""Compare positive drawing values through the centralized relative policy."""
	result = abs(value - target) <= tolerance * max(abs(value), abs(target))
	return result


#============================================
def _clear_nonbonded_atoms(
		molecule: object, coordinates: dict[object, tuple[float, float]],
		bond_length: float,
		) -> None:
	"""Reject candidates whose nonbonded atoms violate the scale-relative gate."""
	minimum = NONBONDED_CLEARANCE_RATIO * bond_length
	for index, first in enumerate(molecule.vertices):
		for second in molecule.vertices[index + 1:]:
			if molecule.get_edge_between(first, second) is not None:
				continue
			if _distance(coordinates[first], coordinates[second]) < minimum:
				raise ValueError("Direct disaccharide Haworth candidate failed nonbonded clearance")


#============================================
def _clear_nonincident_crossings(
		molecule: object, coordinates: dict[object, tuple[float, float]],
		) -> None:
	"""Reject proper crossings between any pair of nonincident graph edges."""
	bonds = tuple(molecule.edges)
	for index, first_bond in enumerate(bonds):
		first_start, first_end = first_bond.vertices
		for second_bond in bonds[index + 1:]:
			second_start, second_end = second_bond.vertices
			if {first_start, first_end} & {second_start, second_end}:
				continue
			if _properly_intersects(
				coordinates[first_start], coordinates[first_end],
				coordinates[second_start], coordinates[second_end],
			):
				raise ValueError("Direct disaccharide Haworth candidate has nonincident bond crossings")


#============================================
def _properly_intersects(
		first_start: tuple[float, float], first_end: tuple[float, float],
		second_start: tuple[float, float], second_end: tuple[float, float],
		) -> bool:
	"""Return whether two nonincident finite segments properly intersect."""
	first_a = _orientation(first_start, first_end, second_start)
	first_b = _orientation(first_start, first_end, second_end)
	second_a = _orientation(second_start, second_end, first_start)
	second_b = _orientation(second_start, second_end, first_end)
	result = first_a * first_b < 0.0 and second_a * second_b < 0.0
	return result


#============================================
def _orientation(
		start: tuple[float, float], end: tuple[float, float],
		point: tuple[float, float],
		) -> float:
	"""Return the central signed-area predicate used for crossing checks."""
	value = (
		((end[0] - start[0]) * (point[1] - start[1]))
		- ((end[1] - start[1]) * (point[0] - start[0]))
	)
	return value


#============================================
def _validate_styles(
		molecule: object, plan: object,
		styles: tuple[tuple[object, object, object, str, str], ...],
		) -> None:
	"""Validate one q plus two adjacent directed w edges for each planned ring."""
	for ring in (plan.left_ring, plan.right_ring):
		ring_atoms = {molecule.vertices[index] for index in ring.vertex_indexes}
		ring_styles = [entry for entry in styles if set(entry[0].vertices) <= ring_atoms]
		q_entries = [entry for entry in ring_styles if entry[3] == "q"]
		w_entries = [entry for entry in ring_styles if entry[3] == "w"]
		if len(q_entries) != 1 or len(w_entries) != 2:
			raise ValueError("Direct disaccharide Haworth style policy requires one q and two w edges")
		q_vertices = set(q_entries[0][0].vertices)
		if any(entry[2] not in q_vertices for entry in w_entries):
			raise ValueError("Direct disaccharide Haworth wedge direction is invalid")


#============================================
def _apply_complete_candidate(
		molecule: object, coordinates: dict[object, tuple[float, float]],
		styles: tuple[tuple[object, object, object, str, str], ...],
		) -> None:
	"""Perform the sole mutation stage after all complete-candidate validation."""
	for atom in molecule.vertices:
		atom.x, atom.y = coordinates[atom]
	for bond, first, second, style, position in styles:
		bond.type = style
		bond.properties_["haworth_position"] = position
		if style == "w":
			bond.set_vertices((first, second))


#============================================
def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
	"""Return the Euclidean distance between two finite 2D drawing points."""
	result = math.hypot(first[0] - second[0], first[1] - second[1])
	return result


#============================================
def _distance_squared(first: tuple[float, float], second: tuple[float, float]) -> float:
	"""Return squared 2D distance for transform-residual comparison."""
	result = ((first[0] - second[0]) ** 2) + ((first[1] - second[1]) ** 2)
	return result
