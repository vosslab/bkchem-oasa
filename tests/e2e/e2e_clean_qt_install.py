#!/usr/bin/env python3
"""Build local wheels and prove BKChem-Qt runs from a clean installed environment."""

# Standard Library
import argparse
import email.parser
import importlib
import importlib.metadata
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile


RECEIPT_SCHEMA = "bkchem-clean-install-1"
REQUIRED_DISTRIBUTIONS = ("oasa", "bkchem-qt")


#============================================
def _parse_args() -> argparse.Namespace:
	"""Parse the installed-interpreter verification mode."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--verify-installed", action="store_true",
		help="verify installed package origins and console entry points",
	)
	parser.add_argument(
		"--run-root", metavar="PATH",
		help="retained clean-install evidence directory for installed verification",
	)
	args = parser.parse_args()
	if args.verify_installed and args.run_root is None:
		parser.error("--verify-installed requires --run-root")
	if not args.verify_installed and args.run_root is not None:
		parser.error("--run-root is used only with --verify-installed")
	return args


#============================================
def _repo_root() -> pathlib.Path:
	"""Return the repository root from this durable E2E script location."""
	return pathlib.Path(__file__).resolve().parents[2]


#============================================
def _require_repo_tmp(path: pathlib.Path) -> None:
	"""Require retained evidence to stay inside the repository-owned tmp directory."""
	tmp_root = _repo_root() / "tmp"
	try:
		path.relative_to(tmp_root)
	except ValueError as error:
		raise RuntimeError("clean-install evidence must stay inside %s: %s" % (tmp_root, path)) from error


#============================================
def _isolated_environment(run_root: pathlib.Path) -> dict[str, str]:
	"""Return subprocess variables that isolate package resolution from the checkout."""
	environment = os.environ.copy()
	environment.pop("PYTHONPATH", None)
	environment["CC"] = "/usr/bin/clang"
	environment["PIP_CACHE_DIR"] = str(run_root / "pip_cache")
	return environment


#============================================
def _write_text(path: pathlib.Path, text: str) -> None:
	"""Write retained UTF-8 evidence to a fresh path."""
	if path.exists():
		raise RuntimeError("evidence path already exists: %s" % path)
	path.write_text(text, encoding="utf-8")


#============================================
def _command_label(command: tuple[str, ...]) -> str:
	"""Return one readable command label for retained logs."""
	return " ".join(command)


#============================================
def _run_logged(
		command: tuple[str, ...], cwd: pathlib.Path, environment: dict[str, str],
		log_path: pathlib.Path,
		) -> None:
	"""Run one release step and retain its combined output for diagnosis."""
	if log_path.exists():
		raise RuntimeError("command log already exists: %s" % log_path)
	with log_path.open("x", encoding="utf-8") as output:
		output.write("$ %s\n\n" % _command_label(command))
		output.flush()
		result = subprocess.run(
			command,
			cwd=cwd,
			env=environment,
			stdout=output,
			stderr=subprocess.STDOUT,
			check=False,
		)
	if result.returncode != 0:
		raise RuntimeError(
			"release step failed with exit %d: %s (see %s)" % (
				result.returncode, _command_label(command), log_path,
			)
		)


#============================================
def _wheel_for_project(wheel_dir: pathlib.Path, distribution: str) -> pathlib.Path:
	"""Return the one fresh wheel produced for one named local distribution."""
	wheels = tuple(sorted(wheel_dir.glob("*.whl")))
	if len(wheels) != 1:
		raise RuntimeError(
			"expected one wheel for %s, found %s in %s" % (
				distribution, len(wheels), wheel_dir,
			)
		)
	wheel_path = wheels[0]
	with zipfile.ZipFile(wheel_path) as archive:
		metadata_names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
		if len(metadata_names) != 1:
			raise RuntimeError("wheel lacks one metadata record: %s" % wheel_path)
		metadata_text = archive.read(metadata_names[0]).decode("utf-8")
	metadata = email.parser.Parser().parsestr(metadata_text)
	if metadata["Name"] != distribution:
		raise RuntimeError(
			"wheel distribution is %s, expected %s: %s" % (
				metadata["Name"], distribution, wheel_path,
			)
		)
	return wheel_path


#============================================
def _require_python_312() -> None:
	"""Require the repository's supported Python interpreter before building wheels."""
	if sys.version_info[:2] != (3, 12):
		raise RuntimeError("clean-install gate requires Python 3.12, found %s" % sys.version)


