"""Explicit durable-ID planning for three-ring Haworth assemblies.

This module deliberately accepts declared ring and linkage facts.  It is not a
carbohydrate recognizer: callers select the rings, attachments, connector
atoms, and drawing directions before asking OASA to make a depiction.
"""

# Standard Library
import dataclasses
import math

# Local modules
import oasa.haworth.layout
import oasa.haworth.renderer_config


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthAtomRef:
	"""One persistent atom address in a detached CDML molecule."""

	molecule_id: str
	atom_id: str


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthRingDeclaration:
	"""One explicitly ordered 5/6-member C/O ring."""

	ring_id: str
	vertices: tuple[HaworthAtomRef, ...]
	orientation: str
	front_face: str


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthLinkDeclaration:
	"""One declared parent-to-child graph path and its drawing direction."""

	link_id: str
	parent_ring_id: str
	parent_attachment: HaworthAtomRef
	child_ring_id: str
	child_attachment: HaworthAtomRef
	connector_atoms: tuple[HaworthAtomRef, ...]
	direction: str


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthAssemblyRequest:
	"""Complete explicit input for exactly one three-ring rooted tree."""

	molecule_id: str
	root_ring_id: str
	rings: tuple[HaworthRingDeclaration, ...]
	links: tuple[HaworthLinkDeclaration, ...]
	bond_length: float=30.0


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthAssemblyRingPlan:
	"""One laid-out ring with the original durable vertex references."""

	ring_id: str
	vertex_refs: tuple[HaworthAtomRef, ...]
	coordinates: tuple[tuple[float, float], ...]
	front_edge_index: int


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthAssemblyLinkPlan:
	"""Coordinates for the declared connector atoms in one linkage."""

	link_id: str
	connector_refs: tuple[HaworthAtomRef, ...]
	coordinates: tuple[tuple[float, float], ...]


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthAssemblyPlan:
	"""Immutable plan guarded by complete durable topology fingerprints."""

	request: HaworthAssemblyRequest
	rings: tuple[HaworthAssemblyRingPlan, ...]
	links: tuple[HaworthAssemblyLinkPlan, ...]
	atom_topology_fingerprint: tuple[tuple[str, str, str], ...]
	bond_topology_fingerprint: tuple[tuple[str, str, int, bool], ...]

	#============================================
	def matches_molecule_topology(self, molecule: object) -> bool:
		"""Return whether every durable atom and bond fact is unchanged."""
		result = (
			_atom_fingerprint(molecule) == self.atom_topology_fingerprint
			and _bond_fingerprint(molecule) == self.bond_topology_fingerprint)
		return result


#============================================
class HaworthAssemblyError(ValueError):
	"""Base error for the explicit three-ring Haworth profile."""


class HaworthAssemblyIdentityError(HaworthAssemblyError):
	"""A durable ID is missing, empty, duplicated, or cross-molecule."""


class HaworthAssemblyDeclarationError(HaworthAssemblyError):
	"""The supplied three-ring tree declarations are incomplete or conflicting."""


class HaworthAssemblyTopologyError(HaworthAssemblyError):
	"""Declared graph facts do not describe the actual supported molecule."""


class HaworthAssemblyGeometryError(HaworthAssemblyError):
	"""A fully declared drawing cannot be placed without invalid geometry."""


class HaworthAssemblyApplicationError(HaworthAssemblyError):
	"""A previously planned molecule changed before atomic application."""


#============================================
def plan_haworth_assembly(
		molecule: object, request: HaworthAssemblyRequest) -> HaworthAssemblyPlan:
	"""Plan one explicit linear or branched three-ring Haworth tree.

	Args:
		molecule: Detached OASA molecule with persistent molecule and atom IDs.
		request: Complete ring, connector, and drawing-direction declarations.

	Returns:
		An immutable plan that can be applied only to the unchanged molecule.
	"""
	_validate_request_identity(molecule, request)
	rings_by_id = {ring.ring_id: ring for ring in request.rings}
	atoms_by_ref = _atom_map(molecule)
	_validate_disjoint_ring_refs(request.rings)
	for ring in request.rings:
		_validate_ring(molecule, ring, atoms_by_ref)
	_validate_links(molecule, request, rings_by_id, atoms_by_ref)
	_validate_exterior_topology(molecule, request, rings_by_id, atoms_by_ref)
	ordered_links = _tree_links(request, rings_by_id)
	ring_plans = _layout_rings(request, rings_by_id, ordered_links, atoms_by_ref)
	link_plans = _layout_links(request, ordered_links, ring_plans, atoms_by_ref)
	_validate_geometry(molecule, ring_plans, link_plans, atoms_by_ref, request.bond_length)
	_validate_link_lengths(request, ring_plans, link_plans)
	plan = HaworthAssemblyPlan(
		request=request,
		rings=tuple(ring_plans[ring.ring_id] for ring in request.rings),
		links=tuple(link_plans[link.link_id] for link in request.links),
		atom_topology_fingerprint=_atom_fingerprint(molecule),
		bond_topology_fingerprint=_bond_fingerprint(molecule),
	)
	return plan


