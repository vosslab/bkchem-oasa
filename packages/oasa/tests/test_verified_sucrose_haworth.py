"""Focused durable behavior for the one identity-bound sucrose preset."""

# Standard Library
import dataclasses
import math

# PIP3 modules
import pytest

# Local modules
import oasa.cdml
import oasa.cdml_document
import oasa.cdml_writer
import oasa.haworth.verified_sucrose
import oasa.smiles_lib


#============================================
def _snapshot(molecule: object) -> tuple:
	"""Return detached mutable state used to prove rejected candidates are inert."""
	indexes = {atom: index for index, atom in enumerate(molecule.vertices)}
	bonds = tuple(sorted(
		(
			tuple(indexes[atom] for atom in bond.vertices),
			bond.type,
			tuple(sorted(bond.properties_.items())),
		)
		for bond in molecule.edges
	))
	result = (
		tuple((atom.x, atom.y) for atom in molecule.vertices),
		bonds,
	)
	return result


#============================================
def _role_geometry(molecule: object) -> dict[str, tuple[float, float]]:
	"""Return coordinates keyed by the production topology resolver."""
	roles = oasa.haworth.verified_sucrose.role_by_atom(molecule)
	result = {role: (atom.x, atom.y) for atom, role in roles.items()}
	return result


#============================================
def _role_directed_styles(molecule: object) -> tuple[tuple[str, str, str, str], ...]:
	"""Return every persistent Haworth style keyed by role-directed endpoints."""
	roles = oasa.haworth.verified_sucrose.role_by_atom(molecule)
	result = tuple(sorted(
		(roles[bond.vertices[0]], roles[bond.vertices[1]], bond.type,
		 bond.properties_["haworth_position"])
		for bond in molecule.edges
		if bond.type in ("q", "w", "n") and "haworth_position" in bond.properties_
	))
	return result


#============================================
def _fixed_shape(molecule: object) -> tuple:
	"""Return the named preset's durable chemistry and directed-style facts."""
	roles = oasa.haworth.verified_sucrose.role_by_atom(molecule)
	role_by_name = {role: atom for atom, role in roles.items()}
	rings = molecule.get_smallest_independent_cycles()
	ring_signature = tuple(sorted(
		tuple(sorted(atom.symbol for atom in ring))
		for ring in rings
	))
	bridge = role_by_name["bridge.o"]
	bridge_roles = tuple(sorted(roles[atom] for atom in bridge.neighbors))
	directed_wedges = tuple(sorted(
		("%s>%s" % (roles[bond.vertices[0]], roles[bond.vertices[1]]),
		 bond.properties_["haworth_position"])
		for bond in molecule.edges if bond.type == "w"
	))
	q_roles = {}
	for prefix in ("glucose", "fructose"):
		q_edges = [
			edge for edge, style, _position in oasa.haworth.verified_sucrose.PLAN.styles
			if edge.startswith(prefix + ".") and style == "q"
		]
		q_roles[prefix] = frozenset(q_edges[0].split(">"))
	wide_ends_on_q = all(
		second in q_roles[first.split(".")[0]]
		for edge, _position in directed_wedges
		for first, second in (edge.split(">", maxsplit=1),)
	)
	result = (
		tuple(sorted(atom.symbol for atom in molecule.vertices)),
		len(set(roles.values())),
		ring_signature,
		bridge.degree,
		bridge_roles,
		directed_wedges,
		wide_ends_on_q,
	)
	return result


#============================================
def _face_map(molecule: object) -> tuple[tuple[str, str], ...]:
	"""Return the fixed +Y-down substituent directions by named role."""
	coordinates = _role_geometry(molecule)
	pairs = (
		("glucose.c1", "bridge.o"), ("glucose.c2", "glucose.c2.oh"),
		("glucose.c3", "glucose.c3.oh"), ("glucose.c4", "glucose.c4.oh"),
		("glucose.c5", "glucose.c6"), ("fructose.c2", "bridge.o"),
		("fructose.c2", "fructose.c1"), ("fructose.c3", "fructose.c3.oh"),
		("fructose.c4", "fructose.c4.oh"), ("fructose.c5", "fructose.c6"),
	)
	result = tuple(
		(role, "down" if coordinates[substituent][1] > coordinates[role][1] else "up")
		for role, substituent in pairs
	)
	return result


#============================================
def _clearances(molecule: object) -> tuple[float, float]:
	"""Measure the two independent fixed-layout clearance predicates."""
	coordinates = _role_geometry(molecule)
	roles = oasa.haworth.verified_sucrose.role_by_atom(molecule)
	min_atom = min(
		math.dist(coordinates[roles[first]], coordinates[roles[second]])
		for index, first in enumerate(molecule.vertices)
		for second in molecule.vertices[index + 1:]
		if molecule.get_edge_between(first, second) is None
	)
	edges = list(molecule.edges)
	min_edge = min(
		math.dist(coordinates[roles[first]], coordinates[roles[second]])
		for index, first_edge in enumerate(edges)
		for second_edge in edges[index + 1:]
		if not set(first_edge.vertices) & set(second_edge.vertices)
		for first in first_edge.vertices for second in second_edge.vertices
	)
	result = min_atom, min_edge
	return result


