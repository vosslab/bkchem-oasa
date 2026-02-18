"""Unit checks for Phase 0 CDML fixtures."""

# Standard Library
import os

# Third Party
import defusedxml.ElementTree

# Local repo modules
import conftest


FIXTURES_DIR = conftest.repo_tests_path("fixtures", "bkchem_phase0")
FIXTURE_EXPECTATIONS = {
	"basic_types.cdml": {
		"types": {"n1", "b1", "d1", "o1", "a1"},
	},
	"stereo.cdml": {
		"types": {"w1", "h1", "n1"},
	},
	"aromatic.cdml": {
		"types": {"n1", "n2"},
	},
	"wavy_color.cdml": {
		"types": {"s1"},
		"wavy_style": {"triangle"},
	},
	"bkchem_widths.cdml": {
		"types": {"n2", "w1"},
		"attrs": {"auto_sign", "bond_width", "equithick"},
	},
}


#============================================
def _strip_namespace(tag):
	"""Return tag without namespace prefix."""
	if "}" in tag:
		return tag.split("}", 1)[1]
	return tag


#============================================
def _iter_bonds(root):
	"""Yield bond elements from a CDML document."""
	for element in root.iter():
		if _strip_namespace(element.tag) == "bond":
			yield element


#============================================
def _load_cdml(path):
	"""Load a CDML file into an ElementTree root."""
	tree = defusedxml.ElementTree.parse(path)
	return tree.getroot()


#============================================
def test_phase0_cdml_fixture_coverage():
	for filename, expectations in FIXTURE_EXPECTATIONS.items():
		path = os.path.join(FIXTURES_DIR, filename)
		assert os.path.isfile(path), "Missing CDML fixture: %s" % path
		root = _load_cdml(path)
		assert root.get("version") == "26.02"
		bond_types = set()
		wavy_styles = set()
		attrs_seen = set()
		for bond in _iter_bonds(root):
			bond_type = bond.get("type")
			if bond_type:
				bond_types.add(bond_type)
			wavy_style = bond.get("wavy_style")
			if wavy_style:
				wavy_styles.add(wavy_style)
			for attr in expectations.get("attrs", set()):
				if bond.get(attr):
					attrs_seen.add(attr)
		assert expectations["types"].issubset(bond_types)
		if "wavy_style" in expectations:
			assert expectations["wavy_style"].issubset(wavy_styles)
		if "attrs" in expectations:
			assert expectations["attrs"].issubset(attrs_seen)