#============================================
def apply_haworth_assembly(molecule: object, plan: HaworthAssemblyPlan) -> None:
	"""Atomically apply one unchanged explicit three-ring plan.

	Every assignment is deferred until coordinates and directed Haworth styles
	are complete and valid, so a rejection leaves the caller-owned molecule
	unchanged.
	"""
	if not isinstance(plan, HaworthAssemblyPlan):
		raise HaworthAssemblyApplicationError("Haworth assembly plan is invalid")
	if not plan.matches_molecule_topology(molecule):
		raise HaworthAssemblyApplicationError("Haworth assembly plan does not match molecule topology")
	atoms_by_ref = _atom_map(molecule)
	coordinates = _plan_coordinates(plan, atoms_by_ref)
	styles = _plan_styles(molecule, plan, atoms_by_ref)
	_validate_geometry(molecule, _plan_ring_map(plan), _plan_link_map(plan), atoms_by_ref,
		plan.request.bond_length)
	_validate_link_lengths(plan.request, _plan_ring_map(plan), _plan_link_map(plan))
	for atom, coordinate in coordinates.items():
		atom.x, atom.y = coordinate
	for bond, first, second, style, position in styles:
		bond.type = style
		bond.properties_["haworth_position"] = position
		if style == "w":
			bond.set_vertices((first, second))


#============================================
def _validate_request_identity(molecule: object, request: HaworthAssemblyRequest) -> None:
	"""Validate fixed cardinality and all durable molecule-level identifiers."""
	if not isinstance(request, HaworthAssemblyRequest):
		raise HaworthAssemblyDeclarationError("Haworth assembly request is invalid")
	if not _finite_positive(request.bond_length):
		raise HaworthAssemblyDeclarationError("Haworth assembly bond_length must be finite and positive")
	if (not isinstance(molecule.id, str) or not molecule.id.strip()
			or molecule.id != request.molecule_id):
		raise HaworthAssemblyIdentityError("Haworth assembly molecule ID does not match")
	if len(request.rings) != 3 or len(request.links) != 2:
		raise HaworthAssemblyDeclarationError(
			"Haworth assembly requires exactly three rings and two links")
	ring_ids = tuple(ring.ring_id for ring in request.rings)
	if request.root_ring_id not in ring_ids or len(set(ring_ids)) != len(ring_ids):
		raise HaworthAssemblyDeclarationError(
			"Haworth assembly ring IDs must be unique and include the root")
	if any(not isinstance(value, str) or not value.strip() for value in ring_ids):
		raise HaworthAssemblyIdentityError("Haworth assembly ring IDs must be non-empty")
	link_ids = tuple(link.link_id for link in request.links)
	if len(set(link_ids)) != len(link_ids) or any(not value.strip() for value in link_ids):
		raise HaworthAssemblyIdentityError("Haworth assembly link IDs must be unique and non-empty")
	_atom_map(molecule)


#============================================
def _atom_map(molecule: object) -> dict[HaworthAtomRef, object]:
	"""Resolve the molecule's complete CDML-compatible durable atom namespace."""
	if not isinstance(molecule.id, str) or not molecule.id.strip():
		raise HaworthAssemblyIdentityError("Haworth assembly requires a non-empty molecule ID")
	result = {}
	for atom in molecule.vertices:
		if not isinstance(atom.id, str) or not atom.id.strip():
			raise HaworthAssemblyIdentityError("Haworth assembly requires non-empty atom IDs")
		ref = HaworthAtomRef(molecule.id, atom.id)
		if ref in result:
			raise HaworthAssemblyIdentityError("Haworth assembly atom IDs must be unique")
		result[ref] = atom
	return result