#============================================
def _release_display_version(repo_root: pathlib.Path) -> str:
	"""Read the declared public release label without importing checkout packages."""
	for raw_line in (repo_root / "VERSION").read_text(encoding="utf-8").splitlines():
		key, separator, value = raw_line.partition("=")
		if separator and key.strip() == "version" and value.strip():
			return value.strip()
	raise RuntimeError("root VERSION has no declared release label")


#============================================
def _require_isolated_venv(venv_path: pathlib.Path) -> None:
	"""Prove the fresh venv cannot inherit system site packages."""
	configuration = (venv_path / "pyvenv.cfg").read_text(encoding="utf-8")
	if "include-system-site-packages = false" not in configuration:
		raise RuntimeError("venv is not dependency-isolated: %s" % venv_path)


#============================================
def _installed_module_origin(module_name: str, venv_path: pathlib.Path) -> str:
	"""Return one installed module origin and reject checkout-package resolution."""
	module = importlib.import_module(module_name)
	origin_text = getattr(module, "__file__", None)
	if not isinstance(origin_text, str):
		raise RuntimeError("installed module has no origin: %s" % module_name)
	origin = pathlib.Path(origin_text).resolve()
	repository_packages = _repo_root() / "packages"
	try:
		origin.relative_to(repository_packages)
	except ValueError:
		pass
	else:
		raise RuntimeError("installed module resolved from checkout packages: %s" % origin)
	try:
		origin.relative_to(venv_path.resolve())
	except ValueError as error:
		raise RuntimeError("installed module is outside fresh venv: %s" % origin) from error
	return str(origin)


#============================================
def _verify_installed(run_root: pathlib.Path) -> int:
	"""Write installed-origin and console-entry evidence from the fresh venv process."""
	_require_repo_tmp(run_root)
	if "PYTHONPATH" in os.environ:
		raise RuntimeError("installed verification requires PYTHONPATH to be absent")
	venv_path = run_root / "venv"
	_require_isolated_venv(venv_path)
	origins = {
		"bkchem_qt": _installed_module_origin("bkchem_qt", venv_path),
		"oasa": _installed_module_origin("oasa", venv_path),
	}
	for distribution in REQUIRED_DISTRIBUTIONS:
		importlib.metadata.distribution(distribution)
	entries = [
		(entry.name, entry.value)
		for entry in importlib.metadata.entry_points(group="console_scripts")
		if entry.name.startswith("bkchem") or entry.value.startswith("bkchem")
	]
	if entries != [("bkchem-qt", "bkchem_qt.cli:main")]:
		raise RuntimeError("installed environment has unexpected BKChem console entries: %r" % entries)
	payload = {
		"console_entries": entries,
		"installed_origins": origins,
		"installed_versions": {
			"bkchem-qt": importlib.metadata.version("bkchem-qt"),
			"oasa": importlib.metadata.version("oasa"),
		},
		"schema": RECEIPT_SCHEMA,
		"status": "installed-origin-verified",
	}
	_write_text(run_root / "installed_verification.json", json.dumps(payload, sort_keys=True) + "\n")
	print(json.dumps(payload, sort_keys=True))
	return 0


#============================================
def _receipt_completed(path: pathlib.Path) -> None:
	"""Require one authoritative lifecycle receipt to prove complete installation behavior."""
	payload = json.loads(path.read_text(encoding="utf-8"))
	if payload.get("status") != "completed":
		raise RuntimeError("authoritative roundtrip did not complete: %s" % path)
	if payload.get("exit_code") != 0:
		raise RuntimeError("authoritative roundtrip has a nonzero receipt exit: %s" % path)


