"""Unit tests for shared fixed bond-length style policy."""

# Standard Library
import math

# Third Party
import pytest

# local repo modules
import oasa
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
from oasa import render_ops
from oasa.render_lib.bond_length_policy import bond_length_profile
from oasa.render_lib.bond_length_policy import resolve_bond_length
from oasa.render_lib.bond_ops import _apply_bond_length_policy
from oasa.render_lib.molecule_ops import molecule_to_ops


#============================================
class _EdgeMock:
	"""Minimal edge-like object for policy helper tests."""

	def __init__(self, order=1, edge_type='n', properties=None):
		self.order = order
		self.type = edge_type
		self.properties_ = properties or {}


#============================================
def _distance(p1, p2):
	return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


#============================================
def _build_two_atom_molecule(order=1, edge_type='n'):
	mol = oasa.molecule_lib.Molecule()
	a1 = oasa.atom_lib.Atom(symbol='C')
	a2 = oasa.atom_lib.Atom(symbol='C')
	a1.x = 0.0
	a1.y = 0.0
	a2.x = 10.0
	a2.y = 0.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	bond = oasa.bond_lib.Bond(order=order, type=edge_type)
	bond.vertices = (a1, a2)
	mol.add_edge(a1, a2, bond)
	return mol, bond


#============================================
def _longest_line_length(ops):
	lines = [op for op in ops if isinstance(op, render_ops.LineOp)]
	if not lines:
		raise AssertionError("Expected at least one LineOp in rendered output")
	return max(_distance(line.p1, line.p2) for line in lines)


#============================================
def test_bond_length_profile_table_keys():
	profile = bond_length_profile()
	assert set(profile) == {
		"single",
		"double",
		"triple",
		"dashed_hbond",
		"rounded_wedge",
		"hashed_wedge",
		"wavy",
	}


#============================================
@pytest.mark.parametrize(
	("style", "expected_ratio"),
	(
		("single", 1.00),
		("double", 0.98),
		("triple", 0.96),
		("dashed_hbond", 1.08),
		("rounded_wedge", 1.00),
		("hashed_wedge", 1.00),
		("wavy", 1.00),
	),
)
def test_resolve_bond_length_defaults(style, expected_ratio):
	resolved = resolve_bond_length(10.0, style)
	assert resolved == pytest.approx(10.0 * expected_ratio)


#============================================
def test_resolve_bond_length_rejects_non_default_override_without_tag():
	with pytest.raises(ValueError, match="Non-default bond length requires one exception tag"):
		resolve_bond_length(
			base_length=10.0,
			bond_style="single",
			requested_length=12.0,
		)


#============================================
def test_resolve_bond_length_enforces_exception_direction_rules():
	with pytest.raises(ValueError, match="may only lengthen"):
		resolve_bond_length(
			base_length=10.0,
			bond_style="single",
			requested_length=9.0,
			exception_tag="EXC_OXYGEN_AVOID_UP",
		)
	with pytest.raises(ValueError, match="may only shorten"):
		resolve_bond_length(
			base_length=10.0,
			bond_style="single",
			requested_length=11.0,
			exception_tag="EXC_RING_INTERIOR_CLEARANCE",
		)


#============================================
@pytest.mark.parametrize(
	("order", "edge_type", "expected_ratio"),
	(
		(1, "n", 1.00),
		(2, "n", 0.98),
		(3, "n", 0.96),
		(1, "d", 1.08),
		(1, "w", 1.00),
		(1, "h", 1.00),
		(1, "s", 1.00),
	),
)
def test_apply_bond_length_policy_uses_style_mapping(order, edge_type, expected_ratio):
	edge = _EdgeMock(order=order, edge_type=edge_type)
	start, end = _apply_bond_length_policy(edge, (0.0, 0.0), (10.0, 0.0))
	assert start == pytest.approx((0.0, 0.0))
	assert _distance(start, end) == pytest.approx(10.0 * expected_ratio)


#============================================
def test_molecule_to_ops_applies_default_double_and_triple_lengths():
	base_mol, _base_bond = _build_two_atom_molecule(order=1, edge_type='n')
	base_ops = molecule_to_ops(base_mol)
	base_length = _longest_line_length(base_ops)

	double_mol, _double_bond = _build_two_atom_molecule(order=2, edge_type='n')
	double_ops = molecule_to_ops(double_mol)
	double_length = _longest_line_length(double_ops)

	triple_mol, _triple_bond = _build_two_atom_molecule(order=3, edge_type='n')
	triple_ops = molecule_to_ops(triple_mol)
	triple_length = _longest_line_length(triple_ops)

	assert double_length == pytest.approx(base_length * 0.98)
	assert triple_length == pytest.approx(base_length * 0.96)


#============================================
def test_molecule_to_ops_rejects_untagged_non_default_override():
	mol, bond = _build_two_atom_molecule(order=1, edge_type='n')
	bond.properties_["bond_length_override"] = 12.0
	with pytest.raises(ValueError, match="Non-default bond length requires one exception tag"):
		molecule_to_ops(mol)


#============================================
def test_molecule_to_ops_accepts_tagged_override():
	mol, bond = _build_two_atom_molecule(order=1, edge_type='n')
	bond.properties_["bond_length_override"] = 12.0
	bond.properties_["bond_length_exception_tag"] = "EXC_OXYGEN_AVOID_UP"
	ops = molecule_to_ops(mol)
	assert _longest_line_length(ops) == pytest.approx(12.0)
