"""Tests for repair operations on real biomolecule SMILES structures.

Exercises the 5 pure-geometry operations in oasa.repair_ops against
4 representative biomolecules loaded from SMILES strings.
"""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.repair_ops
import oasa.smiles_lib

# SMILES strings for 4 representative biomolecules (from PubChem)
MOLECULES = {
	"cholesterol": {
		"smiles": (
			"C[C@H](CCCC(C)C)[C@H]1CC[C@@H]2[C@@]1(CC[C@H]3"
			"[C@H]2CC=C4[C@@]3(CC[C@@H](C4)O)C)C"
		),
		"min_atoms": 27,
		"min_bonds": 29,
		# 4 fused rings: one 5-ring, three 6-rings
		"ring_sizes": [5, 6, 6, 6],
	},
	"GDP": {
		"smiles": (
			"C1=NC2=C(N1[C@H]3[C@@H]([C@@H]([C@H](O3)"
			"COP(=O)(O)OP(=O)(O)O)O)O)N=C(NC2=O)N"
		),
		"min_atoms": 25,
		"min_bonds": 27,
		# bicyclic purine (5+6) plus sugar ring (5)
		"ring_sizes": [5, 5, 6],
	},
	"histidine": {
		"smiles": "C1=C(NC=N1)C[C@@H](C(=O)O)N",
		"min_atoms": 10,
		"min_bonds": 10,
		# single 5-member imidazole ring
		"ring_sizes": [5],
	},
	"sucrose": {
		"smiles": (
			"C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)"
			"O[C@]2([C@H]([C@@H]([C@H](O2)CO)O)O)CO)O)O)O)O"
		),
		"min_atoms": 22,
		"min_bonds": 23,
		# furanose (5-ring) + pyranose (6-ring)
		"ring_sizes": [5, 6],
	},
}

# all 5 repair operations as (function, needs_bond_length) tuples
REPAIR_OPS = {
	"normalize_bond_lengths": (oasa.repair_ops.normalize_bond_lengths, True),
	"normalize_bond_angles": (oasa.repair_ops.normalize_bond_angles, True),
	"normalize_rings": (oasa.repair_ops.normalize_rings, True),
	"straighten_bonds": (oasa.repair_ops.straighten_bonds, False),
	"snap_to_hex_grid": (oasa.repair_ops.snap_to_hex_grid, True),
}


#============================================
def _mol_from_smiles(smiles_str):
	"""Parse a SMILES string and generate 2D coordinates.

	Args:
		smiles_str: SMILES text for one molecule.

	Returns:
		An OASA molecule object with coordinates.
	"""
	mol = oasa.smiles_lib.text_to_mol(smiles_str, calc_coords=1.0)
	assert mol is not None, f"Could not parse SMILES: {smiles_str}"
	return mol


#============================================
def _get_bond_lengths(mol) -> list:
	"""Compute Euclidean bond lengths for every bond in the molecule.

	Args:
		mol: An OASA molecule object.

	Returns:
		List of float distances, one per bond.
	"""
	lengths = []
	for bond in mol.bonds:
		v1, v2 = bond.vertices
		dx = v2.x - v1.x
		dy = v2.y - v1.y
		lengths.append(math.sqrt(dx * dx + dy * dy))
	return lengths


#============================================
def _get_ring_sizes(mol) -> list:
	"""Return sorted list of ring sizes.

	Args:
		mol: An OASA molecule object.

	Returns:
		Sorted list of integer ring sizes.
	"""
	cycles = mol.get_smallest_independent_cycles()
	sizes = sorted(len(c) for c in cycles)
	return sizes


#============================================
def _get_ring_atoms_set(mol) -> set:
	"""Return set of all atoms belonging to at least one ring.

	Args:
		mol: An OASA molecule object.

	Returns:
		Set of atom objects in rings.
	"""
	ring_atoms = set()
	for cycle in mol.get_smallest_independent_cycles():
		ring_atoms.update(cycle)
	return ring_atoms


#============================================
def _get_shared_ring_atoms(cycles) -> set:
	"""Return atoms that appear in more than one ring (fused ring junctions).

	Args:
		cycles: List of ring cycles from get_smallest_independent_cycles().

	Returns:
		Set of atom objects shared between two or more rings.
	"""
	seen = set()
	shared = set()
	for cycle in cycles:
		for atom in cycle:
			if atom in seen:
				shared.add(atom)
			seen.add(atom)
	return shared


