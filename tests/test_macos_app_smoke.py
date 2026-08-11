"""Behavior tests for independent direct and native macOS app smoke routes."""

# Standard Library
import os
import pathlib
import subprocess
import sys

# PIP3 modules
import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "devel"))

# local repo modules
import macos_app_smoke


DIRECT = macos_app_smoke.MacSmokeRoute.DIRECT
NATIVE = macos_app_smoke.MacSmokeRoute.NATIVE


#============================================
def _write_success_receipt(command: tuple[str, ...]) -> None:
	"""Publish the fixed receipt at the path selected by one smoke command."""
	receipt_path = pathlib.Path(command[command.index("--smoke-receipt") + 1])
	receipt_path.write_text(
		'{"schema":"bkchem-smoke-1","exit_code":0}', encoding="utf-8",
	)


#============================================
def test_smoke_commands_preserve_independent_direct_and_native_routes(
		tmp_path: pathlib.Path,
		) -> None:
	"""Each route supplies the same lifecycle arguments through its real boundary."""
	app_path = tmp_path / "BKChem.app"
	direct_root = tmp_path / "smoke"
	native_root = tmp_path / "native_launch"
	direct_command = macos_app_smoke.make_smoke_args(DIRECT, app_path, 2.0, direct_root)
	native_command = macos_app_smoke.make_smoke_args(NATIVE, app_path, 2.0, native_root)

	assert direct_command == (
		str(app_path / "Contents" / "MacOS" / "BKChem"),
		"--smoke-exit", "2.0", "--smoke-receipt", str(direct_root / "completion.json"),
	)
	assert native_command == (
		"/usr/bin/open", "-n", "-W", str(app_path), "--args",
		"--smoke-exit", "2.0", "--smoke-receipt", str(native_root / "completion.json"),
	)