#============================================
def _validate_ring(
		molecule: object, ring: HaworthRingDeclaration,
		atoms_by_ref: dict[HaworthAtomRef, object]) -> None:
	"""Require one declared simple all-single C/O cycle without discovery."""
	if ring.orientation not in ("canonical", "mirrored") or ring.front_face != "front":
		raise HaworthAssemblyDeclarationError("Haworth assembly ring depiction declaration is invalid")
	if len(ring.vertices) not in (5, 6) or len(set(ring.vertices)) != len(ring.vertices):
		raise HaworthAssemblyTopologyError("Haworth assembly ring must have unique five or six vertices")
	atoms = tuple(_resolve_ref(ref, atoms_by_ref) for ref in ring.vertices)
	if (any(atom.symbol not in ("C", "O") for atom in atoms)
			or sum(atom.symbol == "O" for atom in atoms) != 1):
		raise HaworthAssemblyTopologyError("Haworth assembly ring must contain one oxygen and carbons")
	for index, atom in enumerate(atoms):
		next_atom = atoms[(index + 1) % len(atoms)]
		bond = molecule.get_edge_between(atom, next_atom)
		if not _single_non_aromatic(bond):
			raise HaworthAssemblyTopologyError("Haworth assembly declared ring edge is invalid")
		ring_neighbors = tuple(neighbor for neighbor in atom.neighbors if neighbor in atoms)
		if len(ring_neighbors) != 2:
			raise HaworthAssemblyTopologyError("Haworth assembly ring must be a simple cycle")


#============================================
def _validate_disjoint_ring_refs(rings: tuple[HaworthRingDeclaration, ...]) -> None:
	"""Reject fused or spiro declarations before treating cycles independently."""
	declared = set()
	for ring in rings:
		for ref in ring.vertices:
			if ref in declared:
				raise HaworthAssemblyTopologyError(
					"Haworth assembly rings must be vertex-disjoint")
			declared.add(ref)


#============================================
def _validate_links(
		molecule: object, request: HaworthAssemblyRequest,
		rings_by_id: dict[str, HaworthRingDeclaration],
		atoms_by_ref: dict[HaworthAtomRef, object]) -> None:
	"""Validate every exact connector path and reject reused attachments."""
	used_connectors = set()
	used_attachments = set()
	for link in request.links:
		if link.parent_ring_id not in rings_by_id or link.child_ring_id not in rings_by_id:
			raise HaworthAssemblyDeclarationError("Haworth assembly link names an unknown ring")
		if link.parent_ring_id == link.child_ring_id or link.direction not in _DIRECTIONS:
			raise HaworthAssemblyDeclarationError("Haworth assembly link declaration is invalid")
		parent = _resolve_ref(link.parent_attachment, atoms_by_ref)
		child = _resolve_ref(link.child_attachment, atoms_by_ref)
		if link.parent_attachment not in rings_by_id[link.parent_ring_id].vertices:
			raise HaworthAssemblyTopologyError("Haworth assembly parent attachment is outside its ring")
		if link.child_attachment not in rings_by_id[link.child_ring_id].vertices:
			raise HaworthAssemblyTopologyError("Haworth assembly child attachment is outside its ring")
		if parent.symbol != "C" or child.symbol != "C":
			raise HaworthAssemblyTopologyError("Haworth assembly attachments must be ring carbons")
		if link.parent_attachment in used_attachments or link.child_attachment in used_attachments:
			raise HaworthAssemblyDeclarationError("Haworth assembly attachments cannot be reused")
		used_attachments.update((link.parent_attachment, link.child_attachment))
		if len(set(link.connector_atoms)) != len(link.connector_atoms):
			raise HaworthAssemblyTopologyError("Haworth assembly connector atoms must be unique")
		if used_connectors & set(link.connector_atoms):
			raise HaworthAssemblyTopologyError("Haworth assembly connector atoms cannot be reused")
		used_connectors.update(link.connector_atoms)
		path = ((parent,) + tuple(_resolve_ref(ref, atoms_by_ref)
			for ref in link.connector_atoms) + (child,))
		if any(atom in _all_ring_atoms(rings_by_id, atoms_by_ref) for atom in path[1:-1]):
			raise HaworthAssemblyTopologyError("Haworth assembly connector may not enter a declared ring")
		for first, second in zip(path, path[1:]):
			if not _single_non_aromatic(molecule.get_edge_between(first, second)):
				raise HaworthAssemblyTopologyError(
					"Haworth assembly connector path is not an actual single-bond path")
		for connector in path[1:-1]:
			if connector.degree != 2:
				raise HaworthAssemblyTopologyError(
					"Haworth assembly connector may not have undeclared branches")


