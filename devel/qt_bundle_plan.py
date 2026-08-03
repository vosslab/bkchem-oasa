#!/usr/bin/env python3

"""Describe the Qt-only macOS bundle inputs without creating an artifact."""

# Standard Library
import argparse
import dataclasses
import importlib.util
import json
import pathlib


APP_NAME = "BKChem"
BUNDLE_IDENTIFIER = "org.bkchem.BKChem"
ENTRY_MODULE = "bkchem_qt.cli"
LEGACY_RUNTIME_MARKERS = (
	"addons",
	"bkchem-app",
	"bkchem_data",
	"bkchem.cli",
	"tkinter",
	"_tkinter",
)


@dataclasses.dataclass(frozen=True)
class BundleData:
	"""Describe one source tree copied to a bundle-relative destination."""

	source: str
	destination: str


@dataclasses.dataclass(frozen=True)
class QtBundlePlan:
	"""Describe all deterministic inputs for the experimental Qt application bundle."""

	app_name: str
	bundle_name: str
	bundle_identifier: str
	entry_module: str
	entry_script: str
	python_paths: tuple[str, ...]
	data_files: tuple[BundleData, ...]
	hidden_imports: tuple[str, ...]
	excluded_modules: tuple[str, ...]
	collect_binaries: tuple[str, ...]
	frontend_distribution: str
	frontend_project_dir: str
	icon_source: str
	experimental_output_root: str


#============================================
def _repo_path(repo_root: pathlib.Path, *parts: str) -> str:
	"""Return an absolute path inside the supplied repository root.

	Args:
		repo_root: Repository root used to resolve plan inputs.
		*parts: Relative path components below the repository root.

	Returns:
		Absolute string path below the repository root.
	"""
	path = repo_root.joinpath(*parts)
	return str(path)


#============================================
def _action_hidden_imports(actions_dir: pathlib.Path) -> tuple[str, ...]:
	"""Load action hidden imports from the shared immutable registrar manifest.

	Args:
		actions_dir: Directory containing the Qt action modules.

	Returns:
		Qualified action registrar module names in stable startup order.
	"""
	manifest_path = actions_dir / "registrar_manifest.py"
	spec = importlib.util.spec_from_file_location(
		"qt_bundle_action_registrar_manifest", manifest_path,
	)
	if spec is None or spec.loader is None:
		raise ValueError("Qt action registrar manifest cannot be loaded")
	manifest = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(manifest)
	modules = getattr(manifest, "ACTION_REGISTRAR_MODULES", None)
	if not isinstance(modules, tuple) or not all(
		isinstance(module_name, str) for module_name in modules
	):
		raise ValueError("Qt action registrar manifest must be a tuple of module names")
	return modules


#============================================
def make_qt_bundle_plan(repo_root: pathlib.Path) -> QtBundlePlan:
	"""Create the immutable Qt-only bundle plan for a repository checkout.

	Args:
		repo_root: Repository root containing the Qt frontend and OASA backend.

	Returns:
		The side-effect-free Qt bundle plan.
	"""
	root = repo_root.resolve()
	qt_package = root / "packages" / "bkchem-qt.app" / "bkchem_qt"
	actions_dir = qt_package / "actions"
	data_files = (
		BundleData(
			source=_repo_path(root, "packages", "bkchem-qt.app", "bkchem_qt", "resources"),
			destination="bkchem_qt/resources",
		),
		BundleData(
			source=_repo_path(root, "packages", "oasa", "oasa_data"),
			destination="oasa_data",
		),
		BundleData(source=_repo_path(root, "VERSION"), destination="."),
	)
	hidden_imports = (
		"oasa",
		"bkchem_qt.bridge.worker",
		"PySide6.QtCore",
		"PySide6.QtGui",
		"PySide6.QtSvg",
		"PySide6.QtSvgWidgets",
		"PySide6.QtWidgets",
		*_action_hidden_imports(actions_dir),
	)
	plan = QtBundlePlan(
		app_name=APP_NAME,
		bundle_name="BKChem.app",
		bundle_identifier=BUNDLE_IDENTIFIER,
		entry_module=ENTRY_MODULE,
		entry_script=_repo_path(root, "devel", "bkchem_qt_entry.py"),
		python_paths=(
			_repo_path(root, "packages", "bkchem-qt.app"),
			_repo_path(root, "packages", "oasa"),
		),
		data_files=data_files,
		hidden_imports=hidden_imports,
		excluded_modules=("tkinter", "_tkinter", "PIL.ImageTk"),
		collect_binaries=("rdkit", "cairo", "rustworkx"),
		frontend_distribution="bkchem-qt",
		frontend_project_dir=_repo_path(root, "packages", "bkchem-qt.app"),
		icon_source=_repo_path(
			root, "packages", "bkchem-qt.app", "bkchem_qt", "resources", "app_icon.svg"
		),
		experimental_output_root=_repo_path(root, "tmp", "qt_bundle"),
	)
	validate_qt_bundle_plan(plan)
	return plan