#============================================
def _assert_identity_rejected_before_parse(
		monkeypatch: pytest.MonkeyPatch, source: bytes, provenance: str, digest: str,
		) -> None:
	"""Prove each identity-fence failure occurs before OASA's parser boundary."""
	called = []
	def parser_must_not_run(text: str, calc_coords: int) -> object:
		called.append((text, calc_coords))
		raise AssertionError("identity rejection reached the molecule parser")
	monkeypatch.setattr(oasa.smiles_lib, "text_to_mol", parser_must_not_run)
	with pytest.raises(ValueError):
		oasa.haworth.verified_sucrose._parse_verified_source(source, provenance, digest)
	assert not called


#============================================
class _WrongHash:
	"""Deterministic hash result used to reach the recomputed-digest gate."""

	def hexdigest(self) -> str:
		"""Return a digest that disagrees with the immutable identity record."""
		result = "0" * 64
		return result


#============================================
def _wrong_sha256(source: bytes) -> _WrongHash:
	"""Return a deterministic nonmatching hash object for the final fence gate."""
	return _WrongHash()


#============================================
def _unplanned_sucrose() -> object:
	"""Return the preset source graph before fixed-plan mutation."""
	molecule = oasa.smiles_lib.text_to_mol(
		oasa.haworth.verified_sucrose.IDENTITY.isomeric_smiles.decode("ascii"), calc_coords=0,
	)
	for atom in molecule.vertices:
		atom.x = 0.0
		atom.y = 0.0
	return molecule


#============================================
def _ordered_variant(reverse_vertices: bool, reverse_neighbors: bool) -> object:
	"""Return one fresh source graph with harmless storage-order variation."""
	molecule = _unplanned_sucrose()
	if reverse_vertices:
		molecule.vertices.reverse()
	if reverse_neighbors:
		for atom in molecule.vertices:
			atom.neighbors.reverse()
	return molecule