#============================================
def _validate_exterior_topology(
		molecule: object, request: HaworthAssemblyRequest,
		rings_by_id: dict[str, HaworthRingDeclaration],
		atoms_by_ref: dict[HaworthAtomRef, object]) -> None:
	"""Reject undeclared bridges between rings and connector-side branches.

	The declared link paths are the only supported exterior connections between
	rings.  Remaining exterior components may be ordinary substituents, but each
	must meet at most one declared ring and no planned connector.
	"""
	ring_by_atom = {}
	for ring in rings_by_id.values():
		for ref in ring.vertices:
			ring_by_atom[atoms_by_ref[ref]] = ring.ring_id
	connector_atoms = {
		atoms_by_ref[ref] for link in request.links for ref in link.connector_atoms}
	allowed_direct_edges = {
		frozenset((atoms_by_ref[link.parent_attachment], atoms_by_ref[link.child_attachment]))
		for link in request.links if not link.connector_atoms}
	for bond in molecule.edges:
		first, second = bond.vertices
		first_ring = ring_by_atom.get(first)
		second_ring = ring_by_atom.get(second)
		if first_ring and second_ring and first_ring != second_ring:
			if frozenset((first, second)) not in allowed_direct_edges:
				raise HaworthAssemblyTopologyError(
					"Haworth assembly rings have an undeclared exterior bridge")
	exterior_atoms = set(molecule.vertices) - set(ring_by_atom) - connector_atoms
	while exterior_atoms:
		pending = [exterior_atoms.pop()]
		component = set(pending)
		while pending:
			atom = pending.pop()
			for neighbor in atom.neighbors:
				if neighbor in exterior_atoms:
					exterior_atoms.remove(neighbor)
					component.add(neighbor)
					pending.append(neighbor)
		ring_neighbors = {
			ring_by_atom[neighbor] for atom in component for neighbor in atom.neighbors
			if neighbor in ring_by_atom}
		if any(neighbor in connector_atoms for atom in component for neighbor in atom.neighbors):
			raise HaworthAssemblyTopologyError(
				"Haworth assembly exterior component may not touch a connector")
		if len(ring_neighbors) > 1:
			raise HaworthAssemblyTopologyError(
				"Haworth assembly exterior component may not bridge declared rings")


#============================================
def _tree_links(
		request: HaworthAssemblyRequest,
		rings_by_id: dict[str, HaworthRingDeclaration]) -> tuple[HaworthLinkDeclaration, ...]:
	"""Return stable rooted link order after proving exact three-node tree incidence."""
	parents = {}
	child_directions = set()
	for link in request.links:
		if link.child_ring_id in parents:
			raise HaworthAssemblyTopologyError("Haworth assembly child ring has multiple parents")
		parents[link.child_ring_id] = link.parent_ring_id
		key = (link.parent_ring_id, link.direction)
		if key in child_directions:
			raise HaworthAssemblyDeclarationError("Haworth assembly sibling directions must differ")
		child_directions.add(key)
	if request.root_ring_id in parents or set(parents) != set(rings_by_id) - {request.root_ring_id}:
		raise HaworthAssemblyTopologyError("Haworth assembly links must form one rooted tree")
	ordered = []
	seen = {request.root_ring_id}
	remaining = list(request.links)
	while remaining:
		ready = [link for link in remaining if link.parent_ring_id in seen]
		if not ready:
			raise HaworthAssemblyTopologyError("Haworth assembly links are not reachable from the root")
		ready.sort(key=lambda link: (link.parent_ring_id, link.direction, link.link_id))
		for link in ready:
			seen.add(link.child_ring_id)
			remaining.remove(link)
			ordered.append(link)
	return tuple(ordered)


#============================================
def _layout_rings(
		request: HaworthAssemblyRequest, rings_by_id: dict[str, HaworthRingDeclaration],
		ordered_links: tuple[HaworthLinkDeclaration, ...],
		atoms_by_ref: dict[HaworthAtomRef, object]) -> dict[str, HaworthAssemblyRingPlan]:
	"""Place rotation-constrained rings then translate the rooted tree."""
	rotations = _ring_rotations(request, rings_by_id)
	root = _ring_template_plan(rings_by_id[request.root_ring_id], request.bond_length)
	result = {request.root_ring_id: _rotate_ring_plan(root, rotations[request.root_ring_id])}
	for link in ordered_links:
		parent_plan = result[link.parent_ring_id]
		parent_index = parent_plan.vertex_refs.index(link.parent_attachment)
		parent_coordinate = parent_plan.coordinates[parent_index]
		direction = _DIRECTIONS[link.direction]
		separation = (len(link.connector_atoms) + 1) * request.bond_length
		child = _ring_template_plan(rings_by_id[link.child_ring_id], request.bond_length)
		child_plan = _rotate_ring_plan(child, rotations[link.child_ring_id])
		child_index = child_plan.vertex_refs.index(link.child_attachment)
		target = (
			parent_coordinate[0] + (direction[0] * separation),
			parent_coordinate[1] + (direction[1] * separation),
		)
		origin = child_plan.coordinates[child_index]
		translated = tuple((point[0] + target[0] - origin[0], point[1] + target[1] - origin[1])
			for point in child_plan.coordinates)
		result[link.child_ring_id] = dataclasses.replace(child_plan, coordinates=translated)
	return result


