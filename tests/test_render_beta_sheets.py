"""Behavior tests for the beta-sheet CDML fixture generator."""

# Standard Library
import pathlib

# PIP3 modules
from defusedxml import minidom

# local repo modules
import bkchem.versioning
import oasa.cdml_writer
from tools import render_beta_sheets


#============================================
def test_beta_sheet_cdml_separates_format_and_author_versions(tmp_path: pathlib.Path) -> None:
	"""Generated CDML keeps format profile and authoring release independent."""
	output_path = tmp_path / "sheet.cdml"
	render_beta_sheets._write_cdml_file([], str(output_path))
	document = minidom.parse(str(output_path))
	root = document.documentElement
	author = root.getElementsByTagName("author_program")[0]

	assert root.getAttribute("version") == oasa.cdml_writer.DEFAULT_CDML_VERSION
	assert author.getAttribute("version") == bkchem.versioning.application_version()
