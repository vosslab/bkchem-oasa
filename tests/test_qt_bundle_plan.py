"""Focused tests for the side-effect-free Qt macOS bundle manifest."""

# Standard Library
import ast
import dataclasses
import pathlib
import sys

# PIP3 modules
import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "devel"))

# local repo modules
import qt_bundle_plan

# local repo modules
import bkchem_qt.actions.registrar_manifest


#============================================
def test_plan_uses_qt_entrypoint_and_backend_owned_data() -> None:
	"""The future frozen application names Qt, OASA data, and package resources."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	destinations = tuple(data_file.destination for data_file in plan.data_files)
	identity = (
		plan.entry_module, destinations, plan.app_name, plan.bundle_name,
		plan.bundle_identifier, plan.frontend_distribution,
		pathlib.Path(plan.frontend_project_dir).name,
	)

	assert identity == (
		"bkchem_qt.cli", ("bkchem_qt/resources", "oasa_data", "."), "BKChem", "BKChem.app",
		"org.bkchem.BKChem", "bkchem-qt", "bkchem-qt.app",
	)
	assert {"tkinter", "_tkinter"}.issubset(plan.excluded_modules)


#============================================
@pytest.mark.parametrize("required_module", ("tkinter", "_tkinter", "PIL.ImageTk"))
def test_plan_rejects_removing_required_tcl_tk_exclusions(required_module: str) -> None:
	"""The frozen Qt plan preserves exclusions that prevent optional PIL Tk hooks."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	reduced_plan = dataclasses.replace(
		plan, excluded_modules=tuple(module for module in plan.excluded_modules if module != required_module),
	)

	with pytest.raises(ValueError, match="Tcl/Tk"):
		qt_bundle_plan.validate_qt_bundle_plan(reduced_plan)


#============================================
@pytest.mark.parametrize(("field", "legacy_marker"), (
	("python_paths", "bkchem-app"),
	("hidden_imports", "tkinter"),
	("hidden_imports", "_tkinter"),
	("hidden_imports", "bkchem.cli"),
	("collect_binaries", "tkinter"),
	("collect_binaries", "bkchem-app/bkchem"),
	("data_file_source", "packages/bkchem-app"),
	("data_file_destination", "bkchem_data"),
))
def test_plan_rejects_legacy_runtime_inputs(field: str, legacy_marker: str) -> None:
	"""Validation blocks legacy frontend inputs before build commands are created."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	if field == "data_file_source":
		legacy_data = dataclasses.replace(
			plan.data_files[0], source=str(REPO_ROOT / legacy_marker)
		)
		legacy_plan = dataclasses.replace(plan, data_files=(legacy_data, *plan.data_files[1:]))
	elif field == "data_file_destination":
		legacy_data = dataclasses.replace(plan.data_files[0], destination=legacy_marker)
		legacy_plan = dataclasses.replace(plan, data_files=(legacy_data, *plan.data_files[1:]))
	else:
		values = getattr(plan, field)
		legacy_value = legacy_marker
		if legacy_marker == "bkchem-app":
			legacy_value = str(REPO_ROOT / "packages" / legacy_marker)
		legacy_plan = dataclasses.replace(plan, **{field: (*values, legacy_value)})

	with pytest.raises(ValueError, match="legacy runtime"):
		qt_bundle_plan.validate_qt_bundle_plan(legacy_plan)


#============================================
def test_action_hidden_imports_match_the_runtime_registrar_manifest() -> None:
	"""PyInstaller hidden imports reuse the frozen runtime registration authority."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	action_imports = tuple(
		module_name for module_name in plan.hidden_imports
		if module_name.startswith("bkchem_qt.actions.")
	)

	assert action_imports == bkchem_qt.actions.registrar_manifest.ACTION_REGISTRAR_MODULES


#============================================
def test_plan_module_uses_only_stdlib_imports() -> None:
	"""Plan inspection stays available without Qt, OASA, or PyInstaller imports."""
	module_path = REPO_ROOT / "devel" / "qt_bundle_plan.py"
	module_tree = ast.parse(module_path.read_text(encoding="utf-8"))
	import_roots = set()
	for node in ast.walk(module_tree):
		if isinstance(node, ast.Import):
			import_roots.update(alias.name.split(".")[0] for alias in node.names)
		elif isinstance(node, ast.ImportFrom) and node.module is not None:
			import_roots.add(node.module.split(".")[0])

	assert import_roots <= sys.stdlib_module_names


#============================================
