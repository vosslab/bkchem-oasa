"""One identity-bound, fixed Haworth depiction of verified sucrose.

The preset intentionally accepts no caller-supplied chemical graph or SMILES.
It is a deterministic depiction of the module-owned PubChem CID 5988 source,
not a carbohydrate parser or a claim that OASA recovers tetrahedral chemistry.
Positive y is down, as in the rest of the Haworth layout code.
"""

# Standard Library
import dataclasses
import hashlib
import math

# Local modules
import oasa.smiles_lib


#============================================
@dataclasses.dataclass(frozen=True)
class VerifiedSucroseIdentity:
	"""The exact source identity accepted before any parser is called."""

	preset_id: str
	provenance: str
	isomeric_smiles: bytes
	sha256: str


#============================================
@dataclasses.dataclass(frozen=True)
class VerifiedSucrosePlan:
	"""Immutable role-keyed coordinates and directed Haworth bond styles."""

	coordinates: tuple[tuple[str, tuple[float, float]], ...]
	styles: tuple[tuple[str, str, str], ...]


IDENTITY = VerifiedSucroseIdentity(
	preset_id="verified_sucrose_haworth_v2",
	provenance="PubChem CID 5988 isomeric SMILES, recorded 2026-07-29",
	isomeric_smiles=(
		b"C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)O[C@]2([C@H]([C@@H]"
		b"([C@H](O2)CO)O)O)CO)O)O)O)O"
	),
	sha256="616d5d5bc1723b6ded4a8471dca9affbff55d2efed5b54b0c9d483497f340fd9",
)

_COORDINATES = (
	("glucose.c1", (-60.0, 0.0)), ("glucose.c2", (-30.0, 30.0)),
	("glucose.c3", (0.0, 30.0)), ("glucose.c4", (30.0, 0.0)),
	("glucose.c5", (15.0, -30.0)), ("glucose.o5", (-30.0, -30.0)),
	("glucose.c6", (-15.0, -60.0)), ("glucose.c2.oh", (-30.0, 60.0)),
	("glucose.c3.oh", (0.0, 0.0)), ("glucose.c4.oh", (30.0, 30.0)),
	("glucose.c6.oh", (-15.0, -90.0)), ("bridge.o", (-60.0, 35.0)),
	("fructose.c2", (-60.0, 70.0)), ("fructose.c3", (-100.0, 85.0)),
	("fructose.c4", (-135.0, 70.0)), ("fructose.c5", (-125.0, 35.0)),
	("fructose.o5", (-85.0, 25.0)), ("fructose.c1", (-60.0, 110.0)),
	("fructose.c6", (-130.0, 5.0)), ("fructose.c3.oh", (-100.0, 55.0)),
	("fructose.c4.oh", (-135.0, 100.0)), ("fructose.c1.oh", (-60.0, 140.0)),
	("fructose.c6.oh", (-130.0, -25.0)),
)

_STYLES = (
	("glucose.c1>glucose.c2", "w", "front"),
	("glucose.c2>glucose.c3", "q", "front"),
	("glucose.c4>glucose.c3", "w", "front"),
	("glucose.c4>glucose.c5", "n", "back"),
	("glucose.c5>glucose.o5", "n", "back"),
	("glucose.o5>glucose.c1", "n", "back"),
	("fructose.c2>fructose.c3", "w", "front"),
	("fructose.c3>fructose.c4", "q", "front"),
	("fructose.c5>fructose.c4", "w", "front"),
	("fructose.c5>fructose.o5", "n", "back"),
	("fructose.o5>fructose.c2", "n", "back"),
)

PLAN = VerifiedSucrosePlan(_COORDINATES, _STYLES)


#============================================
def validate_identity(
		source: bytes, provenance: str, digest: str,
		) -> None:
	"""Validate exact preset identity before decoding or parsing source bytes."""
	if source != IDENTITY.isomeric_smiles:
		raise ValueError("Verified sucrose source bytes do not match the preset")
	if provenance != IDENTITY.provenance:
		raise ValueError("Verified sucrose provenance does not match the preset")
	if digest != IDENTITY.sha256:
		raise ValueError("Verified sucrose digest does not match the preset")
	if hashlib.sha256(source).hexdigest() != digest:
		raise ValueError("Verified sucrose source digest verification failed")


#============================================
def prepare_verified_sucrose_haworth() -> object:
	"""Return one detached fixed sucrose graph ready for insertion placement.

	All topology, role, style, and geometry checks complete before this function
	changes the parsed detached graph.  A failure leaves that parsed candidate
	untouched and never reaches a frontend or document session.
	"""
	molecule = _parse_verified_source(
		IDENTITY.isomeric_smiles, IDENTITY.provenance, IDENTITY.sha256,
	)
	for atom in molecule.vertices:
		atom.x = 0.0
		atom.y = 0.0
	_apply_plan(molecule, PLAN)
	return molecule