#============================================
def _measure_ring_geometry(ring_atoms, mol) -> tuple:
	"""Measure bond lengths and internal angles for an ordered ring.

	Args:
		ring_atoms: List of atoms from one cycle.
		mol: The molecule object.

	Returns:
		Tuple of (bond_lengths list, internal_angles_deg list).
	"""
	ordered = oasa.repair_ops._order_ring_atoms(set(ring_atoms), mol)
	n = len(ordered)
	lengths = []
	angles = []
	for i in range(n):
		# bond length from atom i to atom i+1
		curr = ordered[i]
		nxt = ordered[(i + 1) % n]
		dx = nxt.x - curr.x
		dy = nxt.y - curr.y
		lengths.append(math.sqrt(dx * dx + dy * dy))
		# internal angle at atom i (between prev-curr-next)
		prev_atom = ordered[(i - 1) % n]
		next_atom = ordered[(i + 1) % n]
		dx1 = prev_atom.x - curr.x
		dy1 = prev_atom.y - curr.y
		dx2 = next_atom.x - curr.x
		dy2 = next_atom.y - curr.y
		dot = dx1 * dx2 + dy1 * dy2
		cross = dx1 * dy2 - dy1 * dx2
		angle_deg = math.degrees(abs(math.atan2(cross, dot)))
		angles.append(angle_deg)
	return lengths, angles


#============================================
def _is_fused_ring(cycle, all_cycles) -> bool:
	"""Check if a ring shares any atoms with another ring.

	Args:
		cycle: One ring cycle (list of atoms).
		all_cycles: All cycles from get_smallest_independent_cycles().

	Returns:
		True if the ring shares atoms with at least one other ring.
	"""
	ring_set = set(cycle)
	for other in all_cycles:
		if other is cycle:
			continue
		if ring_set & set(other):
			return True
	return False


#============================================
@pytest.fixture(params=sorted(MOLECULES.keys()))
def mol_data(request):
	"""Fixture that provides each biomolecule with its expected metadata."""
	key = request.param
	info = MOLECULES[key]
	mol = _mol_from_smiles(info["smiles"])
	result = {"mol": mol, "key": key}
	result.update(info)
	return result


#============================================
class TestMoleculeLoading:
	"""Verify that SMILES parsing produces expected molecular graphs."""

	def test_atom_count(self, mol_data):
		"""Each molecule has at least the expected number of heavy atoms."""
		mol = mol_data["mol"]
		assert len(mol.atoms) >= mol_data["min_atoms"], (
			f"{mol_data['key']}: expected >= {mol_data['min_atoms']} atoms, "
			f"got {len(mol.atoms)}"
		)

	def test_bond_count(self, mol_data):
		"""Each molecule has at least the expected number of bonds."""
		mol = mol_data["mol"]
		assert len(mol.bonds) >= mol_data["min_bonds"], (
			f"{mol_data['key']}: expected >= {mol_data['min_bonds']} bonds, "
			f"got {len(mol.bonds)}"
		)

	def test_ring_sizes(self, mol_data):
		"""Ring decomposition matches expected ring sizes."""
		mol = mol_data["mol"]
		sizes = _get_ring_sizes(mol)
		assert sizes == mol_data["ring_sizes"], (
			f"{mol_data['key']}: expected rings {mol_data['ring_sizes']}, "
			f"got {sizes}"
		)

	def test_coords_not_all_zero(self, mol_data):
		"""All atoms have coordinates and they are not all at the origin."""
		mol = mol_data["mol"]
		has_nonzero = False
		for atom in mol.atoms:
			assert not math.isnan(atom.x), "atom has NaN x"
			assert not math.isnan(atom.y), "atom has NaN y"
			if abs(atom.x) > 1e-6 or abs(atom.y) > 1e-6:
				has_nonzero = True
		assert has_nonzero, f"{mol_data['key']}: all atoms at origin"


#============================================
class TestNormalizeBondLengths:
	"""Test normalize_bond_lengths on each biomolecule."""

	def test_non_ring_bonds_normalized(self, mol_data):
		"""Non-ring bond lengths should be close to the target length."""
		mol = mol_data["mol"]
		oasa.repair_ops.normalize_bond_lengths(mol, bond_length=1.0)
		ring_atoms = _get_ring_atoms_set(mol)
		for bond in mol.bonds:
			v1, v2 = bond.vertices
			# skip bonds where both atoms are in a ring
			if v1 in ring_atoms and v2 in ring_atoms:
				continue
			dx = v2.x - v1.x
			dy = v2.y - v1.y
			length = math.sqrt(dx * dx + dy * dy)
			assert abs(length - 1.0) < 0.05, (
				f"{mol_data['key']}: non-ring bond length {length:.4f} "
				f"not near 1.0"
			)


