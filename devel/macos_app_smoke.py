"""Validate direct and native launch routes for one built macOS app."""

# Standard Library
import dataclasses
import enum
import json
import math
import os
import pathlib
import shlex
import subprocess
from collections.abc import Callable, Mapping


SMOKE_STARTUP_ALLOWANCE_SECONDS = 10.0
SMOKE_RECEIPT_SCHEMA = "bkchem-smoke-1"

ProcessRunner = Callable[
	[tuple[str, ...], pathlib.Path, float],
	subprocess.CompletedProcess[str],
]


#============================================
class MacSmokeRoute(enum.Enum):
	"""Identify one independently observable macOS application launch route."""

	DIRECT = ("direct", "smoke")
	NATIVE = ("native LaunchServices", "native_launch")

	def __init__(self, label: str, artifact_directory: str) -> None:
		"""Retain the diagnostic label and owned artifact directory."""
		self.label = label
		self.artifact_directory = artifact_directory


MACOS_SMOKE_ROUTES = (MacSmokeRoute.DIRECT, MacSmokeRoute.NATIVE)


#============================================
class SmokePathError(RuntimeError):
	"""Report a smoke artifact path that escapes its selected build run root."""


#============================================
@dataclasses.dataclass(frozen=True)
class MacSmokePaths:
	"""Describe validated resolved paths for one app lifecycle smoke."""

	root: pathlib.Path
	stdout_path: pathlib.Path
	stderr_path: pathlib.Path
	receipt_path: pathlib.Path


#============================================
def make_smoke_args(
		route: MacSmokeRoute, app_path: pathlib.Path, seconds: float,
		smoke_root: pathlib.Path,
		) -> tuple[str, ...]:
	"""Return one bounded command for the selected application launch route."""
	if not math.isfinite(seconds) or seconds <= 0.0:
		raise ValueError("--smoke-exit must be a finite positive number of seconds")
	app_arguments = (
		"--smoke-exit", str(seconds),
		"--smoke-receipt", str(smoke_root / "completion.json"),
	)
	if route is MacSmokeRoute.DIRECT:
		return (str(app_path / "Contents" / "MacOS" / "BKChem"), *app_arguments)
	if route is MacSmokeRoute.NATIVE:
		return ("/usr/bin/open", "-n", "-W", str(app_path), "--args", *app_arguments)
	raise ValueError(f"Unsupported macOS smoke route: {route!r}")


#============================================
def resolve_macos_smoke_paths(
		smoke_root: pathlib.Path, build_run_root: pathlib.Path,
		) -> MacSmokePaths:
	"""Resolve and contain every smoke artifact below one selected build run."""
	resolved_run_root = build_run_root.resolve()
	resolved_smoke_root = smoke_root.resolve()
	if resolved_smoke_root == resolved_run_root:
		raise SmokePathError(
			"macOS smoke root must be a child of the selected build run root: "
			f"{resolved_smoke_root}"
		)
	candidates = {
		"smoke root": resolved_smoke_root,
		"smoke stdout log": (resolved_smoke_root / "stdout.log").resolve(),
		"smoke stderr log": (resolved_smoke_root / "stderr.log").resolve(),
		"smoke receipt": (resolved_smoke_root / "completion.json").resolve(),
	}
	for label, candidate in candidates.items():
		if not candidate.is_relative_to(resolved_run_root):
			raise SmokePathError(
				f"{label} escapes selected build run root {resolved_run_root}: {candidate}"
			)
	return MacSmokePaths(
		root=candidates["smoke root"],
		stdout_path=candidates["smoke stdout log"],
		stderr_path=candidates["smoke stderr log"],
		receipt_path=candidates["smoke receipt"],
	)


