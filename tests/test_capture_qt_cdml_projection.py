"""Behavioral checks for atomic publication of the Qt screenshot catalog."""

# Standard Library
import importlib.util
import os
import pathlib
import sys

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import pytest

# local repo modules
import file_utils
import oasa.cdml_document


REPO_ROOT = pathlib.Path(file_utils.get_repo_root())


#============================================
def _capture_tool() -> object:
	"""Load the runnable capture tool without invoking its command-line entry point."""
	module_name = "capture_qt_cdml_projection_test_module"
	spec = importlib.util.spec_from_file_location(
		module_name, REPO_ROOT / "tools" / "capture_qt_cdml_projection.py",
	)
	if spec is None or spec.loader is None:
		raise RuntimeError("Could not load the Qt screenshot capture tool")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


#============================================
def _write_managed_png(path: pathlib.Path) -> None:
	"""Write one valid managed-size image without opening a QApplication window."""
	image = PySide6.QtGui.QImage(
		PySide6.QtCore.QSize(1280, 800), PySide6.QtGui.QImage.Format.Format_RGB32,
	)
	image.fill(PySide6.QtCore.Qt.GlobalColor.white)
	path.parent.mkdir(parents=True, exist_ok=True)
	if not image.save(str(path), "PNG"):
		raise RuntimeError("Could not write synthetic managed PNG")


#============================================
def test_managed_scenarios_match_authoritative_projection_facts() -> None:
	"""Every catalog fixture proves its advertised current backend facts."""
	tool = _capture_tool()
	for scenario in tool._SCENARIOS:
		backend = oasa.cdml_document.CDMLDocumentSession.load(tool._scenario_cdml(scenario))
		plan = backend.projection_snapshot().plan
		kinds = frozenset(record.kind for record in plan.presentation_description.records)
		assert scenario.required_presentation_kinds <= kinds
		assert all(marker in backend.snapshot().cdml for marker in scenario.required_markers)
	drawing = oasa.cdml_document.CDMLDocumentSession.load(
		tool._scenario_cdml(tool._SCENARIOS_BY_KEY["drawing-objects"]),
	)
	pairs = drawing.projection_snapshot().plan.presentation_description.bracket_pairs
	assert tuple((pair.pair_id, pair.member_ids) for pair in pairs) == (
		("left_bracket", ("left_bracket", "right_bracket")),
	)


#============================================
def test_catalog_publish_restores_existing_gallery_after_late_replacement_failure(
		tmp_path: pathlib.Path,
		) -> None:
	"""A failed catalog publication leaves every previously managed PNG unchanged."""
	tool = _capture_tool()
	staging_root = tmp_path / "staging"
	gallery_root = tmp_path / "gallery"
	for scenario in tool._SCENARIOS:
		_write_managed_png(staging_root / scenario.output_name)
		output_path = gallery_root / scenario.output_name
		output_path.parent.mkdir(parents=True, exist_ok=True)
		output_path.write_bytes(("prior-" + scenario.key).encode("ascii"))
	late_target = gallery_root / tool._SCENARIOS[-1].output_name

	def fail_late_publish(source: pathlib.Path, target: pathlib.Path) -> None:
		"""Reject the final replacement after earlier files were already replaced."""
		if target == late_target:
			raise OSError("injected publication failure")
		os.replace(source, target)

	with pytest.raises(OSError, match="injected publication failure"):
		tool._publish_catalog(staging_root, gallery_root, replace_path=fail_late_publish)

	assert all(
		(gallery_root / scenario.output_name).read_bytes()
		== ("prior-" + scenario.key).encode("ascii")
		for scenario in tool._SCENARIOS
	)


#============================================
def test_catalog_publish_requires_complete_staged_generation_before_replacing_gallery(
		tmp_path: pathlib.Path,
		) -> None:
	"""An incomplete staged generation leaves the managed gallery unmodified."""
	tool = _capture_tool()
	staging_root = tmp_path / "staging"
	gallery_root = tmp_path / "gallery"
	for scenario in tool._SCENARIOS[:-1]:
		_write_managed_png(staging_root / scenario.output_name)
	for scenario in tool._SCENARIOS:
		output_path = gallery_root / scenario.output_name
		output_path.parent.mkdir(parents=True, exist_ok=True)
		output_path.write_bytes(("prior-" + scenario.key).encode("ascii"))

	with pytest.raises(tool.CaptureFailure, match="did not produce"):
		tool._publish_catalog(staging_root, gallery_root)

	assert all(
		(gallery_root / scenario.output_name).read_bytes()
		== ("prior-" + scenario.key).encode("ascii")
		for scenario in tool._SCENARIOS
	)
