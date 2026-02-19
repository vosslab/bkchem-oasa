"""Smoke test for CDML version transforms."""

# Standard Library
import os
from defusedxml import minidom

# Third Party
import pytest

# Local repo modules
import conftest

# local repo modules
import CDML_versions
import config


#============================================
def build_cdml(version):
	doc = minidom.parseString(f'<cdml version="{version}"></cdml>')
	return doc.documentElement


#============================================
def test_cdml_transform_legacy_to_current():
	dom = build_cdml("0.16")
	assert CDML_versions.transform_dom_to_version(dom, config.current_CDML_version) == 1


#============================================
def test_cdml_transform_old_to_current():
	dom = build_cdml("0.15")
	assert CDML_versions.transform_dom_to_version(dom, config.current_CDML_version) == 1


#============================================
def test_cdml_transform_legacy_fixture():
	fixture_path = conftest.repo_tests_path("fixtures", "cdml", "legacy_v0.11.cdml")
	if not os.path.isfile(fixture_path):
		pytest.skip("Legacy v0.11 CDML fixture was removed from this checkout")
	with open(fixture_path, "r", encoding="utf-8") as handle:
		text = handle.read()
	doc = minidom.parseString(text)
	dom = doc.documentElement
	assert CDML_versions.transform_dom_to_version(dom, config.current_CDML_version) == 1
