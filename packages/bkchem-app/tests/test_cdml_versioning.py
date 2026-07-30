"""Smoke test for CDML version transforms."""

# PIP3 modules
from defusedxml import minidom
from lxml import etree

# local repo modules
import oasa.atom_lib
import oasa.smiles_lib

from bkchem import CDML_versions
from bkchem import bkchem_config


#============================================
def build_cdml(version: object) -> object:
	doc = minidom.parseString(f'<cdml version="{version}"></cdml>')
	return doc.documentElement


#============================================
def _parse_cdml(text: str) -> etree._Element:
	"""Parse generated CDML without entities, DTDs, network access, or recovery."""
	parser = etree.XMLParser(
		resolve_entities=False,
		no_network=True,
		load_dtd=False,
		dtd_validation=False,
		recover=False,
		huge_tree=False,
	)
	return etree.fromstring(text.encode("utf-8"), parser=parser)


#============================================
def test_cdml_transform_legacy_to_current() -> None:
	dom = build_cdml("0.16")
	assert CDML_versions.transform_dom_to_version(dom, bkchem_config.current_CDML_version) == 1
	assert dom.getAttribute("version") == "26.07"


#============================================
def test_cdml_transform_old_to_current() -> None:
	dom = build_cdml("0.15")
	assert CDML_versions.transform_dom_to_version(dom, bkchem_config.current_CDML_version) == 1
	assert dom.getAttribute("version") == "26.07"


#============================================
def test_cdml_transform_current_compatibility_profile_to_authored_profile() -> None:
	"""The explicit no-op edge advertises the new authored CDML profile."""
	dom = build_cdml("26.02")
	assert CDML_versions.transform_dom_to_version(dom, "26.07") == 1
	assert dom.getAttribute("version") == "26.07"


#============================================
def test_template_cdml_separates_format_and_authoring_versions() -> None:
	"""Template output keeps the CDML profile separate from BKChem release metadata."""
	from bkchem.temp_manager import _build_cdml_string
	mol = oasa.smiles_lib.text_to_mol("CO", calc_coords=1)
	anchor = next(iter(mol.vertices))
	template_atom = oasa.atom_lib.Atom(symbol="C")
	template_atom.x = anchor.x + 1.0
	template_atom.y = anchor.y
	root = _parse_cdml(_build_cdml_string("Methanol", mol, anchor, None, template_atom))
	namespace = "{http://www.freesoftware.fsf.org/bkchem/cdml}"
	author = root.find(namespace + "info/" + namespace + "author_program")
	assert root.attrib["version"] == bkchem_config.current_CDML_version
	assert author.attrib["version"] == bkchem_config.current_BKChem_version