#============================================
def _run_gate() -> int:
	"""Build fresh local wheels and exercise the installed authoritative Qt workflow twice."""
	_require_python_312()
	repo_root = _repo_root()
	tmp_root = repo_root / "tmp"
	if not tmp_root.is_dir():
		raise RuntimeError("repository tmp directory is missing: %s" % tmp_root)
	run_root = pathlib.Path(tempfile.mkdtemp(prefix="clean_qt_install.", dir=tmp_root))
	_require_repo_tmp(run_root)
	logs_dir = run_root / "logs"
	wheel_root = run_root / "wheels"
	venv_path = run_root / "venv"
	logs_dir.mkdir()
	wheel_root.mkdir()
	environment = _isolated_environment(run_root)
	python_path = pathlib.Path(sys.executable).resolve()
	projects = (
		("oasa", repo_root / "packages" / "oasa"),
		("bkchem-qt", repo_root / "packages" / "bkchem-qt.app"),
	)
	wheels = []
	for distribution, project_path in projects:
		wheel_dir = wheel_root / distribution
		wheel_dir.mkdir()
		command = (
			str(python_path), "-m", "build", "--wheel", "--no-isolation",
			"--outdir", str(wheel_dir), str(project_path),
		)
		_run_logged(command, repo_root, environment, logs_dir / (distribution + "_wheel_build.log"))
		wheels.append(_wheel_for_project(wheel_dir, distribution))
	_run_logged(
		(str(python_path), "-m", "venv", str(venv_path)), repo_root, environment,
		logs_dir / "venv_create.log",
	)
	_require_isolated_venv(venv_path)
	venv_python = venv_path / "bin" / "python"
	_run_logged(
		(
			str(venv_python), "-m", "pip", "install", "--find-links", str(wheel_root / "oasa"),
			"--find-links", str(wheel_root / "bkchem-qt"), *(str(wheel) for wheel in wheels),
		),
		repo_root, environment, logs_dir / "pip_install.log",
	)
	_run_logged(
		(str(venv_python), "-m", "pip", "check"), repo_root, environment,
		logs_dir / "pip_check.log",
	)
	_run_logged(
		(str(venv_python), "-m", "pip", "freeze"), repo_root, environment,
		logs_dir / "pip_freeze.log",
	)
	_run_logged(
		(
			str(venv_python), str(pathlib.Path(__file__).resolve()), "--verify-installed",
			"--run-root", str(run_root),
		),
		repo_root, environment, logs_dir / "installed_verify.log",
	)
	version_log = logs_dir / "bkchem_qt_version.log"
	_run_logged(
		(str(venv_path / "bin" / "bkchem-qt"), "--version"), repo_root, environment,
		version_log,
	)
	version_output = version_log.read_text(encoding="utf-8").split("\n\n", 1)[-1].strip()
	expected_version = "BKChem-Qt " + _release_display_version(repo_root)
	if version_output != expected_version:
		raise RuntimeError(
			"installed bkchem-qt --version is %r, expected %r" % (
				version_output, expected_version,
			)
		)
	gui_environment = environment.copy()
	gui_environment["QT_QPA_PLATFORM"] = "offscreen"
	_run_logged(
		(str(venv_path / "bin" / "bkchem-qt"), "--smoke-exit", "1"), repo_root, gui_environment,
		logs_dir / "bkchem_qt_smoke.log",
	)
	roundtrip_runner = repo_root / "tests" / "e2e" / "e2e_installed_qt_authoritative_roundtrip.py"
	for label in ("one", "two"):
		output_dir = run_root / ("roundtrip_" + label)
		output_dir.mkdir()
		receipt_path = output_dir / "receipt.json"
		_run_logged(
			(
				str(venv_python), "-W", "error", str(roundtrip_runner), "--kill-after", "3",
				"--output", str(output_dir), "--receipt", str(receipt_path),
			),
			repo_root, gui_environment, logs_dir / ("roundtrip_" + label + ".log"),
		)
		_receipt_completed(receipt_path)
	payload = {
		"run_root": str(run_root),
		"schema": RECEIPT_SCHEMA,
		"status": "completed",
		"wheels": [str(wheel) for wheel in wheels],
	}
	_write_text(run_root / "receipt.json", json.dumps(payload, sort_keys=True) + "\n")
	print(json.dumps(payload, sort_keys=True))
	return 0


#============================================
def main() -> int:
	"""Dispatch the clean-install gate or its fresh-interpreter verification mode."""
	args = _parse_args()
	if args.verify_installed:
		return _verify_installed(pathlib.Path(args.run_root).resolve())
	return _run_gate()


if __name__ == "__main__":
	raise SystemExit(main())