#============================================
def _ring_rotations(request: HaworthAssemblyRequest,
		rings_by_id: dict[str, HaworthRingDeclaration]) -> dict[str, float]:
	"""Solve each ring's explicit incoming and outgoing face constraints.

	The legacy Haworth templates are intentionally non-regular, so two distinct
	vertex normals cannot always meet two cardinal directions exactly after one
	rigid rotation.  We therefore use the minimax rotation and admit only the
	template-derived residual needed for a compatible cardinal pair.
	"""
	constraints = {ring_id: [] for ring_id in rings_by_id}
	for link in request.links:
		constraints[link.parent_ring_id].append((link.parent_attachment, _DIRECTIONS[link.direction]))
		constraints[link.child_ring_id].append(
			(link.child_attachment, tuple(-value for value in _DIRECTIONS[link.direction])))
	result = {}
	for ring_id, ring_constraints in constraints.items():
		template = _ring_template_plan(rings_by_id[ring_id], request.bond_length)
		if not ring_constraints:
			result[ring_id] = 0.0
			continue
		required_rotations = tuple(
			_angle(direction) - _angle(_attachment_outward_direction(
				template.coordinates, template.vertex_refs.index(ref)))
			for ref, direction in ring_constraints)
		rotation = _minimax_rotation(required_rotations)
		rotated = _rotate_ring_plan(template, rotation)
		for constrained_ref, target in ring_constraints:
			actual = _attachment_outward_direction(
				rotated.coordinates, rotated.vertex_refs.index(constrained_ref))
			if abs(_signed_angle(_angle(actual) - _angle(target))) > _FACE_ALIGNMENT_TOLERANCE:
				raise HaworthAssemblyGeometryError(
					"Haworth assembly attachment faces conflict with declared directions")
		result[ring_id] = rotation
	return result


#============================================
def _rotate_ring_plan(plan: HaworthAssemblyRingPlan, angle: float) -> HaworthAssemblyRingPlan:
	"""Rotate one immutable template around the origin without changing its IDs."""
	cosine = math.cos(angle)
	sine = math.sin(angle)
	coordinates = tuple(
		((point[0] * cosine) - (point[1] * sine), (point[0] * sine) + (point[1] * cosine))
		for point in plan.coordinates)
	result = dataclasses.replace(plan, coordinates=coordinates)
	return result


#============================================
def _attachment_outward_direction(coordinates: tuple[tuple[float, float], ...],
		index: int) -> tuple[float, float]:
	"""Return the template-centre radial face direction at one attachment."""
	center = (
		sum(point[0] for point in coordinates) / len(coordinates),
		sum(point[1] for point in coordinates) / len(coordinates),
	)
	point = coordinates[index]
	result = _unit_vector(point[0] - center[0], point[1] - center[1])
	return result


#============================================
def _unit_vector(x_value: float, y_value: float) -> tuple[float, float]:
	"""Normalize one nonzero finite geometry vector."""
	length = math.hypot(x_value, y_value)
	if not math.isfinite(length) or length <= 0.0:
		raise HaworthAssemblyGeometryError("Haworth assembly attachment direction is invalid")
	result = (x_value / length, y_value / length)
	return result


#============================================
def _angle(vector: tuple[float, float]) -> float:
	"""Return one screen-coordinate direction angle."""
	result = math.atan2(vector[1], vector[0])
	return result


#============================================
def _minimax_rotation(required_rotations: tuple[float, ...]) -> float:
	"""Return the circular midpoint that minimizes the largest face residual."""
	if len(required_rotations) == 1:
		return required_rotations[0]
	if len(required_rotations) != 2:
		raise HaworthAssemblyGeometryError("Haworth assembly ring constraints are invalid")
	first, second = required_rotations
	result = first + (0.5 * _signed_angle(second - first))
	return result


#============================================
def _signed_angle(angle: float) -> float:
	"""Normalize an angle to its nearest signed turn in radians."""
	result = (angle + math.pi) % (2.0 * math.pi) - math.pi
	return result


#============================================
def _dot(first: tuple[float, float], second: tuple[float, float]) -> float:
	"""Return the two-dimensional dot product used for face agreement."""
	result = (first[0] * second[0]) + (first[1] * second[1])
	return result


#============================================
def _ring_template_plan(
		ring: HaworthRingDeclaration, bond_length: float) -> HaworthAssemblyRingPlan:
	"""Return one stable template in the caller's declared cyclic order."""
	refs = ring.vertices if ring.orientation == "canonical" else tuple(reversed(ring.vertices))
	coordinates = tuple((float(x), float(y)) for x, y in oasa.haworth.layout._ring_template(
		len(refs), bond_length=bond_length))
	ring_type = "pyranose" if len(refs) == 6 else "furanose"
	front = oasa.haworth.renderer_config.RING_RENDER_CONFIG[ring_type]["front_edge_index"]
	return HaworthAssemblyRingPlan(ring.ring_id, refs, coordinates, front)


