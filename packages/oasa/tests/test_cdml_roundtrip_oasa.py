"""OASA CDML round-trip metadata checks (Phase 3)."""

# Standard Library
import os

# Local repo modules
import conftest

# local repo modules
import oasa

# fixtures live in the repo-root tests/ directory
FIXTURES_DIR = conftest.repo_tests_path("fixtures", "cdml_roundtrip")


#============================================
def _load_fixture(name):
	path = os.path.join(FIXTURES_DIR, name)
	with open(path, "r", encoding="utf-8") as handle:
		text = handle.read()
	mol = oasa.cdml.text_to_mol(text)
	if mol is None:
		raise AssertionError("Failed to load CDML fixture: %s" % path)
	return mol


#============================================
def test_oasa_preserves_custom_attributes():
	mol = _load_fixture("custom_attr.cdml")
	assert mol.edges
	bond = next(iter(mol.edges))
	assert bond.properties_.get("custom") == "keep"
	present = bond.properties_.get("_cdml_present")
	assert present is not None
	assert "custom" in present


#============================================
def test_oasa_preserves_wavy_and_color():
	mol = _load_fixture("wavy_color.cdml")
	bond = next(iter(mol.edges))
	assert bond.type == "s"
	assert bond.wavy_style == "triangle"
	assert bond.line_color == "#239e2d"


#============================================
def test_oasa_canonicalizes_vertex_ordering():
	mol = _load_fixture("vertex_ordering.cdml")
	bonds = [bond for bond in mol.edges if bond.type in ("w", "h")]
	assert bonds
	for bond in bonds:
		v1, v2 = bond.vertices
		front = v1
		if v2.y > v1.y:
			front = v2
		elif v2.y == v1.y and v2.x > v1.x:
			front = v2
		assert v2 is front
