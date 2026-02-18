# SPDX-License-Identifier: LGPL-3.0-or-later

"""Load the CDML fixture corpus in OASA."""

# Standard Library
import os

# Third Party
from defusedxml import minidom
import pytest

# Local repo modules
import conftest

# local repo modules
import oasa


ROUNDTRIP_FIXTURES_DIR = conftest.repo_tests_path("fixtures", "cdml_roundtrip")
LEGACY_FIXTURES_DIR = conftest.repo_tests_path("fixtures", "cdml")


#============================================
def test_cdml_fixtures_load_in_oasa():
	fixtures = [
		"custom_attr.cdml",
		"wavy_color.cdml",
		"vertex_ordering.cdml",
	]
	for name in fixtures:
		path = os.path.join(ROUNDTRIP_FIXTURES_DIR, name)
		with open(path, "r", encoding="utf-8") as handle:
			text = handle.read()
		mol = oasa.cdml.text_to_mol(text)
		assert mol is not None


#============================================
def test_cdml_embedded_svg_contains_cdml():
	path = os.path.join(LEGACY_FIXTURES_DIR, "embedded_cdml.svg")
	if not os.path.isfile(path):
		pytest.skip("Legacy embedded CDML SVG fixture was not kept in this checkout")
	with open(path, "r", encoding="utf-8") as handle:
		text = handle.read()
	doc = minidom.parseString(text)
	cdml_nodes = doc.getElementsByTagNameNS("http://www.freesoftware.fsf.org/bkchem/cdml", "cdml")
	assert cdml_nodes