#============================================
def _layout_links(
		request: HaworthAssemblyRequest, ordered_links: tuple[HaworthLinkDeclaration, ...],
		ring_plans: dict[str, HaworthAssemblyRingPlan],
		atoms_by_ref: dict[HaworthAtomRef, object]) -> dict[str, HaworthAssemblyLinkPlan]:
	"""Place each declared connector at exact intervals on its directed baseline."""
	result = {}
	for link in ordered_links:
		parent = ring_plans[link.parent_ring_id]
		start = parent.coordinates[parent.vertex_refs.index(link.parent_attachment)]
		direction = _DIRECTIONS[link.direction]
		coordinates = tuple(
			(start[0] + (index + 1) * request.bond_length * direction[0],
				start[1] + (index + 1) * request.bond_length * direction[1])
			for index in range(len(link.connector_atoms)))
		result[link.link_id] = HaworthAssemblyLinkPlan(link.link_id, link.connector_atoms, coordinates)
	return result


#============================================
def _plan_coordinates(
		plan: HaworthAssemblyPlan,
		atoms_by_ref: dict[HaworthAtomRef, object]) -> dict[object, tuple[float, float]]:
	"""Collect every planned coordinate while preserving unrelated atom positions."""
	result = {atom: (float(atom.x), float(atom.y)) for atom in atoms_by_ref.values()}
	for ring in plan.rings:
		for ref, coordinate in zip(ring.vertex_refs, ring.coordinates, strict=True):
			result[atoms_by_ref[ref]] = coordinate
	for link in plan.links:
		for ref, coordinate in zip(link.connector_refs, link.coordinates, strict=True):
			result[atoms_by_ref[ref]] = coordinate
	return result


#============================================
def _plan_styles(
		molecule: object, plan: HaworthAssemblyPlan,
		atoms_by_ref: dict[HaworthAtomRef, object]
		) -> tuple[tuple[object, object, object, str, str], ...]:
	"""Build one q, two directed w, and remaining n records per planned ring."""
	styles = []
	for ring in plan.rings:
		atoms = tuple(atoms_by_ref[ref] for ref in ring.vertex_refs)
		q_index = ring.front_edge_index % len(atoms)
		q_start, q_end = atoms[q_index], atoms[(q_index + 1) % len(atoms)]
		for index, first in enumerate(atoms):
			second = atoms[(index + 1) % len(atoms)]
			bond = molecule.get_edge_between(first, second)
			if bond is None:
				raise HaworthAssemblyApplicationError("Haworth assembly planned ring bond is absent")
			if index == q_index:
				styles.append((bond, q_start, q_end, "q", "front"))
			elif index in ((q_index - 1) % len(atoms), (q_index + 1) % len(atoms)):
				shared = ({first, second} & {q_start, q_end}).pop()
				outer = second if first is shared else first
				styles.append((bond, outer, shared, "w", "front"))
			else:
				styles.append((bond, first, second, "n", "back"))
	return tuple(styles)


#============================================
def _validate_geometry(molecule: object, ring_plans: dict[str, HaworthAssemblyRingPlan],
		link_plans: dict[str, HaworthAssemblyLinkPlan], atoms_by_ref: dict[HaworthAtomRef, object],
		bond_length: float) -> None:
	"""Check planned coordinates and declared link segments before mutation."""
	planned_atoms = {
		atoms_by_ref[ref] for ring in ring_plans.values() for ref in ring.vertex_refs}
	planned_atoms.update(
		atoms_by_ref[ref] for link in link_plans.values() for ref in link.connector_refs)
	coordinates = {}
	for atom in atoms_by_ref.values():
		point = (atom.x, atom.y)
		if atom not in planned_atoms and not _finite_pair(point):
			raise HaworthAssemblyGeometryError("Haworth assembly coordinates must be finite")
		if atom not in planned_atoms:
			coordinates[atom] = (float(point[0]), float(point[1]))
	for ring in ring_plans.values():
		coordinates.update(dict(zip(
			(atoms_by_ref[ref] for ref in ring.vertex_refs), ring.coordinates, strict=True)))
	for link in link_plans.values():
		coordinates.update(dict(zip(
			(atoms_by_ref[ref] for ref in link.connector_refs), link.coordinates, strict=True)))
	if any(not _finite_pair(point) for point in coordinates.values()):
		raise HaworthAssemblyGeometryError("Haworth assembly coordinates must be finite")
	for bond in molecule.edges:
		first, second = bond.vertices
		if _distance(coordinates[first], coordinates[second]) <= 0.0:
			raise HaworthAssemblyGeometryError("Haworth assembly contains a zero-length bond")
	for first, second in _nonincident_edges(molecule):
		if _properly_intersects(coordinates[first[0]], coordinates[first[1]],
			coordinates[second[0]], coordinates[second[1]]):
			raise HaworthAssemblyGeometryError("Haworth assembly has nonincident bond crossings")
	for first, second in _incident_edge_pairs(molecule):
		if _shared_endpoint_overlap(first, second, coordinates):
			raise HaworthAssemblyGeometryError("Haworth assembly has overlapping incident bond segments")
	minimum_clearance = 0.35 * bond_length
	for first, second in _nonbonded_atom_pairs(molecule):
		if _distance(coordinates[first], coordinates[second]) < minimum_clearance:
			raise HaworthAssemblyGeometryError("Haworth assembly failed nonbonded atom clearance")