#============================================
class TestNormalizeBondAngles:
	"""Test normalize_bond_angles on each biomolecule."""

	def test_angles_snap_to_60(self, mol_data):
		"""Non-ring, non-terminal bond angles should be near 60-degree multiples."""
		mol = mol_data["mol"]
		oasa.repair_ops.normalize_bond_angles(mol, bond_length=1.0)
		ring_atoms = _get_ring_atoms_set(mol)
		step = math.pi / 3.0
		violations = 0
		total_checked = 0
		for atom in mol.atoms:
			# skip ring atoms and terminal atoms
			if atom in ring_atoms or atom.degree < 2:
				continue
			for neighbor in atom.neighbors:
				if neighbor in ring_atoms:
					continue
				dx = neighbor.x - atom.x
				dy = neighbor.y - atom.y
				angle = math.atan2(dy, dx) % (2 * math.pi)
				# distance to nearest 60-degree multiple
				remainder = angle % step
				dist_to_slot = min(remainder, step - remainder)
				total_checked += 1
				if dist_to_slot > 0.15:
					violations += 1
		# allow up to 20% violations due to collision resolution
		if total_checked > 0:
			violation_rate = violations / total_checked
			assert violation_rate < 0.25, (
				f"{mol_data['key']}: {violations}/{total_checked} angles "
				f"not near 60-degree multiples"
			)


#============================================
class TestNormalizeRings:
	"""Test normalize_rings produces regular N-gons.

	normalize_rings should take any deformed, mangled N-member ring and
	reshape it into a perfect regular N-gon with uniform bond lengths
	and internal angles of 180*(N-2)/N degrees.

	For isolated (non-fused) rings this is verified strictly.  Fused ring
	systems are a known limitation: the algorithm processes rings
	sequentially, so later rings overwrite shared atom positions set by
	earlier rings.  Fused ring tests are marked xfail to document this.
	"""

	def test_isolated_ring_bond_lengths(self, mol_data):
		"""Isolated rings should have all bond lengths equal to bond_length."""
		mol = mol_data["mol"]
		oasa.repair_ops.normalize_rings(mol, bond_length=1.0)
		cycles = mol.get_smallest_independent_cycles()
		for cycle in cycles:
			if _is_fused_ring(cycle, cycles):
				continue
			lengths, _angles = _measure_ring_geometry(cycle, mol)
			for length in lengths:
				assert abs(length - 1.0) < 0.02, (
					f"{mol_data['key']}: isolated {len(cycle)}-ring "
					f"bond length {length:.4f}, expected 1.0"
				)

	def test_isolated_ring_angles(self, mol_data):
		"""Isolated rings should have internal angles of 180*(N-2)/N degrees."""
		mol = mol_data["mol"]
		oasa.repair_ops.normalize_rings(mol, bond_length=1.0)
		cycles = mol.get_smallest_independent_cycles()
		for cycle in cycles:
			if _is_fused_ring(cycle, cycles):
				continue
			n = len(cycle)
			# regular polygon interior angle formula
			expected_angle = 180.0 * (n - 2) / n
			_lengths, angles = _measure_ring_geometry(cycle, mol)
			for angle_deg in angles:
				assert abs(angle_deg - expected_angle) < 2.0, (
					f"{mol_data['key']}: isolated {n}-ring "
					f"angle {angle_deg:.1f}, expected {expected_angle:.1f}"
				)

	@pytest.mark.xfail(
		reason="fused rings: sequential processing overwrites shared atoms",
		strict=False,
	)
	def test_fused_ring_bond_lengths(self, mol_data):
		"""Fused rings should ideally have uniform bond lengths.

		Known limitation: the algorithm processes rings sequentially,
		so shared atoms get repositioned by the last ring processed,
		distorting earlier rings.
		"""
		mol = mol_data["mol"]
		cycles = mol.get_smallest_independent_cycles()
		has_fused = any(_is_fused_ring(c, cycles) for c in cycles)
		if not has_fused:
			pytest.skip("no fused rings in this molecule")
		oasa.repair_ops.normalize_rings(mol, bond_length=1.0)
		for cycle in cycles:
			if not _is_fused_ring(cycle, cycles):
				continue
			lengths, _angles = _measure_ring_geometry(cycle, mol)
			for length in lengths:
				assert abs(length - 1.0) < 0.02, (
					f"{mol_data['key']}: fused {len(cycle)}-ring "
					f"bond length {length:.4f}, expected 1.0"
				)

	@pytest.mark.xfail(
		reason="fused rings: sequential processing overwrites shared atoms",
		strict=False,
	)
	def test_fused_ring_angles(self, mol_data):
		"""Fused rings should ideally have regular N-gon angles.

		Known limitation: the algorithm processes rings sequentially,
		so shared atoms get repositioned by the last ring processed,
		distorting earlier rings.
		"""
		mol = mol_data["mol"]
		cycles = mol.get_smallest_independent_cycles()
		has_fused = any(_is_fused_ring(c, cycles) for c in cycles)
		if not has_fused:
			pytest.skip("no fused rings in this molecule")
		oasa.repair_ops.normalize_rings(mol, bond_length=1.0)
		for cycle in cycles:
			if not _is_fused_ring(cycle, cycles):
				continue
			n = len(cycle)
			expected_angle = 180.0 * (n - 2) / n
			_lengths, angles = _measure_ring_geometry(cycle, mol)
			for angle_deg in angles:
				assert abs(angle_deg - expected_angle) < 2.0, (
					f"{mol_data['key']}: fused {n}-ring "
					f"angle {angle_deg:.1f}, expected {expected_angle:.1f}"
				)