#============================================
def validate_qt_bundle_plan(plan: QtBundlePlan) -> None:
	"""Validate that a plan is Qt-only and names checked-in build inputs.

	Args:
		plan: Bundle plan to validate before a future controlled build.

	Raises:
		ValueError: If a required plan input is absent or names a legacy runtime.
	"""
	if plan.entry_module != ENTRY_MODULE:
		raise ValueError(f"Qt plan entry module must be {ENTRY_MODULE}")
	paths = (*plan.python_paths, plan.entry_script, plan.frontend_project_dir, plan.icon_source)
	paths += tuple(data_file.source for data_file in plan.data_files)
	for path_text in paths:
		if not pathlib.Path(path_text).exists():
			raise ValueError(f"Qt bundle input does not exist: {path_text}")
	for value in (
		*paths,
		*(data_file.destination for data_file in plan.data_files),
		*plan.hidden_imports,
		*plan.collect_binaries,
	):
		lower_value = value.lower()
		if any(marker in lower_value for marker in LEGACY_RUNTIME_MARKERS):
			raise ValueError(f"Qt bundle plan contains a legacy runtime input: {value}")
	if not plan.frontend_distribution:
		raise ValueError("Qt bundle frontend distribution must be nonempty")
	if not {"tkinter", "_tkinter", "PIL.ImageTk"}.issubset(plan.excluded_modules):
		raise ValueError("Qt bundle plan must exclude the Tcl/Tk runtime modules")
	if not (pathlib.Path(plan.frontend_project_dir) / "pyproject.toml").is_file():
		raise ValueError("Qt bundle frontend project must contain pyproject.toml")


#============================================
def plan_as_json(plan: QtBundlePlan) -> str:
	"""Render a stable, serializable plan representation for inspection.

	Args:
		plan: Validated plan to render.

	Returns:
		Indented deterministic JSON text followed by a newline.
	"""
	plan_data = dataclasses.asdict(plan)
	text = json.dumps(plan_data, indent=2, sort_keys=True)
	return text + "\n"


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments for plan inspection.

	Returns:
		Parsed plan inspection arguments.
	"""
	parser = argparse.ArgumentParser(description="Inspect the Qt-only BKChem bundle plan.")
	parser.add_argument("--json", action="store_true", help="Print the plan as JSON.")
	parser.add_argument("--repo-root", type=pathlib.Path, default=None, help="Repository root.")
	args = parser.parse_args()
	return args


#============================================
def main() -> None:
	"""Print the validated Qt bundle plan without writing any files."""
	args = parse_args()
	if args.repo_root is None:
		repo_root = pathlib.Path(__file__).resolve().parents[1]
	else:
		repo_root = args.repo_root
	plan = make_qt_bundle_plan(repo_root)
	if args.json:
		print(plan_as_json(plan), end="")
	else:
		print(f"Qt bundle plan: {plan.app_name} via {plan.entry_module}")
		print(f"Experimental output: {plan.experimental_output_root}")


#============================================

if __name__ == "__main__":
	main()