#============================================
def test_route_runners_enforce_offscreen_direct_and_native_display_environments(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
		) -> None:
	"""A caller's Qt platform override cannot turn native validation offscreen."""
	seen_environments: list[dict[str, str]] = []

	def record_process(
			_command: tuple[str, ...], *, cwd: pathlib.Path, env: dict[str, str],
			capture_output: bool, text: bool, check: bool, timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Record only the child environments selected by the production runner."""
		assert cwd == tmp_path
		assert capture_output and text and not check and timeout == 12.0
		seen_environments.append(env)
		return subprocess.CompletedProcess(_command, 0, "", "")

	monkeypatch.setenv("QT_QPA_PLATFORM", "caller-override")
	monkeypatch.setattr(macos_app_smoke.subprocess, "run", record_process)
	macos_app_smoke._run_smoke_command(DIRECT, ("direct",), tmp_path, 12.0)
	macos_app_smoke._run_smoke_command(NATIVE, ("native",), tmp_path, 12.0)

	assert seen_environments[0]["QT_QPA_PLATFORM"] == "offscreen"
	assert "QT_QPA_PLATFORM" not in seen_environments[1]
	assert os.environ["QT_QPA_PLATFORM"] == "caller-override"


#============================================
def test_smoke_receipt_validator_requires_the_fixed_success_schema(tmp_path: pathlib.Path) -> None:
	"""Only an exact zero-exit app receipt proves controlled lifecycle completion."""
	receipt_path = tmp_path / "completion.json"
	receipt_path.write_text('{"schema":"bkchem-smoke-1","exit_code":0}', encoding="utf-8")

	macos_app_smoke._validate_smoke_receipt(receipt_path)


#============================================
@pytest.mark.parametrize("payload", ('{}', '{"schema":"bkchem-smoke-1","exit_code":1}'))
def test_smoke_receipt_validator_rejects_non_success_payloads(
		tmp_path: pathlib.Path, payload: str,
		) -> None:
	"""A malformed or nonzero receipt cannot turn an incomplete smoke into success."""
	receipt_path = tmp_path / "completion.json"
	receipt_path.write_text(payload, encoding="utf-8")

	with pytest.raises(RuntimeError, match="Invalid smoke receipt"):
		macos_app_smoke._validate_smoke_receipt(receipt_path)


#============================================
def test_macos_smoke_rejects_missing_receipt_after_process_success(tmp_path: pathlib.Path) -> None:
	"""A zero process status alone is not application lifecycle completion."""
	def successful_process(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Return process success without creating app-owned completion proof."""
		return subprocess.CompletedProcess(command, 0, "", "")

	with pytest.raises(RuntimeError, match="Missing or invalid smoke receipt"):
		macos_app_smoke.run_macos_smoke(
			DIRECT, tmp_path / "BKChem.app", 2.0, tmp_path / "smoke",
			tmp_path, tmp_path, successful_process,
		)


#============================================
def test_macos_smoke_reports_route_and_retains_process_failure(tmp_path: pathlib.Path) -> None:
	"""A route failure is terminal, attributable, and retains launcher output."""
	smoke_root = tmp_path / "native_launch"

	def failed_process(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Return the controlled nonzero native-launch result."""
		return subprocess.CompletedProcess(command, 1, "launcher stdout", "launcher stderr")

	with pytest.raises(RuntimeError, match="native LaunchServices smoke failed") as error:
		macos_app_smoke.run_macos_smoke(
			NATIVE, tmp_path / "BKChem.app", 2.0, smoke_root,
			tmp_path, tmp_path, failed_process,
		)

	assert all(text in str(error.value) for text in ("launcher stdout", "launcher stderr"))
	assert (smoke_root / "stdout.log").read_text(encoding="utf-8") == "launcher stdout"
	assert (smoke_root / "stderr.log").read_text(encoding="utf-8") == "launcher stderr"


#============================================
def test_macos_smoke_rejects_fatal_diagnostic_after_valid_receipt(tmp_path: pathlib.Path) -> None:
	"""A late fatal diagnostic remains terminal after controlled completion."""
	def process_runner(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Create completion evidence plus a retained fatal diagnostic."""
		_write_success_receipt(command)
		return subprocess.CompletedProcess(command, 0, "", "Abort trap: 6")

	with pytest.raises(RuntimeError, match="fatal process diagnostic"):
		macos_app_smoke.run_macos_smoke(
			DIRECT, tmp_path / "BKChem.app", 2.0, tmp_path / "smoke",
			tmp_path, tmp_path, process_runner,
		)


#============================================
def test_macos_smoke_rejects_escaping_artifact_path_before_launch(
		tmp_path: pathlib.Path,
		) -> None:
	"""A traversal cannot place smoke artifacts outside its retained build run."""
	run_root = tmp_path / "run"
	run_root.mkdir()
	process_calls: list[tuple[str, ...]] = []

	def process_runner(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Record an unexpected process request."""
		process_calls.append(command)
		return subprocess.CompletedProcess(command, 0, "", "")

	with pytest.raises(macos_app_smoke.SmokePathError, match="escapes selected build run root"):
		macos_app_smoke.run_macos_smoke(
			DIRECT, tmp_path / "BKChem.app", 2.0,
			run_root / "smoke" / ".." / ".." / "outside",
			run_root, tmp_path, process_runner,
		)

	assert process_calls == []
	assert not (tmp_path / "outside").exists()


#============================================
def test_macos_smoke_suite_requires_separate_receipts_for_both_routes(
		tmp_path: pathlib.Path,
		) -> None:
	"""A direct pass cannot substitute for a native user-launch observation."""
	run_root = tmp_path / "run"
	run_root.mkdir()
	commands: dict[macos_app_smoke.MacSmokeRoute, tuple[str, ...]] = {}

	def runner_for(route: macos_app_smoke.MacSmokeRoute) -> macos_app_smoke.ProcessRunner:
		"""Return one runner that publishes evidence only for its selected route."""
		def process_runner(
				command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
				) -> subprocess.CompletedProcess[str]:
			commands[route] = command
			_write_success_receipt(command)
			return subprocess.CompletedProcess(command, 0, f"{route.label} output", "")

		return process_runner

	macos_app_smoke.run_macos_smoke_suite(
		tmp_path / "BKChem.app", 2.0, run_root, tmp_path,
		{route: runner_for(route) for route in macos_app_smoke.MACOS_SMOKE_ROUTES},
	)

	assert set(commands) == set(macos_app_smoke.MACOS_SMOKE_ROUTES)
	for route in macos_app_smoke.MACOS_SMOKE_ROUTES:
		artifact_root = run_root / route.artifact_directory
		assert (artifact_root / "completion.json").is_file()
		assert (artifact_root / "stdout.log").read_text(encoding="utf-8") == (
			f"{route.label} output"
		)