#============================================
def _validate_smoke_receipt(receipt_path: pathlib.Path) -> None:
	"""Require one exact successful application lifecycle receipt."""
	try:
		payload = json.loads(receipt_path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise RuntimeError(f"Missing or invalid smoke receipt: {receipt_path}: {error}") from error
	if payload != {"schema": SMOKE_RECEIPT_SCHEMA, "exit_code": 0}:
		raise RuntimeError(f"Invalid smoke receipt: {receipt_path}: {payload!r}")


#============================================
def _fatal_smoke_diagnostic(stderr_path: pathlib.Path) -> str | None:
	"""Return one retained fatal process diagnostic, when present."""
	try:
		stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
	except OSError as error:
		raise RuntimeError(f"Missing macOS smoke stderr log: {stderr_path}: {error}") from error
	for marker in (
		"Abort trap", "Fatal Python error", "Segmentation fault", "EXC_CRASH", "EXC_BAD_ACCESS",
	):
		if marker in stderr:
			return marker
	return None


#============================================
def _write_smoke_logs(
		paths: MacSmokePaths, result: subprocess.CompletedProcess[str],
		) -> None:
	"""Retain route output next to its application lifecycle receipt."""
	try:
		paths.stdout_path.write_text(result.stdout, encoding="utf-8")
		paths.stderr_path.write_text(result.stderr, encoding="utf-8")
	except OSError as error:
		raise RuntimeError(f"Could not retain macOS smoke output: {error}") from error


#============================================
def _run_smoke_command(
		route: MacSmokeRoute, command: tuple[str, ...], cwd: pathlib.Path,
		timeout_seconds: float,
		) -> subprocess.CompletedProcess[str]:
	"""Run one route with an environment that preserves its intended boundary."""
	environment = dict(os.environ)
	if route is MacSmokeRoute.DIRECT:
		environment["QT_QPA_PLATFORM"] = "offscreen"
	elif route is MacSmokeRoute.NATIVE:
		environment.pop("QT_QPA_PLATFORM", None)
	else:
		raise ValueError(f"Unsupported macOS smoke route: {route!r}")
	return subprocess.run(
		command, cwd=cwd, env=environment, capture_output=True, text=True, check=False,
		timeout=timeout_seconds,
	)


#============================================
def run_macos_smoke(
		route: MacSmokeRoute, app_path: pathlib.Path, seconds: float,
		smoke_root: pathlib.Path, build_run_root: pathlib.Path, repo_root: pathlib.Path,
		runner: ProcessRunner | None = None,
		) -> None:
	"""Run one bounded route and require app-owned completion proof."""
	smoke_paths = resolve_macos_smoke_paths(smoke_root, build_run_root)
	if smoke_paths.root.exists():
		raise RuntimeError(f"macOS {route.label} smoke root must be fresh: {smoke_paths.root}")
	smoke_paths.root.mkdir(parents=True)
	command = make_smoke_args(route, app_path, seconds, smoke_paths.root)
	timeout_seconds = seconds + SMOKE_STARTUP_ALLOWANCE_SECONDS
	def default_runner(
			child_command: tuple[str, ...], cwd: pathlib.Path, timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Run the selected production route when no test seam is injected."""
		return _run_smoke_command(route, child_command, cwd, timeout)

	process_runner = runner or default_runner
	try:
		result = process_runner(command, repo_root, timeout_seconds)
	except subprocess.TimeoutExpired as error:
		raise RuntimeError(
			f"macOS {route.label} smoke timed out after {timeout_seconds:g}s: "
			f"{shlex.join(command)}"
		) from error
	_write_smoke_logs(smoke_paths, result)
	if result.returncode != 0:
		raise RuntimeError(
			f"macOS {route.label} smoke failed ({result.returncode}): "
			f"{shlex.join(command)}\n"
			f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
		)
	_validate_smoke_receipt(smoke_paths.receipt_path)
	fatal_diagnostic = _fatal_smoke_diagnostic(smoke_paths.stderr_path)
	if fatal_diagnostic is not None:
		raise RuntimeError(
			f"macOS {route.label} smoke recorded fatal process diagnostic "
			f"{fatal_diagnostic!r}: {smoke_paths.stderr_path}"
		)


#============================================
def run_macos_smoke_suite(
		app_path: pathlib.Path, seconds: float, build_run_root: pathlib.Path,
		repo_root: pathlib.Path,
		runners: Mapping[MacSmokeRoute, ProcessRunner] | None = None,
		) -> None:
	"""Validate direct lifecycle and native user-launch routes independently."""
	selected_runners = runners or {}
	for route in MACOS_SMOKE_ROUTES:
		run_macos_smoke(
			route, app_path, seconds, build_run_root / route.artifact_directory,
			build_run_root, repo_root, selected_runners.get(route),
		)