#============================================
def _parse_verified_source(source: bytes, provenance: str, digest: str) -> object:
	"""Parse only the exact source accepted by the preset identity fence."""
	validate_identity(source, provenance, digest)
	source_text = source.decode("ascii")
	molecule = oasa.smiles_lib.text_to_mol(source_text, calc_coords=0)
	return molecule


#============================================
def role_by_atom(molecule: object) -> dict[object, str]:
	"""Resolve the fixed preset's named roles after its topology is validated."""
	candidates = _ring_candidates(molecule)
	pyranose = [ring for kind, ring in candidates if kind == "pyranose"]
	furanose = [ring for kind, ring in candidates if kind == "furanose"]
	if len(pyranose) != 1 or len(furanose) != 1:
		raise ValueError("Verified sucrose requires one six-member and one five-member C/O ring")
	glucose_ring = set(pyranose[0])
	fructose_ring = set(furanose[0])
	if glucose_ring & fructose_ring:
		raise ValueError("Verified sucrose rings must be vertex disjoint")
	bridge, glucose_c1, fructose_c2 = _direct_bridge(molecule, glucose_ring, fructose_ring)
	glucose_o5 = next(atom for atom in glucose_ring if atom.symbol == "O")
	glucose_c5 = next(atom for atom in glucose_o5.neighbors if atom is not glucose_c1)
	glucose_path = _carbon_path(glucose_c1, glucose_c5, 4)
	fructose_o5 = next(atom for atom in fructose_ring if atom.symbol == "O")
	fructose_c5 = next(atom for atom in fructose_o5.neighbors if atom is not fructose_c2)
	fructose_path = _carbon_path(fructose_c2, fructose_c5, 3)
	roles = {bridge: "bridge.o", glucose_o5: "glucose.o5", fructose_o5: "fructose.o5"}
	for number, atom in enumerate(glucose_path, 1):
		roles[atom] = "glucose.c%s" % number
	for number, atom in enumerate(fructose_path, 2):
		roles[atom] = "fructose.c%s" % number
	for key, anchor, ring in (
			("glucose.c6", glucose_path[-1], glucose_ring),
			("fructose.c1", fructose_c2, fructose_ring),
			("fructose.c6", fructose_path[-1], fructose_ring),
			):
		exterior = [
			atom for atom in anchor.neighbors
			if atom not in glucose_ring and atom not in fructose_ring
			and atom is not bridge and atom.symbol == "C"
		]
		if len(exterior) != 1:
			raise ValueError("Verified sucrose exterior carbon chain is missing or ambiguous")
		roles[exterior[0]] = key
	for atom in molecule.vertices:
		if atom in roles:
			continue
		if atom.symbol != "O" or atom.degree != 1 or atom.neighbors[0] not in roles:
			raise ValueError("Verified sucrose has unsupported topology")
		roles[atom] = roles[atom.neighbors[0]] + ".oh"
	if len(roles) != len(molecule.vertices) or len(set(roles.values())) != len(roles):
		raise ValueError("Verified sucrose role resolution must cover every atom once")
	return roles


#============================================
def _ring_candidates(molecule: object) -> list[tuple[str, tuple[object, ...]]]:
	"""Return uniquely identifiable C/O ring candidates from the fixed graph."""
	candidates = []
	for oxygen in molecule.vertices:
		if oxygen.symbol != "O" or oxygen.degree != 2:
			continue
		neighbors = [atom for atom in oxygen.neighbors if atom.symbol == "C"]
		if len(neighbors) != 2:
			continue
		for carbon_count, kind in ((5, "pyranose"), (4, "furanose")):
			paths = _carbon_paths(neighbors[0], neighbors[1], carbon_count - 1)
			if len(paths) == 1:
				candidates.append((kind, paths[0] + (oxygen,)))
	return candidates


#============================================
def _carbon_paths(start: object, end: object, length: int) -> list[tuple[object, ...]]:
	"""Return simple all-carbon paths with one exact edge count."""
	paths = []
	def walk(atom: object, path: tuple[object, ...]) -> None:
		if len(path) - 1 == length:
			if atom is end:
				paths.append(path)
			return
		for neighbor in atom.neighbors:
			if neighbor.symbol == "C" and neighbor not in path:
				walk(neighbor, path + (neighbor,))
	walk(start, (start,))
	return paths


#============================================
def _carbon_path(start: object, end: object, length: int) -> tuple[object, ...]:
	"""Return one unambiguous fixed-role carbon path."""
	paths = _carbon_paths(start, end, length)
	if len(paths) != 1:
		raise ValueError("Verified sucrose carbon path is ambiguous")
	return paths[0]