#============================================
def _validate_link_lengths(request: HaworthAssemblyRequest,
		ring_plans: dict[str, HaworthAssemblyRingPlan],
		link_plans: dict[str, HaworthAssemblyLinkPlan]) -> None:
	"""Require every declared linkage bond to retain the requested drawing scale."""
	for link in request.links:
		parent = ring_plans[link.parent_ring_id]
		child = ring_plans[link.child_ring_id]
		start = parent.coordinates[parent.vertex_refs.index(link.parent_attachment)]
		end = child.coordinates[child.vertex_refs.index(link.child_attachment)]
		connector = link_plans[link.link_id].coordinates
		path = (start,) + connector + (end,)
		if any(not _relative_close(_distance(first, second), request.bond_length)
			for first, second in zip(path, path[1:])):
			raise HaworthAssemblyGeometryError("Haworth assembly link bond did not meet target scale")


#============================================
def _plan_ring_map(plan: HaworthAssemblyPlan) -> dict[str, HaworthAssemblyRingPlan]:
	"""Return immutable ring plans by durable declaration name."""
	result = {ring.ring_id: ring for ring in plan.rings}
	return result


#============================================
def _plan_link_map(plan: HaworthAssemblyPlan) -> dict[str, HaworthAssemblyLinkPlan]:
	"""Return immutable link plans by durable declaration name."""
	result = {link.link_id: link for link in plan.links}
	return result


#============================================
def _atom_fingerprint(molecule: object) -> tuple[tuple[str, str, str], ...]:
	"""Encode every durable atom identity and symbol independent of vertex order."""
	result = tuple(sorted((molecule.id, atom.id, atom.symbol) for atom in molecule.vertices))
	return result


#============================================
def _bond_fingerprint(molecule: object) -> tuple[tuple[str, str, int, bool], ...]:
	"""Encode every durable bond chemistry independent of edge or endpoint order."""
	records = []
	for bond in molecule.edges:
		first, second = sorted((bond.vertices[0].id, bond.vertices[1].id))
		records.append((first, second, int(bond.order), bool(bond.aromatic)))
	result = tuple(sorted(records))
	return result


#============================================
def _resolve_ref(ref: HaworthAtomRef, atoms_by_ref: dict[HaworthAtomRef, object]) -> object:
	"""Resolve one explicit declared atom or report its durable-ID defect."""
	if ref not in atoms_by_ref:
		raise HaworthAssemblyIdentityError("Haworth assembly atom reference is unknown")
	result = atoms_by_ref[ref]
	return result


#============================================
def _all_ring_atoms(rings_by_id: dict[str, HaworthRingDeclaration],
		atoms_by_ref: dict[HaworthAtomRef, object]) -> set[object]:
	"""Return the explicitly declared ring atoms without inferring new cycles."""
	result = set()
	for ring in rings_by_id.values():
		result.update(_resolve_ref(ref, atoms_by_ref) for ref in ring.vertices)
	return result


#============================================
def _finite_positive(value: object) -> bool:
	"""Return whether one requested drawing scalar is finite and positive."""
	result = type(value) in (int, float) and math.isfinite(float(value)) and value > 0
	return result


#============================================
def _finite_pair(point: tuple[float, float]) -> bool:
	"""Return whether both coordinates are finite builtin scalars."""
	result = all(type(value) in (int, float) and math.isfinite(float(value)) for value in point)
	return result


#============================================
def _single_non_aromatic(bond: object) -> bool:
	"""Return whether one required declared edge has supported chemistry."""
	result = bond is not None and bond.order == 1 and not bond.aromatic
	return result


#============================================
def _nonincident_edges(
		molecule: object) -> tuple[tuple[tuple[object, object], tuple[object, object]], ...]:
	"""Return deterministic nonincident edge pairs for crossing checks."""
	bonds = tuple(molecule.edges)
	result = []
	for index, first_bond in enumerate(bonds):
		first = first_bond.vertices
		for second_bond in bonds[index + 1:]:
			second = second_bond.vertices
			if not set(first) & set(second):
				result.append((first, second))
	return tuple(result)


