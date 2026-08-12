"""Behavior and import-boundary coverage for Qt release metadata."""

# Standard Library
import importlib.metadata
import pathlib
from unittest import mock

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.bridge.release_metadata


#============================================
def test_source_registry_produces_the_frontend_display_version(tmp_path: pathlib.Path) -> None:
	"""A recognized checkout obtains its user-facing label from root VERSION."""
	version_path = tmp_path / "VERSION"
	version_path.write_text("version = 26.07\n", encoding="utf-8")

	assert bkchem_qt.bridge.release_metadata.read_source_tree_display_version(version_path) == "26.07"


#============================================
def test_invalid_source_registry_reports_the_typed_boundary_failure(
		tmp_path: pathlib.Path,
		) -> None:
	"""A malformed checkout registry cannot become a guessed display label."""
	version_path = tmp_path / "VERSION"
	version_path.write_text("version = invalid\n", encoding="utf-8")

	with pytest.raises(
		bkchem_qt.bridge.release_metadata.ReleaseMetadataError,
		match="Unable to read VERSION file",
	):
		bkchem_qt.bridge.release_metadata.read_source_tree_display_version(version_path)


#============================================
def test_installed_metadata_normalizes_to_the_frontend_display_version() -> None:
	"""Wheel metadata becomes the same zero-padded label used by the CLI and UI."""
	with mock.patch.object(
			bkchem_qt.bridge.release_metadata.importlib.metadata,
			"version", return_value="26.7",
			):
		assert (
			bkchem_qt.bridge.release_metadata.installed_display_version("bkchem-qt")
			== "26.07"
		)


#============================================
def test_invalid_installed_metadata_reports_the_typed_boundary_failure() -> None:
	"""Unexpected wheel metadata fails explicitly instead of inventing a release label."""
	with mock.patch.object(
			bkchem_qt.bridge.release_metadata.importlib.metadata,
			"version", return_value="not-a-bkchem-release",
			):
		with pytest.raises(
			bkchem_qt.bridge.release_metadata.ReleaseMetadataError,
			match="Unsupported installed BKChem-Qt version metadata",
		):
			bkchem_qt.bridge.release_metadata.installed_display_version("bkchem-qt")


#============================================
def test_missing_installed_metadata_reports_the_typed_boundary_failure() -> None:
	"""An installed-layout lookup identifies absent package metadata clearly."""
	def missing_metadata(_name: str) -> str:
		raise importlib.metadata.PackageNotFoundError

	with mock.patch.object(
			bkchem_qt.bridge.release_metadata.importlib.metadata,
			"version", side_effect=missing_metadata,
			):
		with pytest.raises(
			bkchem_qt.bridge.release_metadata.ReleaseMetadataError,
			match="BKChem-Qt package metadata is unavailable",
		):
			bkchem_qt.bridge.release_metadata.installed_display_version("bkchem-qt")
