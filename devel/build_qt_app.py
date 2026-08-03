#!/usr/bin/env python3

"""Build one isolated Qt-only BKChem.app experiment from the bundle plan."""

# Standard Library
import argparse
import dataclasses
import json
import math
import os
import pathlib
import platform
import plistlib
import re
import shutil
import stat
import struct
import subprocess
import sys
import zipfile
import zlib
from collections.abc import Callable, Mapping
from email.parser import BytesParser
from email.policy import default

# PIP3 modules
from packaging.version import InvalidVersion, Version
from PyInstaller.archive import readers as pyinstaller_archive_readers

# local repo modules
import oasa.version_registry as release_version_registry
import qt_bundle_plan
import version_registry


ICON_POINT_SIZES = (16, 32, 128, 256, 512)
ICON_SCALES = (("", 1), ("@2x", 2))
ICON_SPECS = tuple(
	(
		f"icon_{point_size}x{point_size}{scale_suffix}.png",
		point_size * scale,
	)
	for point_size in ICON_POINT_SIZES
	for scale_suffix, scale in ICON_SCALES
)
VERSION_CHECK_TIMEOUT_SECONDS = 10.0
SMOKE_STARTUP_ALLOWANCE_SECONDS = 10.0
SMOKE_RECEIPT_SCHEMA = "bkchem-smoke-1"
ICONUTIL_SELF_TEST_TIMEOUT_SECONDS = 10.0
ICONUTIL_SELF_TEST_ICON = pathlib.Path(
	"/System/Applications/Chess.app/Contents/Resources/AppIcon.icns"
)
FALLBACK_ICNS_SPECS = (
	("icp4", 16),
	("icp5", 32),
	("icp6", 64),
	("ic07", 128),
	("ic08", 256),
	("ic09", 512),
	("ic10", 1024),
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
QT_ICON_RENDERER = pathlib.Path(__file__).with_name("render_qt_icon_png.py")


@dataclasses.dataclass(frozen=True)
class QtBuildLayout:
	"""Describe one fresh, isolated Qt application build run."""

	run_root: pathlib.Path
	app_dist_dir: pathlib.Path
	work_dir: pathlib.Path
	spec_dir: pathlib.Path
	icon_dir: pathlib.Path
	iconset_dir: pathlib.Path
	icon_path: pathlib.Path
	wheel_dir: pathlib.Path
	metadata_dir: pathlib.Path
	pyinstaller_config_parent: pathlib.Path
	app_path: pathlib.Path


@dataclasses.dataclass(frozen=True)
class IconutilSelfTestResult:
	"""Report whether this host can encode a known-good macOS iconset."""

	usable: bool
	diagnostic: str


@dataclasses.dataclass(frozen=True)
class FrontendMetadataStage:
	"""Describe one validated frontend distribution record staged from a wheel."""

	wheel_path: pathlib.Path
	dist_info_path: pathlib.Path


@dataclasses.dataclass(frozen=True)
class MacAppLayout:
	"""Describe the validated native roots of one self-contained macOS app."""

	app_path: pathlib.Path
	contents_root: pathlib.Path
	resources_root: pathlib.Path
	frameworks_root: pathlib.Path
	executable_path: pathlib.Path
	info_path: pathlib.Path


#============================================
class SmokePathError(RuntimeError):
	"""Report a smoke artifact path that escapes its selected build run root."""


#============================================
@dataclasses.dataclass(frozen=True)
class MacSmokePaths:
	"""Describe validated resolved paths for one frozen-app lifecycle smoke."""

	root: pathlib.Path
	stdout_path: pathlib.Path
	stderr_path: pathlib.Path
	receipt_path: pathlib.Path


#============================================
def resolve_repo_root() -> pathlib.Path:
	"""Return the repository root that owns this build command.

	Returns:
		Resolved repository root path.
	"""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		cwd=pathlib.Path(__file__).resolve().parents[1],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0 or not result.stdout.strip():
		raise RuntimeError("Could not resolve the repository root with git rev-parse")
	repo_root = pathlib.Path(result.stdout.strip()).resolve()
	return repo_root


#============================================
def make_build_layout(repo_root: pathlib.Path, output: pathlib.Path) -> QtBuildLayout:
	"""Describe the fixed paths below one requested build run root.

	Args:
		repo_root: Repository root that owns the allowed ``tmp`` directory.
		output: Explicit run-root path supplied by the caller.

	Returns:
		Immutable isolated output layout.
	"""
	run_root = output.resolve()
	layout = QtBuildLayout(
		run_root=run_root,
		app_dist_dir=run_root / "app",
		work_dir=run_root / "work",
		spec_dir=run_root / "spec",
		icon_dir=run_root / "icon",
		iconset_dir=run_root / "icon" / "BKChem.iconset",
		icon_path=run_root / "icon" / "BKChem.icns",
		wheel_dir=run_root / "wheel",
		metadata_dir=run_root / "metadata",
		pyinstaller_config_parent=run_root / "pyinstaller_config",
		app_path=run_root / "app" / "BKChem.app",
	)
	validate_new_output(layout, repo_root)
	return layout


#============================================
def validate_new_output(layout: QtBuildLayout, repo_root: pathlib.Path) -> None:
	"""Require one new output root below the repository-owned ``tmp`` tree.

	Args:
		layout: Proposed isolated output layout.
		repo_root: Repository root that owns the allowed ``tmp`` directory.

	Raises:
		ValueError: If the requested root is unsafe, outside ``tmp``, or exists.
	"""
	root = repo_root.resolve()
	tmp_root = (root / "tmp").resolve()
	run_root = layout.run_root.resolve()
	if run_root == root or run_root == tmp_root:
		raise ValueError("--output must name a new run root below the repository tmp directory")
	if not run_root.is_relative_to(tmp_root):
		raise ValueError(f"--output must be below {tmp_root}: {run_root}")
	if run_root.exists():
		raise ValueError(f"--output must not already exist: {run_root}")


#============================================
def make_frontend_wheel_args(
		plan: qt_bundle_plan.QtBundlePlan, layout: QtBuildLayout,
		) -> tuple[str, ...]:
	"""Return the isolated local-wheel command for the planned frontend.

	Args:
		plan: Validated Qt-only bundle input plan.
		layout: Fresh isolated output layout.

	Returns:
		One deterministic wheel-build argument tuple with no installation phase.
	"""
	qt_bundle_plan.validate_qt_bundle_plan(plan)
	return (
		sys.executable,
		"-m",
		"build",
		"--wheel",
		"--no-isolation",
		"--outdir",
		str(layout.wheel_dir),
		plan.frontend_project_dir,
	)


#============================================
def make_pyinstaller_args(
		plan: qt_bundle_plan.QtBundlePlan, layout: QtBuildLayout,
		staged_metadata: pathlib.Path,
		) -> tuple[str, ...]:
	"""Build a deterministic PyInstaller command from the accepted Qt plan.

	Args:
		plan: Validated Qt-only bundle input plan.
		layout: Fresh isolated output layout.
		staged_metadata: Complete wheel-produced ``.dist-info`` directory.

	Returns:
		One immutable child-process argument tuple.
	"""
	qt_bundle_plan.validate_qt_bundle_plan(plan)
	arguments = [
		sys.executable,
		"-m",
		"PyInstaller",
		"--name",
		plan.app_name,
		"--onedir",
		"--windowed",
		"--osx-bundle-identifier",
		plan.bundle_identifier,
		"--target-architecture",
		"arm64",
		"--distpath",
		str(layout.app_dist_dir),
		"--workpath",
		str(layout.work_dir),
		"--specpath",
		str(layout.spec_dir),
	]
	for python_path in plan.python_paths:
		arguments.extend(("--paths", python_path))
	for data_file in plan.data_files:
		arguments.extend(("--add-data", f"{data_file.source}:{data_file.destination}"))
	arguments.extend(("--add-data", f"{staged_metadata}:{staged_metadata.name}"))
	for hidden_import in plan.hidden_imports:
		arguments.extend(("--hidden-import", hidden_import))
	for module_name in plan.excluded_modules:
		arguments.extend(("--exclude-module", module_name))
	for package_name in plan.collect_binaries:
		arguments.extend(("--collect-binaries", package_name))
	arguments.extend(("--icon", str(layout.icon_path), plan.entry_script))
	command = tuple(arguments)
	return command


#============================================
def _planned_pyinstaller_config_parent(layout: QtBuildLayout) -> pathlib.Path:
	"""Return the one approved PyInstaller configuration parent for this run.

	Args:
		layout: Fresh isolated build layout.

	Returns:
		Resolved repository-local parent directory supplied to PyInstaller.

	Raises:
		RuntimeError: If a malformed layout would place PyInstaller state outside
			the validated build run root.
	"""
	run_root = layout.run_root.resolve()
	expected = (run_root / "pyinstaller_config").resolve()
	configured = layout.pyinstaller_config_parent.resolve()
	if configured != expected:
		raise RuntimeError(
			"PyInstaller configuration parent must be the planned run-root location: "
			f"{expected}; got {configured}"
		)
	return configured


#============================================
def prepare_pyinstaller_config_parent(layout: QtBuildLayout) -> pathlib.Path:
	"""Create the fresh PyInstaller configuration parent inside one build run.

	Args:
		layout: Fresh isolated build layout whose root has already been created.

	Returns:
		The newly created parent directory passed through ``PYINSTALLER_CONFIG_DIR``.

	Raises:
		RuntimeError: If the run root is unavailable or the planned parent cannot
			be created as a new directory.
	"""
	config_parent = _planned_pyinstaller_config_parent(layout)
	if not layout.run_root.is_dir():
		raise RuntimeError(f"PyInstaller run root is missing: {layout.run_root}")
	try:
		config_parent.mkdir()
	except FileExistsError as error:
		raise RuntimeError(
			"PyInstaller configuration parent must be new for this build run: "
			f"{config_parent}"
		) from error
	except OSError as error:
		raise RuntimeError(
			"Could not create PyInstaller configuration parent: {config_parent}: {error}"
		) from error
	return config_parent


#============================================
def make_pyinstaller_environment(
		layout: QtBuildLayout, inherited_environment: Mapping[str, str] | None = None,
		) -> dict[str, str]:
	"""Return the PyInstaller child environment for one isolated build run.

	Args:
		layout: Fresh isolated build layout with its planned configuration parent.
		inherited_environment: Optional parent environment used by tests or callers.

	Returns:
		A copy of the inherited environment with the one PyInstaller-specific
		configuration location set below the current run root.
	"""
	config_parent = _planned_pyinstaller_config_parent(layout)
	environment = dict(os.environ if inherited_environment is None else inherited_environment)
	environment["PYINSTALLER_CONFIG_DIR"] = str(config_parent)
	return environment


#============================================
def _normalized_distribution_name(name: str) -> str:
	"""Return the wheel filename spelling for one normalized distribution name.

	Args:
		name: Distribution name from the frontend bundle plan.

	Returns:
		Lowercase wheel-safe distribution spelling.
	"""
	parts = []
	separator_pending = False
	for character in name:
		if character.isalnum():
			if separator_pending and parts:
				parts.append("_")
			parts.append(character.lower())
			separator_pending = False
		elif character in "-_.":
			separator_pending = True
		else:
			raise RuntimeError(f"Frontend distribution has an unsupported character: {name!r}")
	result = "".join(parts)
	if not result:
		raise RuntimeError("Frontend distribution normalization produced an empty name")
	return result


#============================================
def _release_profile(value: release_version_registry.ReleaseVersion | str) -> release_version_registry.ReleaseVersion:
	"""Return one typed release profile while retaining narrow source-tool inputs."""
	if isinstance(value, release_version_registry.ReleaseVersion):
		return value
	try:
		return release_version_registry.release_version_profile(value)
	except release_version_registry.ReleaseVersionError as error:
		raise RuntimeError(str(error)) from error


#============================================
def _expected_dist_info_name(
		plan: qt_bundle_plan.QtBundlePlan,
		release: release_version_registry.ReleaseVersion | str,
		) -> str:
	"""Return the one wheel-produced metadata directory expected for this build.

	Args:
		plan: Validated bundle plan naming the frontend distribution.
		release: Typed release identity or its exact source display spelling.

	Returns:
		Expected top-level ``.dist-info`` directory basename.
	"""
	profile = _release_profile(release)
	return (
		f"{_normalized_distribution_name(plan.frontend_distribution)}-"
		f"{profile.distribution}.dist-info"
	)


#============================================
def _canonical_pep440_version(version: str) -> str:
	"""Return the normalized wheel spelling for one canonical repository version.

	Args:
		version: Version text from the root registry or wheel metadata.

	Returns:
		PEP 440 normalized text used by wheel filenames and ``.dist-info`` paths.

	Raises:
		RuntimeError: If the supplied version is not valid PEP 440 version text.
	"""
	if not version:
		raise RuntimeError("Expected frontend metadata version must be nonempty")
	try:
		return str(Version(version))
	except InvalidVersion as error:
		raise RuntimeError(f"Frontend metadata version is not valid PEP 440 text: {version!r}") from error


#============================================
def _matching_frontend_wheels(
		plan: qt_bundle_plan.QtBundlePlan, wheel_dir: pathlib.Path,
		release: release_version_registry.ReleaseVersion | str,
		) -> tuple[pathlib.Path, ...]:
	"""Return the exact locally-built wheel candidates for the planned frontend.

	Args:
		plan: Validated bundle plan naming the frontend distribution.
		wheel_dir: Fresh build-local wheel output directory.
		release: Typed release identity or its exact source display spelling.

	Returns:
		Sorted wheel paths whose filename names the planned distribution and version.

	Raises:
		RuntimeError: If the wheel output directory is unavailable.
	"""
	profile = _release_profile(release)
	if not wheel_dir.is_dir():
		raise RuntimeError(f"Frontend wheel output directory is missing: {wheel_dir}")
	expected_prefix = (
		f"{_normalized_distribution_name(plan.frontend_distribution)}-"
		f"{profile.distribution}-"
	)
	return tuple(sorted(
		path for path in wheel_dir.glob("*.whl") if path.name.startswith(expected_prefix)
	))


#============================================
def _validate_wheel_member_path(member_name: str, wheel_path: pathlib.Path) -> pathlib.PurePosixPath:
	"""Validate one ZIP member name before it can influence staged filesystem paths.

	Args:
		member_name: Raw ZIP member name.
		wheel_path: Archive used in a clear validation failure.

	Returns:
		Safe relative POSIX member path.

	Raises:
		RuntimeError: If the archive member can escape or ambiguously map staging.
	"""
	pure_path = pathlib.PurePosixPath(member_name)
	if (
		not member_name
		or "\\" in member_name
		or pure_path.is_absolute()
		or ".." in pure_path.parts
		or "." in pure_path.parts
	):
		raise RuntimeError(f"Frontend wheel has an unsafe ZIP member path: {member_name!r} in {wheel_path}")
	return pure_path


#============================================
def _metadata_fields(metadata_payload: bytes, wheel_path: pathlib.Path) -> tuple[str, str]:
	"""Read required distribution identity fields from one wheel METADATA payload.

	Args:
		metadata_payload: Raw wheel ``METADATA`` bytes.
		wheel_path: Archive used in any validation failure.

	Returns:
		Distribution name and version exactly declared by the wheel.

	Raises:
		RuntimeError: If the metadata cannot declare one usable identity.
	"""
	try:
		message = BytesParser(policy=default).parsebytes(metadata_payload)
	except (UnicodeDecodeError, ValueError) as error:
		raise RuntimeError(f"Frontend wheel has malformed METADATA: {wheel_path}: {error}") from error
	name = message.get("Name")
	version = message.get("Version")
	if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
		raise RuntimeError(f"Frontend wheel METADATA lacks Name or Version: {wheel_path}")
	return name, version


#============================================
def _is_regular_zip_file(info: zipfile.ZipInfo) -> bool:
	"""Return whether one ZIP member is a regular file suitable for staging.

	Args:
		info: ZIP metadata for one direct wheel member.

	Returns:
		Whether the member is a regular file rather than a directory, link, or
		special filesystem entry.
	"""
	if info.is_dir():
		return False
	if info.create_system == 0:
		# DOS/FAT stores directory and volume-label semantics in the low word.
		dos_attributes = info.external_attr & 0xFFFF
		return not (dos_attributes & (0x10 | 0x08))
	if info.create_system == 3:
		file_type = (info.external_attr >> 16) & 0o170000
		return file_type in (0, 0o100000)
	return False


#============================================
def stage_frontend_metadata(
		plan: qt_bundle_plan.QtBundlePlan, layout: QtBuildLayout,
		release: release_version_registry.ReleaseVersion | str,
		) -> FrontendMetadataStage:
	"""Extract one complete matching wheel metadata tree into the retained run root.

	Args:
		plan: Validated bundle plan naming the frontend distribution and source project.
		layout: Current isolated build layout whose wheel and metadata paths are retained.
		release: Typed release identity or its exact source display spelling.

	Returns:
		Validated wheel and staged metadata directory paths.

	Raises:
		RuntimeError: If wheel selection, ZIP safety, metadata identity, or completeness fails.
	"""
	qt_bundle_plan.validate_qt_bundle_plan(plan)
	profile = _release_profile(release)
	candidates = _matching_frontend_wheels(plan, layout.wheel_dir, profile)
	if not candidates:
		raise RuntimeError(
			"Frontend wheel is missing for the planned distribution and version: "
			f"{plan.frontend_distribution} {profile.distribution} in {layout.wheel_dir}"
		)
	if len(candidates) != 1:
		raise RuntimeError(
			"Frontend wheel selection is ambiguous for the planned distribution and version: "
			f"{', '.join(str(path) for path in candidates)}"
		)
	wheel_path = candidates[0]
	dist_info_name = _expected_dist_info_name(plan, profile)
	required_members = {"METADATA", "WHEEL", "RECORD"}
	try:
		with zipfile.ZipFile(wheel_path) as archive:
			infos = archive.infolist()
			member_paths = [_validate_wheel_member_path(info.filename, wheel_path) for info in infos]
			if len({path.as_posix() for path in member_paths}) != len(member_paths):
				raise RuntimeError(f"Frontend wheel has duplicate ZIP members: {wheel_path}")
			matching_infos = [
				(info, path)
				for info, path in zip(infos, member_paths, strict=True)
				if path.parts and path.parts[0] == dist_info_name
			]
			known_dist_info_roots = {
				path.parts[0]
				for path in member_paths
				if path.parts and path.parts[0].endswith(".dist-info")
			}
			if known_dist_info_roots != {dist_info_name}:
				raise RuntimeError(
					"Frontend wheel must contain exactly one matching .dist-info tree: "
					f"expected {dist_info_name!r}, found {sorted(known_dist_info_roots)!r}"
				)
			direct_infos = {
				path.parts[1]: info
				for info, path in matching_infos
				if len(path.parts) == 2 and path.parts[1] in required_members
			}
			valid_required_members = {
				member_name
				for member_name, info in direct_infos.items()
				if _is_regular_zip_file(info)
			}
			missing_members = required_members - valid_required_members
			if missing_members:
				raise RuntimeError(
					"Frontend wheel metadata is incomplete or has non-regular direct members; missing "
					f"{sorted(missing_members)!r}: {wheel_path}"
				)
			metadata_info = direct_infos["METADATA"]
			metadata_name, metadata_version = _metadata_fields(archive.read(metadata_info), wheel_path)
			if metadata_name != plan.frontend_distribution:
				raise RuntimeError(
					"Frontend wheel METADATA Name does not match the bundle plan: "
					f"{metadata_name!r}; expected {plan.frontend_distribution!r}"
				)
			if metadata_version != profile.distribution:
				raise RuntimeError(
					"Frontend wheel METADATA Version does not match the canonical version: "
					f"{metadata_version!r}; expected normalized {profile.distribution!r}"
				)
			staged_path = layout.metadata_dir / dist_info_name
			if staged_path.exists():
				raise RuntimeError(f"Frontend metadata staging path already exists: {staged_path}")
			for info, path in matching_infos:
				if info.is_dir():
					continue
				if not _is_regular_zip_file(info):
					raise RuntimeError(
						f"Frontend wheel metadata contains a non-regular member: {info.filename!r}"
					)
				relative_path = pathlib.PurePosixPath(*path.parts[1:])
				destination = staged_path.joinpath(*relative_path.parts)
				destination.parent.mkdir(parents=True, exist_ok=True)
				with archive.open(info) as source_file, destination.open("xb") as destination_file:
					shutil.copyfileobj(source_file, destination_file)
	except (OSError, zipfile.BadZipFile) as error:
		raise RuntimeError(f"Could not stage frontend wheel metadata from {wheel_path}: {error}") from error
	if not staged_path.is_dir():
		raise RuntimeError(f"Frontend metadata staging did not produce a directory: {staged_path}")
	return FrontendMetadataStage(wheel_path=wheel_path, dist_info_path=staged_path)


#============================================
def make_smoke_args(
		app_path: pathlib.Path, seconds: float, smoke_root: pathlib.Path,
		) -> tuple[str, ...]:
	"""Return the direct timer-exit command for one built macOS app.

	Args:
		app_path: Expected ``BKChem.app`` location.
		seconds: Positive finite duration before normal Qt event-loop exit.
		smoke_root: Fresh builder-owned directory for app diagnostics and receipt.

	Returns:
		Immutable smoke command tuple.

	Raises:
		ValueError: If the requested timer duration is not positive and finite.
	"""
	if not math.isfinite(seconds) or seconds <= 0.0:
		raise ValueError("--smoke-exit must be a finite positive number of seconds")
	command = (
		str(app_path / "Contents" / "MacOS" / "BKChem"),
		"--smoke-exit", str(seconds),
		"--smoke-receipt", str(smoke_root / "completion.json"),
	)
	return command


#============================================
def resolve_macos_smoke_paths(
		smoke_root: pathlib.Path, build_run_root: pathlib.Path,
		) -> MacSmokePaths:
	"""Resolve and contain every smoke artifact below one selected build run.

	Args:
		smoke_root: Requested fresh directory for this smoke's diagnostics.
		build_run_root: Already selected fresh retained build run root.

	Returns:
		Resolved contained smoke directory and fixed log/receipt paths.

	Raises:
		SmokePathError: If any resolved smoke path escapes the selected run root.
	"""
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
	paths = MacSmokePaths(
		root=candidates["smoke root"],
		stdout_path=candidates["smoke stdout log"],
		stderr_path=candidates["smoke stderr log"],
		receipt_path=candidates["smoke receipt"],
	)
	return paths


#============================================
def _validate_smoke_receipt(receipt_path: pathlib.Path) -> None:
	"""Require one exact successful application lifecycle receipt.

	Args:
		receipt_path: Expected fresh JSON receipt written by the launched app.

	Raises:
		RuntimeError: If the receipt is absent, unreadable, or not the fixed schema.
	"""
	try:
		payload = json.loads(receipt_path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise RuntimeError(f"Missing or invalid smoke receipt: {receipt_path}: {error}") from error
	if payload != {"schema": SMOKE_RECEIPT_SCHEMA, "exit_code": 0}:
		raise RuntimeError(f"Invalid smoke receipt: {receipt_path}: {payload!r}")


#============================================
def _fatal_smoke_diagnostic(stderr_path: pathlib.Path) -> str | None:
	"""Return one retained fatal application diagnostic, when present."""
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
	"""Retain frozen-app output next to its lifecycle receipt."""
	try:
		paths.stdout_path.write_text(result.stdout, encoding="utf-8")
		paths.stderr_path.write_text(result.stderr, encoding="utf-8")
	except OSError as error:
		raise RuntimeError(f"Could not retain macOS smoke output: {error}") from error


#============================================
def run_macos_smoke(
		app_path: pathlib.Path, seconds: float, smoke_root: pathlib.Path,
		build_run_root: pathlib.Path, repo_root: pathlib.Path,
		runner: Callable[[tuple[str, ...], pathlib.Path, float], subprocess.CompletedProcess[str]],
		) -> None:
	"""Run one bounded frozen app and require app-owned completion proof."""
	smoke_paths = resolve_macos_smoke_paths(smoke_root, build_run_root)
	if smoke_paths.root.exists():
		raise RuntimeError(f"macOS smoke root must be fresh: {smoke_paths.root}")
	smoke_paths.root.mkdir(parents=True)
	command = make_smoke_args(app_path, seconds, smoke_paths.root)
	try:
		result = runner(command, repo_root, seconds + SMOKE_STARTUP_ALLOWANCE_SECONDS)
	except subprocess.TimeoutExpired as error:
		raise RuntimeError(
			f"macOS smoke timed out after {seconds + SMOKE_STARTUP_ALLOWANCE_SECONDS:g}s: "
			f"{_format_command(command)}"
		) from error
	_write_smoke_logs(smoke_paths, result)
	if result.returncode != 0:
		raise RuntimeError(
			f"macOS smoke failed ({result.returncode}): {_format_command(command)}\n"
			f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
		)
	_validate_smoke_receipt(smoke_paths.receipt_path)
	fatal_diagnostic = _fatal_smoke_diagnostic(smoke_paths.stderr_path)
	if fatal_diagnostic is not None:
		raise RuntimeError(
			f"macOS smoke recorded fatal application diagnostic {fatal_diagnostic!r}: "
			f"{smoke_paths.stderr_path}"
		)


#============================================
def make_version_args(app_path: pathlib.Path) -> tuple[str, ...]:
	"""Return the frozen application's lightweight version-check command.

	Args:
		app_path: Expected ``BKChem.app`` location.

	Returns:
		Immutable command for the frozen application's public version query.
	"""
	executable = app_path / "Contents" / "MacOS" / "BKChem"
	command = (str(executable), "--version")
	return command


#============================================
def _classify_macos_app_bundle(
		app_path: pathlib.Path, app_name: str,
		) -> MacAppLayout:
	"""Classify one self-contained native macOS application bundle.

	The distributable ``.app`` owns its conventional Resources and Frameworks
	roots.  A parallel PyInstaller one-dir collection is intentionally outside
	this model and cannot repair a malformed application bundle.

	Args:
		app_path: Expected application bundle root.
		app_name: Expected executable basename.

	Returns:
		Validated immutable native app-layout paths.

	Raises:
		RuntimeError: If the supplied path is not the supported macOS app layout.
	"""
	if app_path.suffix != ".app":
		raise RuntimeError(f"Unsupported macOS app bundle name: {app_path}")
	if app_path.is_symlink() or not app_path.is_dir():
		raise RuntimeError(f"Missing application bundle directory: {app_path}")
	contents_root = app_path / "Contents"
	macos_root = contents_root / "MacOS"
	frameworks_root = contents_root / "Frameworks"
	resources_root = contents_root / "Resources"
	for root_path, description in (
		(contents_root, "application Contents directory"),
		(macos_root, "application MacOS directory"),
		(frameworks_root, "application Frameworks directory"),
		(resources_root, "application Resources directory"),
	):
		if root_path.is_symlink() or not root_path.is_dir():
			raise RuntimeError(f"Unsupported or missing {description}: {root_path}")
	executable_path = macos_root / app_name
	if executable_path.is_symlink() or not executable_path.is_file() or not os.access(executable_path, os.X_OK):
		raise RuntimeError(f"Missing or non-executable frozen application: {executable_path}")
	info_path = contents_root / "Info.plist"
	if info_path.is_symlink() or not info_path.is_file():
		raise RuntimeError(f"Missing application Info.plist: {info_path}")
	return MacAppLayout(
		app_path=app_path,
		contents_root=contents_root,
		resources_root=resources_root,
		frameworks_root=frameworks_root,
		executable_path=executable_path,
		info_path=info_path,
	)


#============================================
def _contained_path(
		path: pathlib.Path, contents_root: pathlib.Path, expected_kind: str,
		) -> pathlib.Path:
	"""Return an existing in-bundle file or directory with safe link resolution.

	Args:
		path: Candidate path below one native application root.
		contents_root: Authoritative ``Contents`` root for containment checks.
		expected_kind: Required ``"file"`` or ``"directory"`` capability kind.

	Returns:
		The resolved contained target.

	Raises:
		RuntimeError: If the path is missing, malformed, dangling, or escapes.
	"""
	if expected_kind not in {"file", "directory"}:
		raise ValueError(f"Unsupported application payload kind: {expected_kind!r}")
	try:
		resolved_root = contents_root.resolve(strict=True)
		resolved_path = path.resolve(strict=True)
	except OSError as error:
		raise RuntimeError(f"Missing or dangling required application payload: {path}: {error}") from error
	if not resolved_path.is_relative_to(resolved_root):
		raise RuntimeError(f"Required application payload escapes Contents: {path}")
	mode = resolved_path.stat().st_mode
	if expected_kind == "file" and not stat.S_ISREG(mode):
		raise RuntimeError(f"Missing or corrupt required application file: {path}")
	if expected_kind == "directory" and not stat.S_ISDIR(mode):
		raise RuntimeError(f"Missing or corrupt required application directory: {path}")
	return resolved_path


#============================================
def _require_payload(
		root: pathlib.Path, contents_root: pathlib.Path, relative_path: str, expected_kind: str,
		) -> pathlib.Path:
	"""Require one explicit resource or framework payload below its owned root."""
	pure_path = pathlib.PurePosixPath(relative_path)
	if pure_path.is_absolute() or ".." in pure_path.parts or relative_path in ("", "."):
		raise RuntimeError(f"Unexpected required application payload path: {relative_path!r}")
	return _contained_path(root.joinpath(*pure_path.parts), contents_root, expected_kind)


#============================================
def _require_native_capability(
		owner_root: pathlib.Path, contents_root: pathlib.Path, pattern: str, description: str,
		*, executable: bool = False,
		) -> pathlib.Path:
	"""Require one contained native payload below its declared package root.

	Args:
		owner_root: Package or framework root that owns the capability.
		contents_root: Authoritative ``Contents`` root for containment checks.
		pattern: ABI-tolerant filename pattern searched only below ``owner_root``.
		description: Human-readable capability name used in diagnostics.
		executable: Whether the native payload must have an executable mode bit.

	Returns:
		The matching contained payload path.

	Raises:
		RuntimeError: If the owning root or a suitable payload is unavailable.
	"""
	resolved_owner_root = _contained_path(owner_root, contents_root, "directory")
	for candidate in resolved_owner_root.rglob(pattern):
		try:
			resolved_candidate = _contained_path(candidate, contents_root, "file")
		except RuntimeError:
			continue
		if executable and not os.access(resolved_candidate, os.X_OK):
			continue
		return resolved_candidate
	capability_kind = "executable native payload" if executable else "native payload"
	raise RuntimeError(
		f"Missing required {description} {capability_kind} below declared owner root "
		f"{owner_root}"
	)


#============================================
def _forbidden_frozen_runtime_label(member_name: str) -> str | None:
	"""Return the delivery rule violated by one filesystem or archive member name."""
	lower_name = member_name.replace("\\", "/").lower()
	components = tuple(
		component.replace("-", "_")
		for component in re.split(r"[/.!]+", lower_name)
		if component
	)
	if "addons" in components:
		return "legacy add-on payload"
	if (
		"bkchem_app" in components
		or lower_name.startswith("bkchem/")
		or "/bkchem/" in lower_name
		or "!bkchem." in lower_name
	):
		return "legacy BKChem application"
	if "bkchem_data" in components:
		return "legacy BKChem data"
	if lower_name.endswith(".tcl") or any(
		component in {"tk", "tcl", "imagetk"}
		or component.startswith(("_tk", "_tcl", "libtk", "libtcl"))
		or component.startswith("tcl") and component[3:].isdigit()
		or component.startswith("tk") and component[2:].isdigit()
		or "tkinter" in component
		for component in components
	):
		return "Tk/Tcl runtime"
	return None


#============================================
def _normalized_frozen_member_name(member_name: str) -> str:
	"""Return one safe normalized filesystem or nested-archive member name.

	Every archive level is relative to its owning container. Rejecting absolute
	or parent-traversing names makes a copied checkout or escaped archive member
	visible at the artifact boundary instead of trusting PyInstaller's layout.
	"""
	levels = member_name.replace("\\", "/").split("!")
	normalized_levels: list[str] = []
	for level in levels:
		path = pathlib.PurePosixPath(level)
		if level in {"", "."} or path.is_absolute() or any(
				part in {"", ".", ".."} for part in path.parts
				):
			raise RuntimeError(
			"Qt-only frozen bundle contains an unsafe or checkout-leaking member path: "
			f"{member_name}"
		)
		normalized_levels.append(path.as_posix())
	return "!".join(normalized_levels)


#============================================
def _reject_forbidden_frozen_runtime_members(
		member_names: tuple[str, ...], source_label: str,
		) -> None:
	"""Reject one artifact source that contains a forbidden delivery payload."""
	for member_name in sorted(member_names):
		normalized_name = _normalized_frozen_member_name(member_name)
		label = _forbidden_frozen_runtime_label(normalized_name)
		if label is not None:
			raise RuntimeError(
				f"Qt-only frozen bundle contains forbidden {label} in {source_label}: {normalized_name}"
			)


#============================================
def _reject_bundle_filesystem_escapes(contents_root: pathlib.Path) -> None:
	"""Require every filesystem payload link to resolve inside ``Contents``."""
	resolved_contents = contents_root.resolve(strict=True)
	for path in contents_root.rglob("*"):
		try:
			resolved_path = path.resolve(strict=True)
		except OSError as error:
			raise RuntimeError(f"dangling frozen bundle payload: {path}: {error}") from error
		if not resolved_path.is_relative_to(resolved_contents):
			raise RuntimeError(
				"Required application payload escapes Contents (checkout-source leakage): "
				f"{path} -> {resolved_path}"
			)


#============================================
def _bundle_filesystem_member_names(contents_root: pathlib.Path) -> tuple[str, ...]:
	"""Return every direct bundle payload path for Qt-only delivery inspection."""
	return tuple(
		path.relative_to(contents_root).as_posix()
		for path in contents_root.rglob("*")
	)


#============================================
def _walk_pyinstaller_archive_members(archive: object, prefix: str) -> tuple[str, ...]:
	"""Return archive members and recursively inspect embedded PyInstaller archives."""
	toc = getattr(archive, "toc", None)
	if not isinstance(toc, dict):
		raise RuntimeError("PyInstaller archive has no readable member table")
	member_names: list[str] = []
	for member_name in sorted(toc):
		qualified_name = f"{prefix}!{member_name}" if prefix else member_name
		member_names.append(qualified_name)
		if not isinstance(archive, pyinstaller_archive_readers.CArchiveReader):
			continue
		try:
			embedded_archive = archive.open_embedded_archive(member_name)
		except pyinstaller_archive_readers.NotAnArchiveError:
			continue
		except pyinstaller_archive_readers.ArchiveReadError as error:
			raise RuntimeError(
				f"Could not inspect embedded PyInstaller archive {qualified_name}: {error}"
			) from error
		member_names.extend(_walk_pyinstaller_archive_members(embedded_archive, qualified_name))
	return tuple(member_names)


#============================================
def _pyinstaller_archive_member_names(executable_path: pathlib.Path) -> tuple[str, ...]:
	"""Return every member stored in a frozen executable and its embedded archives."""
	try:
		archive = pyinstaller_archive_readers.CArchiveReader(executable_path)
	except (OSError, pyinstaller_archive_readers.ArchiveReadError) as error:
		raise RuntimeError(f"Could not inspect PyInstaller executable archive: {executable_path}: {error}") from error
	return _walk_pyinstaller_archive_members(archive, "")


#============================================
def _inspect_bundle_payloads(
		plan: qt_bundle_plan.QtBundlePlan, layout: MacAppLayout,
		release: release_version_registry.ReleaseVersion,
		archive_member_reader: Callable[[pathlib.Path], tuple[str, ...]],
		) -> None:
	"""Validate the frontend, backend, metadata, Python, Qt, and native capabilities."""
	_reject_bundle_filesystem_escapes(layout.contents_root)
	_reject_forbidden_frozen_runtime_members(
		_bundle_filesystem_member_names(layout.contents_root), "bundle filesystem payload",
	)
	_reject_forbidden_frozen_runtime_members(
		archive_member_reader(layout.executable_path), "PyInstaller archive member",
	)
	for relative_path in (
		"bkchem_qt/resources/menus.yaml",
		"bkchem_qt/resources/modes.yaml",
		"bkchem_qt/resources/themes/light.yaml",
		"bkchem_qt/resources/themes/dark.yaml",
		"oasa_data/__init__.py",
		"oasa_data/isotopes.json",
		"oasa_data/sugar_codes.yaml",
		"oasa_data/biomolecule_smiles.yaml",
	):
		_require_payload(layout.resources_root, layout.contents_root, relative_path, "file")
	dist_info_name = _expected_dist_info_name(plan, release)
	dist_info_root = _require_payload(
		layout.resources_root, layout.contents_root, dist_info_name, "directory"
	)
	for member_name in ("METADATA", "WHEEL", "RECORD"):
		_require_payload(dist_info_root, layout.contents_root, member_name, "file")
	metadata_path = dist_info_root / "METADATA"
	try:
		metadata_name, metadata_version = _metadata_fields(metadata_path.read_bytes(), metadata_path)
	except OSError as error:
		raise RuntimeError(f"Could not read staged frontend METADATA: {metadata_path}: {error}") from error
	if _normalized_distribution_name(metadata_name) != _normalized_distribution_name(plan.frontend_distribution):
		raise RuntimeError(
			"Staged frontend METADATA Name does not match the planned distribution: "
			f"{metadata_name!r}; expected {plan.frontend_distribution!r}"
		)
	if metadata_version != release.distribution:
		raise RuntimeError(
			"Staged frontend METADATA Version does not match the normalized distribution: "
			f"{metadata_version!r}; expected {release.distribution!r}"
		)
	python_framework = _require_payload(
		layout.frameworks_root, layout.contents_root, "Python.framework", "directory"
	)
	_require_native_capability(
		python_framework, layout.contents_root, "Python", "Python runtime", executable=True,
	)
	_require_native_capability(
		layout.frameworks_root / "PySide6", layout.contents_root, "QtCore*.so", "PySide6 QtCore",
	)
	_require_payload(
		layout.frameworks_root, layout.contents_root,
		"PySide6/Qt/plugins/platforms/libqcocoa.dylib", "file",
	)
	for owner_name, pattern, description in (
		("rdkit", "rdBase*.so", "rdkit"),
		("cairo", "_cairo*.so", "cairo"),
		("rustworkx", "rustworkx*.so", "rustworkx"),
	):
		_require_native_capability(
			layout.frameworks_root / owner_name, layout.contents_root, pattern, description,
		)


#============================================
def _run_version_command(
		command: tuple[str, ...], cwd: pathlib.Path, timeout_seconds: float,
		) -> subprocess.CompletedProcess[str]:
	"""Run the bounded public version check for one frozen application.

	Args:
		command: Frozen application's public version command.
		cwd: Existing application bundle directory.
		timeout_seconds: Positive maximum duration for the command.

	Returns:
		Completed child-process result with captured text streams.
	"""
	result = subprocess.run(
		command, cwd=cwd, capture_output=True, text=True, check=False,
		timeout=timeout_seconds,
	)
	return result


#============================================
def patch_built_app_metadata(
		plan: qt_bundle_plan.QtBundlePlan, app_path: pathlib.Path,
		release: release_version_registry.ReleaseVersion, bundle_build: str,
		) -> None:
	"""Set the planned identity and canonical version in one built app plist.

	Args:
		plan: Validated immutable Qt bundle plan.
		app_path: Completed ``BKChem.app`` path produced by PyInstaller.
		release: Typed authoritative release identity.
		bundle_build: Explicit validated numeric macOS build identity.

	Raises:
		RuntimeError: If the generated plist is missing or cannot be parsed.
	"""
	try:
		validated_build = release_version_registry.validate_macos_bundle_build(bundle_build)
	except release_version_registry.ReleaseVersionError as error:
		raise RuntimeError(str(error)) from error
	if app_path.name != plan.bundle_name:
		raise RuntimeError(f"Unexpected macOS app bundle path: {app_path}")
	layout = _classify_macos_app_bundle(app_path, plan.app_name)
	info_path = layout.info_path
	try:
		with info_path.open("rb") as info_file:
			info = plistlib.load(info_file)
	except (OSError, plistlib.InvalidFileException) as error:
		raise RuntimeError(f"Corrupt application Info.plist for metadata patch: {info_path}: {error}") from error
	info["CFBundleIdentifier"] = plan.bundle_identifier
	info["BKChemReleaseVersion"] = release.display
	info["CFBundleShortVersionString"] = release.macos_short_version
	info["CFBundleVersion"] = validated_build
	try:
		with info_path.open("wb") as info_file:
			plistlib.dump(info, info_file, sort_keys=True)
	except OSError as error:
		raise RuntimeError(f"Could not write application Info.plist metadata: {info_path}: {error}") from error


#============================================
def make_adhoc_codesign_args(app_path: pathlib.Path) -> tuple[str, ...]:
	"""Return the local-delivery signature command for one complete app bundle."""
	return ("codesign", "--force", "--deep", "--sign", "-", str(app_path))


#============================================
def make_codesign_verify_args(app_path: pathlib.Path) -> tuple[str, ...]:
	"""Return the strict recursive signature-verification command for one bundle."""
	return ("codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app_path))


#============================================
def finalize_built_app_signature(app_path: pathlib.Path, repo_root: pathlib.Path) -> None:
	"""Ad-hoc sign and verify final metadata after PyInstaller assembles the app.

	PyInstaller signs its initial bundle. The builder then writes authoritative
	version metadata, which changes the signed Info.plist. Finalization makes the
	final metadata and the local-delivery signature one build stage.
	"""
	if shutil.which("codesign") is None:
		raise RuntimeError("codesign is required to finalize a macOS application bundle")
	_run_checked(make_adhoc_codesign_args(app_path), repo_root)
	_run_checked(make_codesign_verify_args(app_path), repo_root)


#============================================
def inspect_built_app(
		plan: qt_bundle_plan.QtBundlePlan, app_path: pathlib.Path,
		release: release_version_registry.ReleaseVersion, bundle_build: str,
	version_runner: Callable[
		[tuple[str, ...], pathlib.Path, float], subprocess.CompletedProcess[str]
		] = _run_version_command,
	archive_member_reader: Callable[[pathlib.Path], tuple[str, ...]] = _pyinstaller_archive_member_names,
		) -> None:
	"""Validate a completed BKChem application before its smoke launch.

	Args:
		plan: Validated immutable Qt bundle plan.
		app_path: Expected completed ``BKChem.app`` path.
		release: Typed authoritative release identity.
		bundle_build: Explicit validated numeric macOS build identity.
		version_runner: Bounded command runner used for the public version query.

	Raises:
		RuntimeError: If bundle identity, required payload, or frozen version fails.
	"""
	qt_bundle_plan.validate_qt_bundle_plan(plan)
	try:
		validated_build = release_version_registry.validate_macos_bundle_build(bundle_build)
	except release_version_registry.ReleaseVersionError as error:
		raise RuntimeError(str(error)) from error
	if app_path.name != plan.bundle_name:
		raise RuntimeError(f"Unexpected macOS app bundle path: {app_path}")
	layout = _classify_macos_app_bundle(app_path, plan.app_name)
	info_path = layout.info_path
	try:
		with info_path.open("rb") as info_file:
			info = plistlib.load(info_file)
	except (OSError, plistlib.InvalidFileException) as error:
		raise RuntimeError(f"Corrupt application Info.plist: {info_path}: {error}") from error
	if info.get("CFBundleIdentifier") != plan.bundle_identifier:
		raise RuntimeError(
			"Unexpected application bundle identifier: "
			f"{info.get('CFBundleIdentifier')!r}; expected {plan.bundle_identifier!r}"
		)
	for version_key, expected_value in (
		("BKChemReleaseVersion", release.display),
		("CFBundleShortVersionString", release.macos_short_version),
		("CFBundleVersion", validated_build),
	):
		if info.get(version_key) != expected_value:
			raise RuntimeError(
				f"Unexpected {version_key}: {info.get(version_key)!r}; "
				f"expected {expected_value!r}"
			)
	_inspect_bundle_payloads(plan, layout, release, archive_member_reader)
	command = make_version_args(app_path)
	try:
		result = version_runner(command, app_path, VERSION_CHECK_TIMEOUT_SECONDS)
	except subprocess.TimeoutExpired as error:
		raise RuntimeError(
			f"Frozen version check timed out after {VERSION_CHECK_TIMEOUT_SECONDS:g}s: "
			f"{_format_command(command)}"
		) from error
	if result.returncode != 0:
		raise RuntimeError(
			f"Frozen version check failed ({result.returncode}): {_format_command(command)}\n"
			f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
		)
	expected_output = f"BKChem-Qt {release.display}"
	if result.stdout.strip() != expected_output:
		raise RuntimeError(
			f"Unexpected frozen version output: {result.stdout.strip()!r}; "
			f"expected {expected_output!r}"
		)


#============================================
def run_post_build_checks(
		plan: qt_bundle_plan.QtBundlePlan, app_path: pathlib.Path,
		release: release_version_registry.ReleaseVersion, bundle_build: str,
		smoke_seconds: float, smoke_root: pathlib.Path, build_run_root: pathlib.Path,
		repo_root: pathlib.Path,
		smoke_runner: Callable[
			[tuple[str, ...], pathlib.Path, float], subprocess.CompletedProcess[str]
			] | None = None,
		) -> None:
	"""Inspect a built application, then retain one bounded lifecycle smoke.

	Args:
		plan: Validated immutable Qt bundle plan.
		app_path: Expected completed ``BKChem.app`` path.
		release: Typed authoritative release identity.
		bundle_build: Explicit validated numeric macOS build identity.
		smoke_seconds: Positive normal event-loop smoke duration.
		smoke_root: Fresh builder-owned directory for smoke logs and completion.
		build_run_root: Selected fresh retained root that owns smoke artifacts.
		repo_root: Working directory for the smoke child process.
		smoke_runner: Optional injected bounded executable runner for focused tests.
	"""
	patch_built_app_metadata(plan, app_path, release, bundle_build)
	finalize_built_app_signature(app_path, repo_root)
	inspect_built_app(plan, app_path, release, bundle_build)
	runner = smoke_runner or _run_macos_smoke_command
	run_macos_smoke(app_path, smoke_seconds, smoke_root, build_run_root, repo_root, runner)


#============================================
def make_icon_commands(plan: qt_bundle_plan.QtBundlePlan, layout: QtBuildLayout) -> tuple[tuple[str, ...], ...]:
	"""Return deterministic commands that produce the isolated application icon.

	Args:
		plan: Validated Qt-only bundle input plan.
		layout: Fresh isolated output layout.

	Returns:
		Icon renderer and iconutil command tuples.
	"""
	commands: list[tuple[str, ...]] = []
	for filename, size in ICON_SPECS:
		output_path = layout.iconset_dir / filename
		command = (
			"rsvg-convert", "-w", str(size), "-h", str(size), plan.icon_source,
			"-o", str(output_path),
		)
		commands.append(command)
	iconutil_command = (
		"iconutil", "-c", "icns", str(layout.iconset_dir), "-o", str(layout.icon_path),
	)
	commands.append(iconutil_command)
	result = tuple(commands)
	return result


#============================================
def _iconutil_self_test(
		layout: QtBuildLayout, repo_root: pathlib.Path,
		system_icon: pathlib.Path = ICONUTIL_SELF_TEST_ICON,
		) -> IconutilSelfTestResult:
	"""Probe the local iconutil encoder with a system-owned valid icon.

	Args:
		layout: Fresh build layout whose icon directory receives retained probe output.
		repo_root: Working directory for the bounded macOS tool calls.
		system_icon: Known macOS ICNS source used only to test this host toolchain.

	Returns:
		Explicit encoder capability result and a human-visible diagnostic.
	"""
	if shutil.which("iconutil") is None:
		return IconutilSelfTestResult(False, "iconutil self-test unavailable: iconutil is not on PATH")
	if not system_icon.is_file():
		return IconutilSelfTestResult(
			False, f"iconutil self-test unavailable: system icon is missing: {system_icon}"
		)
	probe_iconset = layout.icon_dir / "iconutil-self-test.iconset"
	probe_icns = layout.icon_dir / "iconutil-self-test.icns"
	decode_command = (
		"iconutil", "-c", "iconset", str(system_icon), "-o", str(probe_iconset),
	)
	decode = _run_iconutil_self_test_command(decode_command, repo_root, "decoding system icon")
	if isinstance(decode, IconutilSelfTestResult):
		return decode
	if decode.returncode != 0:
		detail = decode.stderr.strip() or decode.stdout.strip() or "no diagnostic output"
		return IconutilSelfTestResult(
			False, f"iconutil self-test failed while decoding system icon: {detail}"
		)
	encode_command = (
		"iconutil", "-c", "icns", str(probe_iconset), "-o", str(probe_icns),
	)
	encode = _run_iconutil_self_test_command(
		encode_command, repo_root, "encoding valid system iconset"
	)
	if isinstance(encode, IconutilSelfTestResult):
		return encode
	if encode.returncode != 0:
		detail = encode.stderr.strip() or encode.stdout.strip() or "no diagnostic output"
		return IconutilSelfTestResult(
			False, f"iconutil self-test failed while encoding valid system iconset: {detail}"
		)
	if not probe_icns.is_file():
		return IconutilSelfTestResult(
			False, "iconutil self-test failed: encoder returned success without an ICNS output"
		)
	return IconutilSelfTestResult(True, "iconutil self-test passed with the system Chess icon")


#============================================
def _run_iconutil_self_test_command(
		command: tuple[str, ...], repo_root: pathlib.Path, stage: str,
		) -> subprocess.CompletedProcess[str] | IconutilSelfTestResult:
	"""Run one terminal host-tool probe command with its defined timeout.

	Args:
		command: One iconutil probe command.
		repo_root: Working directory for the host-tool command.
		stage: Human-visible description of the probe direction.

	Returns:
		Completed process on execution, or a structured unavailable/timeout result.
	"""
	try:
		result = subprocess.run(
			command, cwd=repo_root, capture_output=True, text=True, check=False,
			timeout=ICONUTIL_SELF_TEST_TIMEOUT_SECONDS,
		)
	except subprocess.TimeoutExpired:
		return IconutilSelfTestResult(
			False,
			f"iconutil self-test timed out while {stage} after "
			f"{ICONUTIL_SELF_TEST_TIMEOUT_SECONDS:g}s",
		)
	except OSError as error:
		return IconutilSelfTestResult(
			False, f"iconutil self-test unavailable while {stage}: {error}"
		)
	return result


#============================================
def _png_dimensions(payload: bytes, source: pathlib.Path) -> tuple[int, int]:
	"""Validate one PNG payload and return its IHDR dimensions.

	Args:
		payload: Raw PNG bytes rendered by the controlled Qt subprocess.
		source: Source path included in any clear validation error.

	Returns:
		Width and height from the PNG IHDR chunk.

	Raises:
		RuntimeError: If the renderer output is not one complete RGBA PNG file.
	"""
	if not payload.startswith(PNG_SIGNATURE):
		raise RuntimeError(f"Qt icon renderer did not produce a PNG payload: {source}")
	offset = len(PNG_SIGNATURE)
	width = 0
	height = 0
	saw_idat = False
	saw_iend = False
	while offset < len(payload):
		if len(payload) - offset < 12:
			raise RuntimeError(f"Qt icon renderer PNG has a truncated chunk: {source}")
		length = struct.unpack(">I", payload[offset:offset + 4])[0]
		chunk_type = payload[offset + 4:offset + 8]
		chunk_end = offset + 12 + length
		if chunk_end > len(payload):
			raise RuntimeError(f"Qt icon renderer PNG has a truncated chunk payload: {source}")
		if not all(
			(ord("A") <= character <= ord("Z")) or (ord("a") <= character <= ord("z"))
			for character in chunk_type
		):
			raise RuntimeError(f"Qt icon renderer PNG has an invalid chunk type: {source}")
		chunk_data = payload[offset + 8:offset + 8 + length]
		expected_crc = struct.unpack(">I", payload[offset + 8 + length:chunk_end])[0]
		actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xffffffff
		if actual_crc != expected_crc:
			raise RuntimeError(f"Qt icon renderer PNG has an invalid chunk CRC: {source}")
		if offset == len(PNG_SIGNATURE):
			if chunk_type != b"IHDR" or length != 13:
				raise RuntimeError(f"Qt icon renderer PNG lacks a valid IHDR chunk: {source}")
			width, height, bit_depth, color_type, compression, filter_method, interlace = (
				struct.unpack(">IIBBBBB", chunk_data)
			)
			if width == 0 or height == 0:
				raise RuntimeError(f"Qt icon renderer PNG has zero dimensions: {source}")
			if bit_depth != 8 or color_type != 6:
				raise RuntimeError(f"Qt icon renderer PNG is not 8-bit RGBA: {source}")
			if compression != 0 or filter_method != 0 or interlace not in (0, 1):
				raise RuntimeError(f"Qt icon renderer PNG has unsupported IHDR settings: {source}")
		elif chunk_type == b"IHDR":
			raise RuntimeError(f"Qt icon renderer PNG has multiple IHDR chunks: {source}")
		elif chunk_type == b"IDAT":
			# The fallback renderer always emits compressed scanline data.  Empty
			# IDAT chunks add no representation data and are outside this narrow
			# controlled RGBA subset.
			if length == 0:
				raise RuntimeError(f"Qt icon renderer PNG has an empty IDAT chunk: {source}")
			saw_idat = True
		elif chunk_type == b"IEND":
			if length != 0 or not saw_idat:
				raise RuntimeError(f"Qt icon renderer PNG has an invalid IEND chunk: {source}")
			if chunk_end != len(payload):
				raise RuntimeError(f"Qt icon renderer PNG has data after IEND: {source}")
			saw_iend = True
			break
		elif saw_idat:
			# PNG permits one contiguous IDAT sequence only.  The controlled
			# fallback needs no post-IDAT ancillary chunks, so terminal IEND is
			# the sole permitted non-IDAT chunk once compressed image data starts.
			raise RuntimeError(f"Qt icon renderer PNG has a nonconsecutive IDAT sequence: {source}")
		elif chunk_type[0] & 0x20 == 0:
			raise RuntimeError(f"Qt icon renderer PNG has an unknown critical chunk: {source}")
		offset = chunk_end
	if not saw_iend:
		raise RuntimeError(f"Qt icon renderer PNG lacks a terminal IEND chunk: {source}")
	return width, height


#============================================
def write_multiresolution_icns(
		png_paths: tuple[tuple[str, int, pathlib.Path], ...], output: pathlib.Path,
		) -> None:
	"""Frame validated PNG payloads as one deterministic multiresolution ICNS.

	Args:
		png_paths: Ordered ICNS chunk types, required square sizes, and PNG sources.
		output: ICNS destination below the current fresh build layout.

	Raises:
		RuntimeError: If required chunk order, PNG identity, or dimensions are invalid.
	"""
	expected = tuple((chunk_type, size) for chunk_type, size in FALLBACK_ICNS_SPECS)
	provided = tuple((chunk_type, size) for chunk_type, size, _path in png_paths)
	if provided != expected:
		raise RuntimeError("Fallback ICNS requires the ordered seven standard PNG chunk sizes")
	chunks: list[bytes] = []
	for chunk_type, expected_size, path in png_paths:
		payload = path.read_bytes()
		width, height = _png_dimensions(payload, path)
		if (width, height) != (expected_size, expected_size):
			raise RuntimeError(
				f"Qt icon renderer produced {width}x{height}, expected "
				f"{expected_size}x{expected_size}: {path}"
			)
		chunk_size = len(payload) + 8
		chunks.append(chunk_type.encode("ascii") + struct.pack(">I", chunk_size) + payload)
	body = b"".join(chunks)
	data = b"icns" + struct.pack(">I", len(body) + 8) + body
	output.write_bytes(data)


#============================================
def _fallback_icon_render_commands(
		plan: qt_bundle_plan.QtBundlePlan, layout: QtBuildLayout,
		) -> tuple[tuple[str, ...], ...]:
	"""Return controlled subprocess calls for the seven fallback PNG sources.

	Args:
		plan: Validated Qt-only bundle input plan.
		layout: Fresh output layout for rendered PNGs.

	Returns:
		One Qt renderer command per distinct ICNS bitmap size.
	"""
	commands = []
	for _chunk_type, size in FALLBACK_ICNS_SPECS:
		output_path = layout.icon_dir / f"fallback_icon_{size}.png"
		command = (
			sys.executable, str(QT_ICON_RENDERER), "--source", plan.icon_source,
			"--size", str(size), "--output", str(output_path),
		)
		commands.append(command)
	result = tuple(commands)
	return result


#============================================
def _format_command(command: tuple[str, ...]) -> str:
	"""Render one argument tuple for human inspection.

	Args:
		command: Child-process arguments to render.

	Returns:
		Space-delimited diagnostic command text.
	"""
	text = " ".join(command)
	return text


#============================================
def _require_macos_build_tools() -> None:
	"""Require the platform and programs used by a real macOS app experiment."""
	if sys.platform != "darwin":
		raise RuntimeError("Qt app builds run only on macOS arm64")
	if platform.machine() != "arm64":
		raise RuntimeError("Qt app builds require an arm64 Python environment")
	probe = subprocess.run(
		[sys.executable, "-c", "import PyInstaller"], capture_output=True, text=True, check=False,
	)
	if probe.returncode != 0:
		raise RuntimeError("PyInstaller is required for a real Qt app build")
	build_probe = subprocess.run(
		[sys.executable, "-c", "import build"], capture_output=True, text=True, check=False,
	)
	if build_probe.returncode != 0:
		raise RuntimeError("The Python build package is required for frontend metadata staging")
	if not QT_ICON_RENDERER.is_file():
		raise RuntimeError(f"Missing controlled Qt icon renderer: {QT_ICON_RENDERER}")
	if shutil.which("codesign") is None:
		raise RuntimeError("codesign is required for a real Qt app build")


#============================================
def _run_checked(
		command: tuple[str, ...], cwd: pathlib.Path, *, env: Mapping[str, str] | None = None,
		) -> None:
	"""Run one child command and retain its failure output in the exception.

	Args:
		command: Child-process command to execute.
		cwd: Repository-root working directory.
		env: Optional child-only environment for one controlled invocation.

	Raises:
		RuntimeError: If the child process fails.
	"""
	result = subprocess.run(
		command, cwd=cwd, env=env, capture_output=True, text=True, check=False,
	)
	if result.returncode != 0:
		message = f"Command failed ({result.returncode}): {_format_command(command)}"
		if result.stdout:
			message += f"\nstdout:\n{result.stdout}"
		if result.stderr:
			message += f"\nstderr:\n{result.stderr}"
		raise RuntimeError(message)


#============================================
def _run_macos_smoke_command(
		command: tuple[str, ...], cwd: pathlib.Path, timeout_seconds: float,
		) -> subprocess.CompletedProcess[str]:
	"""Run the frozen executable directly with an offscreen Qt platform."""
	environment = dict(os.environ)
	environment["QT_QPA_PLATFORM"] = "offscreen"
	return subprocess.run(
		command, cwd=cwd, env=environment, capture_output=True, text=True, check=False,
		timeout=timeout_seconds,
	)


#============================================
def _create_icon(plan: qt_bundle_plan.QtBundlePlan, layout: QtBuildLayout, repo_root: pathlib.Path) -> None:
	"""Render the planned SVG through a self-tested host-adaptive encoder.

	Args:
		plan: Validated Qt-only bundle input plan.
		layout: Fresh output layout whose root already exists.
		repo_root: Working directory for tool execution.
	"""
	layout.icon_dir.mkdir(parents=True)
	self_test = _iconutil_self_test(layout, repo_root)
	if self_test.usable:
		if shutil.which("rsvg-convert") is None:
			raise RuntimeError(
				"iconutil self-test passed, but standard iconset renderer is unavailable: rsvg-convert"
			)
		print(f"Icon encoder route: standard iconutil ({self_test.diagnostic})")
		layout.iconset_dir.mkdir(parents=True)
		for command in make_icon_commands(plan, layout):
			_run_checked(command, repo_root)
		return
	print(f"Icon encoder route: Qt PNG-chunk fallback ({self_test.diagnostic})")
	for command in _fallback_icon_render_commands(plan, layout):
		_run_checked(command, repo_root)
	png_paths = tuple(
		(
			chunk_type,
			size,
			layout.icon_dir / f"fallback_icon_{size}.png",
		)
		for chunk_type, size in FALLBACK_ICNS_SPECS
	)
	write_multiresolution_icns(png_paths, layout.icon_path)


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse the isolated Qt application build command arguments.

	Returns:
		Parsed command-line arguments.
	"""
	parser = argparse.ArgumentParser(description="Build one isolated Qt-only BKChem.app experiment.")
	parser.add_argument(
		"--output", type=pathlib.Path, required=True,
		help="New repository-local tmp run root for this one build experiment.",
	)
	parser.add_argument("--dry-run", action="store_true", help="Print commands without writing or running.")
	parser.add_argument(
		"--bundle-build",
		default=None,
		help=(
			"Explicit numeric macOS CFBundleVersion for a real build, with one to three "
			"dotted components (for example 26.2.1)."
		),
	)
	parser.add_argument(
		"--smoke-exit", type=float, default=2.0,
		help="Seconds for normal Qt timer-exit smoke after a future successful build.",
	)
	args = parser.parse_args()
	if not math.isfinite(args.smoke_exit) or args.smoke_exit <= 0.0:
		parser.error("--smoke-exit must be a finite positive number of seconds")
	if args.bundle_build is not None:
		try:
			release_version_registry.validate_macos_bundle_build(args.bundle_build)
		except release_version_registry.ReleaseVersionError as error:
			parser.error(str(error))
	return args


#============================================
def main() -> None:
	"""Print or run exactly one isolated Qt-only application build experiment."""
	args = parse_args()
	repo_root = resolve_repo_root()
	plan = qt_bundle_plan.make_qt_bundle_plan(repo_root)
	layout = make_build_layout(repo_root, args.output)
	expected_version = version_registry.read_version_file(repo_root / "VERSION")
	try:
		release = release_version_registry.release_version_profile(expected_version)
	except release_version_registry.ReleaseVersionError as error:
		raise RuntimeError(f"Root VERSION is outside the Qt bundle CalVer profile: {error}") from error
	wheel_args = make_frontend_wheel_args(plan, layout)
	planned_metadata = layout.metadata_dir / _expected_dist_info_name(plan, release)
	planned_pyinstaller_args = make_pyinstaller_args(plan, layout, planned_metadata)
	planned_config_parent = _planned_pyinstaller_config_parent(layout)
	smoke_args = make_smoke_args(layout.app_path, args.smoke_exit, layout.run_root / "smoke")
	icon_commands = make_icon_commands(plan, layout)
	print(f"Qt bundle plan: {plan.app_name} via {plan.entry_module}")
	print(f"Run root: {layout.run_root}")
	print(f"Release display: {release.display}")
	print(f"Distribution version: {release.distribution}")
	print(f"macOS short version: {release.macos_short_version}")
	if args.bundle_build is None:
		print("Real build requirement: provide --bundle-build with a numeric macOS build identity")
	else:
		print(f"macOS bundle build: {args.bundle_build}")
	for command in icon_commands:
		print(f"Icon command: {_format_command(command)}")
	print("Icon encoder selection: real builds self-test iconutil before choosing a route")
	print(f"Frontend wheel command: {_format_command(wheel_args)}")
	print(f"Frontend metadata stage: {planned_metadata}")
	print(f"PyInstaller config parent: {planned_config_parent}")
	print(f"Planned PyInstaller command: {_format_command(planned_pyinstaller_args)}")
	print(f"Future smoke command: {_format_command(smoke_args)}")
	if args.dry_run:
		return
	if args.bundle_build is None:
		raise RuntimeError("Real Qt bundle builds require --bundle-build with a numeric macOS build identity")
	_require_macos_build_tools()
	layout.run_root.mkdir(parents=True)
	prepare_pyinstaller_config_parent(layout)
	_create_icon(plan, layout, repo_root)
	layout.wheel_dir.mkdir()
	_run_checked(wheel_args, repo_root)
	metadata_stage = stage_frontend_metadata(plan, layout, release)
	pyinstaller_args = make_pyinstaller_args(plan, layout, metadata_stage.dist_info_path)
	print(f"PyInstaller command: {_format_command(pyinstaller_args)}")
	pyinstaller_environment = make_pyinstaller_environment(layout)
	_run_checked(pyinstaller_args, repo_root, env=pyinstaller_environment)
	run_post_build_checks(
		plan, layout.app_path, release, args.bundle_build, args.smoke_exit,
		layout.run_root / "smoke", layout.run_root, repo_root,
	)


#============================================

if __name__ == "__main__":
	main()