#============================================
def _incident_edge_pairs(
		molecule: object) -> tuple[tuple[tuple[object, object], tuple[object, object]], ...]:
	"""Return edge pairs meeting at one vertex for collinear-overlap checks."""
	bonds = tuple(molecule.edges)
	result = []
	for index, first_bond in enumerate(bonds):
		first = first_bond.vertices
		for second_bond in bonds[index + 1:]:
			second = second_bond.vertices
			if len(set(first) & set(second)) == 1:
				result.append((first, second))
	return tuple(result)


#============================================
def _shared_endpoint_overlap(first: tuple[object, object], second: tuple[object, object],
		coordinates: dict[object, tuple[float, float]]) -> bool:
	"""Return whether incident collinear bonds overlap beyond their shared endpoint."""
	shared = (set(first) & set(second)).pop()
	first_other = next(atom for atom in first if atom is not shared)
	second_other = next(atom for atom in second if atom is not shared)
	base = coordinates[shared]
	first_vector = (coordinates[first_other][0] - base[0], coordinates[first_other][1] - base[1])
	second_vector = (coordinates[second_other][0] - base[0], coordinates[second_other][1] - base[1])
	cross = (first_vector[0] * second_vector[1]) - (first_vector[1] * second_vector[0])
	result = abs(cross) <= 1.0e-8 and _dot(first_vector, second_vector) > 0.0
	return result


#============================================
def _nonbonded_atom_pairs(molecule: object) -> tuple[tuple[object, object], ...]:
	"""Return atom pairs whose separation is a genuine nonbonded clearance fact."""
	atoms = tuple(molecule.vertices)
	result = []
	for index, first in enumerate(atoms):
		for second in atoms[index + 1:]:
			if molecule.get_edge_between(first, second) is None:
				result.append((first, second))
	return tuple(result)


#============================================
def _properly_intersects(first_start: tuple[float, float], first_end: tuple[float, float],
		second_start: tuple[float, float], second_end: tuple[float, float]) -> bool:
	"""Return whether two nonincident finite line segments cross properly."""
	first_a = _orientation(first_start, first_end, second_start)
	first_b = _orientation(first_start, first_end, second_end)
	second_a = _orientation(second_start, second_end, first_start)
	second_b = _orientation(second_start, second_end, first_end)
	result = first_a * first_b < 0.0 and second_a * second_b < 0.0
	return result


#============================================
def _orientation(
		start: tuple[float, float], end: tuple[float, float], point: tuple[float, float]) -> float:
	"""Return the signed-area orientation predicate for one point and edge."""
	result = ((end[0] - start[0]) * (point[1] - start[1])
		- (end[1] - start[1]) * (point[0] - start[0]))
	return result


#============================================
def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
	"""Return the Euclidean distance between two finite points."""
	result = math.hypot(first[0] - second[0], first[1] - second[1])
	return result


#============================================
def _relative_close(value: float, target: float) -> bool:
	"""Compare one positive drawing length with the shared eight-percent tolerance."""
	result = abs(value - target) <= 0.08 * max(abs(value), abs(target))
	return result


_DIRECTIONS = {
	"east": (1.0, 0.0),
	"west": (-1.0, 0.0),
	"north": (0.0, -1.0),
	"south": (0.0, 1.0),
}

def _template_face_alignment_tolerance() -> float:
	"""Return the largest minimax cardinal residual in the shipped templates.

	For every pair of distinct template vertices, this measures the smallest
	rotation error needed to map their radial-face separation to a cardinal
	separation (same, quarter, or half turn).  The bound is scale-independent
	and comes solely from the non-regular five- and six-member template shapes;
	it is not a permissive caller-selected angle.
	"""
	residuals = []
	cardinal_separations = (0.0, math.pi / 2.0, math.pi, -math.pi / 2.0)
	for ring_size in (5, 6):
		coordinates = tuple((float(x), float(y)) for x, y in oasa.haworth.layout._ring_template(
			ring_size, bond_length=30.0))
		face_angles = tuple(_angle(_attachment_outward_direction(coordinates, index))
			for index in range(ring_size))
		for first_index, first_angle in enumerate(face_angles):
			for second_index, second_angle in enumerate(face_angles):
				if first_index == second_index:
					continue
				separation = _signed_angle(second_angle - first_angle)
				residuals.append(0.5 * min(
					abs(_signed_angle(separation - cardinal))
					for cardinal in cardinal_separations))
	result = max(residuals) + 1.0e-9
	return result


_FACE_ALIGNMENT_TOLERANCE = _template_face_alignment_tolerance()