#============================================
def _direct_bridge(
		molecule: object, glucose_ring: set[object], fructose_ring: set[object],
		) -> tuple[object, object, object]:
	"""Return the only external degree-two oxygen joining the named rings."""
	bridges = []
	for atom in molecule.vertices:
		if atom.symbol != "O" or atom.degree != 2 or atom in glucose_ring or atom in fructose_ring:
			continue
		glucose_neighbors = [atom2 for atom2 in atom.neighbors if atom2 in glucose_ring and atom2.symbol == "C"]
		fructose_neighbors = [atom2 for atom2 in atom.neighbors if atom2 in fructose_ring and atom2.symbol == "C"]
		if len(glucose_neighbors) == 1 and len(fructose_neighbors) == 1:
			bridges.append((atom, glucose_neighbors[0], fructose_neighbors[0]))
	if len(bridges) != 1:
		raise ValueError("Verified sucrose requires one direct degree-two glycosidic oxygen bridge")
	return bridges[0]


#============================================
def _apply_plan(molecule: object, plan: VerifiedSucrosePlan) -> None:
	"""Validate one whole detached candidate and then apply it in one stage."""
	roles = role_by_atom(molecule)
	if plan != PLAN:
		raise ValueError("Verified sucrose accepts only its immutable fixed plan")
	coordinates = dict(plan.coordinates)
	if set(coordinates) != set(roles.values()):
		raise ValueError("Verified sucrose plan role coverage does not match topology")
	_validate_geometry(molecule, roles, coordinates)
	by_role = {role: atom for atom, role in roles.items()}
	updates = []
	for edge, style, position in plan.styles:
		first_role, second_role = edge.split(">", maxsplit=1)
		bond = molecule.get_edge_between(by_role[first_role], by_role[second_role])
		if bond is None:
			raise ValueError("Verified sucrose style edge is absent from the fixed topology")
		updates.append((bond, by_role[first_role], by_role[second_role], style, position))
	_validate_wedges(plan, roles)
	for atom, role in roles.items():
		atom.x, atom.y = coordinates[role]
	for bond, first, second, style, position in updates:
		bond.type = style
		bond.properties_["haworth_position"] = position
		if style == "w":
			bond.set_vertices((first, second))


#============================================
def _validate_wedges(plan: VerifiedSucrosePlan, roles: dict[object, str]) -> None:
	"""Check the q/w/n face convention before any graph mutation."""
	role_names = set(roles.values())
	for prefix in ("glucose", "fructose"):
		ring_styles = [entry for entry in plan.styles if entry[0].startswith(prefix + ".")]
		q_edges = [edge for edge, style, _position in ring_styles if style == "q"]
		w_edges = [edge for edge, style, _position in ring_styles if style == "w"]
		if len(q_edges) != 1 or len(w_edges) != 2:
			raise ValueError("Verified sucrose requires one q and two w edges per ring")
		q_roles = set(q_edges[0].split(">"))
		for edge in w_edges:
			first, second = edge.split(">", maxsplit=1)
			if first not in role_names or second not in q_roles:
				raise ValueError("Verified sucrose wedge wide endpoint is not on the q edge")


#============================================
def _validate_geometry(
		molecule: object, roles: dict[object, str], coordinates: dict[str, tuple[float, float]],
		) -> None:
	"""Validate finite fixed coordinates and the recorded clearance predicates."""
	for x, y in coordinates.values():
		_finite_coordinate(x)
		_finite_coordinate(y)
	min_atom = min(
		_distance(coordinates[roles[first]], coordinates[roles[second]])
		for index, first in enumerate(molecule.vertices)
		for second in molecule.vertices[index + 1:]
		if molecule.get_edge_between(first, second) is None
	)
	edges = list(molecule.edges)
	min_edge = min(
		_distance(coordinates[roles[first]], coordinates[roles[second]])
		for index, first_edge in enumerate(edges)
		for second_edge in edges[index + 1:]
		if not set(first_edge.vertices) & set(second_edge.vertices)
		for first in first_edge.vertices for second in second_edge.vertices
	)
	if min_atom < 9.0 or min_edge < 6.0:
		raise ValueError("Verified sucrose fixed geometry did not clear its layout gate")


#============================================
def _finite_coordinate(value: object) -> float:
	"""Return one finite built-in coordinate value."""
	if type(value) not in (int, float):
		raise ValueError("Verified sucrose coordinates must be finite builtin numbers")
	result = float(value)
	if not math.isfinite(result):
		raise ValueError("Verified sucrose coordinates must be finite builtin numbers")
	return result


#============================================
def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
	"""Return Euclidean distance between two fixed drawing points."""
	result = math.hypot(first[0] - second[0], first[1] - second[1])
	return result