#============================================
def test_verified_sucrose_rejects_altered_source_before_parse(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Changed bytes are rejected before the fixed source reaches the parser."""
	identity = oasa.haworth.verified_sucrose.IDENTITY
	_assert_identity_rejected_before_parse(
		monkeypatch, identity.isomeric_smiles + b" ", identity.provenance, identity.sha256,
	)


#============================================
def test_verified_sucrose_rejects_wrong_provenance_before_parse(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Changed provenance is rejected before the fixed source reaches the parser."""
	identity = oasa.haworth.verified_sucrose.IDENTITY
	_assert_identity_rejected_before_parse(
		monkeypatch, identity.isomeric_smiles, identity.provenance + " changed", identity.sha256,
	)


#============================================
def test_verified_sucrose_rejects_declared_digest_before_parse(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A declared digest different from the preset record is rejected before parse."""
	identity = oasa.haworth.verified_sucrose.IDENTITY
	_assert_identity_rejected_before_parse(
		monkeypatch, identity.isomeric_smiles, identity.provenance, "0" * 64,
	)


#============================================
def test_verified_sucrose_rejects_recomputed_digest_before_parse(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A recomputed digest mismatch is rejected before parser invocation."""
	identity = oasa.haworth.verified_sucrose.IDENTITY
	monkeypatch.setattr(oasa.haworth.verified_sucrose.hashlib, "sha256", _wrong_sha256)
	_assert_identity_rejected_before_parse(
		monkeypatch, identity.isomeric_smiles, identity.provenance, identity.sha256,
	)


#============================================
def test_verified_sucrose_has_fixed_scientific_shape_and_directed_wedges() -> None:
	"""Preparation creates the declared 6+5 bridge and directed-face representation."""
	molecule = oasa.haworth.verified_sucrose.prepare_verified_sucrose_haworth()
	shape = _fixed_shape(molecule)

	assert shape[:5] == (
		tuple("C" for _index in range(12)) + tuple("O" for _index in range(11)),
		23, (tuple("C" for _index in range(5)) + ("O",),
		     tuple("C" for _index in range(4)) + ("O",)),
		2, ("fructose.c2", "glucose.c1"),
	)
	assert shape[5:] == (
		(("fructose.c2>fructose.c3", "front"), ("fructose.c5>fructose.c4", "front"),
		 ("glucose.c1>glucose.c2", "front"), ("glucose.c4>glucose.c3", "front")), True,
	)


#============================================
def test_verified_sucrose_has_selected_alpha_beta_face_map() -> None:
	"""The named preset keeps the selected alpha-glucose and beta-fructose faces."""
	molecule = oasa.haworth.verified_sucrose.prepare_verified_sucrose_haworth()

	assert _face_map(molecule) == (
		("glucose.c1", "down"), ("glucose.c2", "down"), ("glucose.c3", "up"),
		("glucose.c4", "down"), ("glucose.c5", "up"), ("fructose.c2", "up"),
		("fructose.c2", "down"), ("fructose.c3", "up"), ("fructose.c4", "down"),
		("fructose.c5", "up"),
	)


#============================================
def test_verified_sucrose_fixed_geometry_clears_recorded_layout_gates() -> None:
	"""The fixed drawing retains meaningful atom and nonincident-edge clearance."""
	molecule = oasa.haworth.verified_sucrose.prepare_verified_sucrose_haworth()
	min_atom, min_edge = _clearances(molecule)

	assert min_atom >= 9.0
	assert min_edge >= 6.0


#============================================
def test_verified_sucrose_role_resolution_is_order_independent() -> None:
	"""Source storage order cannot change the prepared fixed depiction."""
	representations = []
	for reverse_vertices, reverse_neighbors in ((False, False), (True, False), (False, True), (True, True)):
		molecule = _ordered_variant(reverse_vertices, reverse_neighbors)
		oasa.haworth.verified_sucrose._apply_plan(molecule, oasa.haworth.verified_sucrose.PLAN)
		representations.append((_fixed_shape(molecule), _role_geometry(molecule)))

	assert all(representation == representations[0] for representation in representations[1:])


#============================================
def test_verified_sucrose_rejects_invalid_topology_without_mutation() -> None:
	"""Topology validation rejects a detached damaged graph without further mutation."""
	molecule = _unplanned_sucrose()
	roles = {
		role: atom for atom, role in oasa.haworth.verified_sucrose.role_by_atom(molecule).items()
	}
	molecule.disconnect(roles["glucose.c2"], roles["glucose.c3"])
	before = _snapshot(molecule)
	with pytest.raises(ValueError, match="ring"):
		oasa.haworth.verified_sucrose._apply_plan(molecule, oasa.haworth.verified_sucrose.PLAN)

	assert _snapshot(molecule) == before


#============================================
def test_verified_sucrose_rejects_invalid_fixed_plan_without_mutation() -> None:
	"""An alternate fixed-plan record is inert even when its source graph is valid."""
	molecule = oasa.haworth.verified_sucrose.prepare_verified_sucrose_haworth()
	before = _snapshot(molecule)
	tampered = dataclasses.replace(
		oasa.haworth.verified_sucrose.PLAN,
		styles=tuple(reversed(oasa.haworth.verified_sucrose.PLAN.styles)),
	)
	with pytest.raises(ValueError, match="immutable fixed plan"):
		oasa.haworth.verified_sucrose._apply_plan(molecule, tampered)

	assert _snapshot(molecule) == before


#============================================
def test_verified_sucrose_rejects_nonfinite_coordinate_without_mutation() -> None:
	"""Numeric validation rejects a detached coordinate candidate before graph mutation."""
	molecule = _unplanned_sucrose()
	roles = oasa.haworth.verified_sucrose.role_by_atom(molecule)
	coordinates = dict(oasa.haworth.verified_sucrose.PLAN.coordinates)
	coordinates["glucose.c1"] = (math.nan, 0.0)
	before = _snapshot(molecule)
	with pytest.raises(ValueError, match="finite builtin"):
		oasa.haworth.verified_sucrose._validate_geometry(molecule, roles, coordinates)

	assert _snapshot(molecule) == before


#============================================
def test_verified_sucrose_authoritative_round_trip_preserves_fixed_depiction() -> None:
	"""Backend commit and reload preserve the preset's persistent scientific data."""
	molecule = oasa.haworth.verified_sucrose.prepare_verified_sucrose_haworth()
	before_shape = _fixed_shape(molecule)
	before_faces = _face_map(molecule)
	before_geometry = _role_geometry(molecule)
	before_styles = _role_directed_styles(molecule)
	proposal = oasa.cdml_writer.molecules_to_insertion_proposal(
		[molecule], token_stem="verified-sucrose",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load("<cdml />")
	accepted = session.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=0, proposal_cdml=proposal,
	))
	oasa.cdml_document.CDMLDocument.parse(accepted.cdml, validation="strict")
	reloaded = next(oasa.cdml.read_cdml(accepted.cdml))
	after_geometry = _role_geometry(reloaded)
	after_styles = _role_directed_styles(reloaded)
	drift = max(math.dist(before_geometry[role], after_geometry[role]) for role in before_geometry)
	expected_styles = (
		("fructose.c2", "fructose.c3", "w", "front"),
		("fructose.c3", "fructose.c4", "q", "front"),
		("fructose.c5", "fructose.c4", "w", "front"),
		("fructose.c5", "fructose.o5", "n", "back"),
		("fructose.o5", "fructose.c2", "n", "back"),
		("glucose.c1", "glucose.c2", "w", "front"),
		("glucose.c1", "glucose.o5", "n", "back"),
		("glucose.c3", "glucose.c2", "q", "front"),
		("glucose.c4", "glucose.c3", "w", "front"),
		("glucose.c5", "glucose.c4", "n", "back"),
		("glucose.o5", "glucose.c5", "n", "back"),
	)

	assert (
		(_fixed_shape(reloaded), _face_map(reloaded)), (before_styles, after_styles)
		) == ((before_shape, before_faces), (expected_styles, expected_styles))
	assert drift <= 0.021