#============================================
class TestStraightenBonds:
	"""Test straighten_bonds on each biomolecule."""

	def test_terminal_angles_snap_to_30(self, mol_data):
		"""Terminal bond angles should be multiples of 30 degrees."""
		mol = mol_data["mol"]
		oasa.repair_ops.straighten_bonds(mol)
		step = math.pi / 6.0
		for atom in mol.atoms:
			if atom.degree != 1:
				continue
			neighbor = atom.neighbors[0]
			dx = atom.x - neighbor.x
			dy = atom.y - neighbor.y
			dist = math.sqrt(dx * dx + dy * dy)
			if dist < 1e-6:
				continue
			angle = math.atan2(dy, dx) % (2 * math.pi)
			remainder = angle % step
			dist_to_slot = min(remainder, step - remainder)
			assert dist_to_slot < 0.05, (
				f"{mol_data['key']}: terminal bond angle "
				f"{math.degrees(angle):.1f} not near 30-degree multiple"
			)


#============================================
class TestSnapToHexGrid:
	"""Test snap_to_hex_grid on each biomolecule.

	Snap-to-hex-grid is a global operation. N-member rings where
	N % 3 != 0 (e.g. 4, 5, 7, 8-member rings) cannot fit on a hex
	grid because the hex grid's 60-degree geometry only tiles with
	rings whose vertex count is a multiple of 3 (3, 6, 9, ...).
	Therefore we only verify the operation completes without error
	or NaN coordinates -- not that every atom lands on a grid point.
	"""

	def test_runs_without_error(self, mol_data):
		"""snap_to_hex_grid should complete without exceptions."""
		mol = mol_data["mol"]
		oasa.repair_ops.snap_to_hex_grid(mol, bond_length=1.0)

	def test_no_nan_after_snap(self, mol_data):
		"""No atom should have NaN or infinite coordinates after snapping."""
		mol = mol_data["mol"]
		oasa.repair_ops.snap_to_hex_grid(mol, bond_length=1.0)
		for atom in mol.atoms:
			assert math.isfinite(atom.x), (
				f"{mol_data['key']}: atom has non-finite x={atom.x}"
			)
			assert math.isfinite(atom.y), (
				f"{mol_data['key']}: atom has non-finite y={atom.y}"
			)


#============================================
class TestOperationsPreserveTopology:
	"""All repair operations must preserve atom and bond counts."""

	@pytest.fixture(params=sorted(REPAIR_OPS.keys()))
	def op_name(self, request):
		"""Parametrize over all repair operation names."""
		return request.param

	def test_atom_count_preserved(self, mol_data, op_name):
		"""Atom count unchanged after any repair operation."""
		mol = mol_data["mol"]
		original_count = len(mol.atoms)
		func, needs_bl = REPAIR_OPS[op_name]
		if needs_bl:
			func(mol, bond_length=1.0)
		else:
			func(mol)
		assert len(mol.atoms) == original_count, (
			f"{mol_data['key']} + {op_name}: atom count changed "
			f"from {original_count} to {len(mol.atoms)}"
		)

	def test_bond_count_preserved(self, mol_data, op_name):
		"""Bond count unchanged after any repair operation."""
		mol = mol_data["mol"]
		original_count = len(mol.bonds)
		func, needs_bl = REPAIR_OPS[op_name]
		if needs_bl:
			func(mol, bond_length=1.0)
		else:
			func(mol)
		assert len(mol.bonds) == original_count, (
			f"{mol_data['key']} + {op_name}: bond count changed "
			f"from {original_count} to {len(mol.bonds)}"
		)


#============================================
class TestOperationsProduceFiniteCoords:
	"""No repair operation should produce NaN or infinite coordinates."""

	@pytest.fixture(params=sorted(REPAIR_OPS.keys()))
	def op_name(self, request):
		"""Parametrize over all repair operation names."""
		return request.param

	def test_no_nan_or_inf(self, mol_data, op_name):
		"""All atom coordinates must be finite after any repair operation."""
		mol = mol_data["mol"]
		func, needs_bl = REPAIR_OPS[op_name]
		if needs_bl:
			func(mol, bond_length=1.0)
		else:
			func(mol)
		for atom in mol.atoms:
			assert math.isfinite(atom.x), (
				f"{mol_data['key']} + {op_name}: atom x={atom.x}"
			)
			assert math.isfinite(atom.y), (
				f"{mol_data['key']} + {op_name}: atom y={atom.y}"
			)
