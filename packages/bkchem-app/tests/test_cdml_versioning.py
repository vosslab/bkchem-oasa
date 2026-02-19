"""Smoke test for CDML version transforms."""

from defusedxml import minidom

# local repo modules
from bkchem import CDML_versions
from bkchem import bkchem_config


#============================================
def build_cdml(version):
	doc = minidom.parseString(f'<cdml version="{version}"></cdml>')
	return doc.documentElement


#============================================
def test_cdml_transform_legacy_to_current():
	dom = build_cdml("0.16")
	assert CDML_versions.transform_dom_to_version(dom, bkchem_config.current_CDML_version) == 1


#============================================
def test_cdml_transform_old_to_current():
	dom = build_cdml("0.15")
	assert CDML_versions.transform_dom_to_version(dom, bkchem_config.current_CDML_version) == 1
