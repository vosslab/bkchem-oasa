"""Focused pure tests for the isolated Qt-only PyInstaller command builder."""

# Standard Library
import dataclasses
import importlib.metadata
import pathlib
import plistlib
import struct
import subprocess
import sys
import zipfile
import zlib

# PIP3 modules
import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "devel"))

# local repo modules
import build_qt_app
import qt_bundle_plan


def _release(display: str) -> object:
	"""Return the typed release identity used by synthetic bundle assertions."""
	return build_qt_app.release_version_registry.release_version_profile(display)


def _inspect(
		plan: qt_bundle_plan.QtBundlePlan, app_path: pathlib.Path, display: str,
		version_runner: object = None,
		) -> None:
	"""Inspect one synthetic bundle with its explicit independent build identity."""
	runner = version_runner or _successful_version_result
	build_qt_app.inspect_built_app(plan, app_path, _release(display), "26.7.1", runner)


#============================================
def _make_synthetic_bundle(
		tmp_path: pathlib.Path, plan: qt_bundle_plan.QtBundlePlan, version: str,
		) -> pathlib.Path:
	"""Create one minimal inspected frozen-bundle fixture without PyInstaller.

	Args:
		tmp_path: Test-owned temporary directory.
		plan: Bundle plan whose declared payload paths are created.
		version: Expected frozen application version.

	Returns:
		Synthetic ``BKChem.app`` root suitable for post-build inspection tests.
	"""
	app_path = tmp_path / plan.bundle_name
	contents_path = app_path / "Contents"
	executable_path = contents_path / "MacOS" / plan.app_name
	resources_root = contents_path / "Resources"
	frameworks_root = contents_path / "Frameworks"
	executable_path.parent.mkdir(parents=True)
	executable_path.write_text("synthetic executable", encoding="utf-8")
	executable_path.chmod(0o755)
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
		payload_path = resources_root.joinpath(*pathlib.PurePosixPath(relative_path).parts)
		payload_path.parent.mkdir(parents=True, exist_ok=True)
		payload_path.write_text("synthetic resource payload", encoding="utf-8")
	profile = _release(version)
	dist_info = resources_root / build_qt_app._expected_dist_info_name(plan, profile)
	dist_info.mkdir()
	(dist_info / "METADATA").write_text(
		f"Metadata-Version: 2.1\nName: {plan.frontend_distribution}\nVersion: {profile.distribution}\n",
		encoding="utf-8",
	)
	for member_name in ("WHEEL", "RECORD"):
		(dist_info / member_name).write_text("synthetic metadata payload", encoding="utf-8")
	python_binary = frameworks_root / "Python.framework" / "Versions" / "3.12" / "Python"
	python_binary.parent.mkdir(parents=True)
	python_binary.write_text("synthetic Python runtime", encoding="utf-8")
	python_binary.chmod(0o755)
	for relative_path in (
		"PySide6/QtCore.abi3.so",
		"PySide6/Qt/plugins/platforms/libqcocoa.dylib",
		"rdkit/rdBase.abi3.so",
		"cairo/_cairo.abi3.so",
		"rustworkx/rustworkx.abi3.so",
	):
		payload_path = frameworks_root.joinpath(*pathlib.PurePosixPath(relative_path).parts)
		payload_path.parent.mkdir(parents=True, exist_ok=True)
		payload_path.write_text("synthetic native payload", encoding="utf-8")
	info = {
		"CFBundleIdentifier": plan.bundle_identifier,
		"BKChemReleaseVersion": profile.display,
		"CFBundleShortVersionString": profile.macos_short_version,
		"CFBundleVersion": "26.7.1",
	}
	with (contents_path / "Info.plist").open("wb") as info_file:
		plistlib.dump(info, info_file)
	return app_path


#============================================
def _successful_version_result(
		command: tuple[str, ...], _cwd: pathlib.Path, _timeout_seconds: float,
		) -> subprocess.CompletedProcess[str]:
	"""Return a frozen public-version result that follows the expected contract.

	Args:
		command: Version command submitted by the builder.
		_cwd: Unused synthetic bundle working directory.
		_timeout_seconds: Unused bounded timeout requested by the builder.

	Returns:
		Successful completed-process fixture.
	"""
	return subprocess.CompletedProcess(command, 0, "BKChem-Qt 26.07\n", "")


#============================================
def _write_frontend_wheel(
		wheel_dir: pathlib.Path, version: str, *, metadata_name: str = "bkchem-qt",
		metadata_version: str | None = None, include_metadata: bool = True,
		extra_members: tuple[tuple[str, bytes], ...] = (),
		directory_required_member: str | None = None,
		link_required_member: str | None = None,
		dos_directory_required_member: str | None = None,
		special_required_member: str | None = None,
		) -> pathlib.Path:
	"""Write one minimal wheel-shaped frontend metadata fixture.

	Args:
		wheel_dir: Test-owned wheel output directory.
		version: Canonical frontend version used in the archive filename.
		metadata_name: Distribution name placed into the archive METADATA.
		metadata_version: Optional METADATA version override.
		include_metadata: Whether the required METADATA member is present.
		extra_members: Additional exact ZIP members for one validation case.
		directory_required_member: Required direct member written as a ZIP directory.
		link_required_member: Required direct member written as a symbolic link.
		dos_directory_required_member: Required member written as a DOS/FAT directory.
		special_required_member: Required member written as a POSIX special file.

	Returns:
		Created wheel archive path.
	"""
	wheel_dir.mkdir(parents=True, exist_ok=True)
	wheel_version = build_qt_app._canonical_pep440_version(version)
	dist_info = f"bkchem_qt-{wheel_version}.dist-info"
	wheel_path = wheel_dir / f"bkchem_qt-{wheel_version}-py3-none-any.whl"
	with zipfile.ZipFile(wheel_path, "w") as archive:
		required_members = {
			"METADATA": (
				f"Metadata-Version: 2.1\nName: {metadata_name}\n"
				f"Version: {metadata_version or version}\n"
			),
			"WHEEL": "Wheel-Version: 1.0\n",
			"RECORD": "",
		}
		for member_name, payload in required_members.items():
			if member_name == "METADATA" and not include_metadata:
				continue
			member_path = f"{dist_info}/{member_name}"
			if member_name == directory_required_member:
				archive.writestr(f"{member_path}/", "")
			elif member_name == link_required_member:
				link_info = zipfile.ZipInfo(member_path)
				link_info.create_system = 3
				link_info.external_attr = 0o120777 << 16
				archive.writestr(link_info, "target")
			elif member_name == dos_directory_required_member:
				directory_info = zipfile.ZipInfo(member_path)
				directory_info.create_system = 0
				directory_info.external_attr = 0x10
				archive.writestr(directory_info, "")
			elif member_name == special_required_member:
				special_info = zipfile.ZipInfo(member_path)
				special_info.create_system = 3
				special_info.external_attr = 0o060644 << 16
				archive.writestr(special_info, "")
			else:
				archive.writestr(member_path, payload)
		for member_name, payload in extra_members:
			archive.writestr(member_name, payload)
	return wheel_path


#============================================
def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
	"""Build one complete PNG chunk with its deterministic CRC.

	Args:
		chunk_type: Four-byte ASCII PNG chunk type.
		data: Chunk payload bytes.

	Returns:
		One complete length/type/payload/CRC PNG chunk.
	"""
	chunk = struct.pack(">I", len(data)) + chunk_type + data
	crc = zlib.crc32(chunk_type + data) & 0xffffffff
	return chunk + struct.pack(">I", crc)


#============================================
def _valid_rgba_png(width: int, height: int) -> bytes:
	"""Build one complete transparent 8-bit RGBA PNG for ICNS writer tests.

	Args:
		width: IHDR width in pixels.
		height: IHDR height in pixels.

	Returns:
		Complete structurally valid PNG bytes with the requested dimensions.
	"""
	ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
	row = b"\x00" + (b"\x00" * (width * 4))
	idat = zlib.compress(row * height)
	payload = build_qt_app.PNG_SIGNATURE
	payload += _png_chunk(b"IHDR", ihdr)
	payload += _png_chunk(b"IDAT", idat)
	payload += _png_chunk(b"IEND", b"")
	return payload


#============================================
def _rgba_png_chunks(width: int, height: int) -> tuple[bytes, bytes]:
	"""Build the fixed IHDR and compressed scanline bytes for one test PNG.

	Args:
		width: IHDR width in pixels.
		height: IHDR height in pixels.

	Returns:
		Controlled 8-bit RGBA IHDR and nonempty compressed IDAT payload bytes.
	"""
	ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
	row = b"\x00" + (b"\x00" * (width * 4))
	idat = zlib.compress(row * height)
	return ihdr, idat


#============================================
def _invalid_png(kind: str) -> bytes:
	"""Return one complete-PNG validation failure shape.

	Args:
		kind: Stable corruption category selected by the parameterized test.

	Returns:
		Malformed PNG bytes for one validation boundary case.
	"""
	payload = _valid_rgba_png(16, 16)
	if kind == "truncated":
		return payload[:-1]
	if kind == "malformed":
		return payload[:12] + b"1HDR" + payload[16:]
	if kind == "corrupt_crc":
		return payload[:29] + bytes([payload[29] ^ 1]) + payload[30:]
	if kind == "missing_iend":
		return payload[:-12]
	ihdr, idat = _rgba_png_chunks(16, 16)
	if kind == "nonconsecutive_idat":
		split = len(idat) // 2
		return (
			build_qt_app.PNG_SIGNATURE
			+ _png_chunk(b"IHDR", ihdr)
			+ _png_chunk(b"IDAT", idat[:split])
			+ _png_chunk(b"tEXt", b"note=between-image-data")
			+ _png_chunk(b"IDAT", idat[split:])
			+ _png_chunk(b"IEND", b"")
		)
	if kind == "empty_idat":
		return (
			build_qt_app.PNG_SIGNATURE
			+ _png_chunk(b"IHDR", ihdr)
			+ _png_chunk(b"IDAT", b"")
			+ _png_chunk(b"IEND", b"")
		)
	if kind == "duplicate_ihdr":
		return (
			build_qt_app.PNG_SIGNATURE
			+ _png_chunk(b"IHDR", ihdr)
			+ _png_chunk(b"IHDR", ihdr)
			+ _png_chunk(b"IDAT", idat)
			+ _png_chunk(b"IEND", b"")
		)
	if kind == "iend_before_idat":
		return (
			build_qt_app.PNG_SIGNATURE
			+ _png_chunk(b"IHDR", ihdr)
			+ _png_chunk(b"IEND", b"")
			+ _png_chunk(b"IDAT", idat)
		)
	raise ValueError(f"Unknown PNG corruption kind: {kind}")


#============================================
def _parse_icns_chunks(data: bytes) -> list[tuple[str, int, bytes]]:
	"""Parse an ICNS container produced by the local deterministic writer.

	Args:
		data: Complete binary ICNS payload.

	Returns:
		Ordered chunk type, declared length, and payload tuples.
	"""
	chunks = []
	offset = 8
	while offset < len(data):
		chunk_type = data[offset:offset + 4].decode("ascii")
		length = struct.unpack(">I", data[offset + 4:offset + 8])[0]
		payload = data[offset + 8:offset + length]
		chunks.append((chunk_type, length, payload))
		offset += length
	return chunks


#============================================
def test_fresh_layout_uses_only_isolated_run_paths(tmp_path: pathlib.Path) -> None:
	"""A fresh nested run root has its own app, work, spec, and icon locations."""
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "one_run")

	assert layout.app_path == tmp_path / "tmp" / "one_run" / "app" / "BKChem.app"
	assert (
		layout.work_dir, layout.spec_dir, layout.icon_path, layout.wheel_dir,
		layout.metadata_dir, layout.pyinstaller_config_parent,
	) == (
		tmp_path / "tmp" / "one_run" / "work",
		tmp_path / "tmp" / "one_run" / "spec",
		tmp_path / "tmp" / "one_run" / "icon" / "BKChem.icns",
		tmp_path / "tmp" / "one_run" / "wheel",
		tmp_path / "tmp" / "one_run" / "metadata",
		tmp_path / "tmp" / "one_run" / "pyinstaller_config",
	)


#============================================
@pytest.mark.parametrize("output_kind", ("existing", "repo_root", "tmp_root", "outside"))
def test_layout_rejects_nonfresh_or_unsafe_output(
		tmp_path: pathlib.Path, output_kind: str,
		) -> None:
	"""The builder requires one new root under the repository-owned tmp directory."""
	tmp_root = tmp_path / "tmp"
	tmp_root.mkdir()
	if output_kind == "existing":
		output = tmp_root / "existing"
		output.mkdir()
	elif output_kind == "repo_root":
		output = tmp_path
	elif output_kind == "tmp_root":
		output = tmp_root
	else:
		output = tmp_path.parent / "outside"

	with pytest.raises(ValueError, match="output"):
		build_qt_app.make_build_layout(tmp_path, output)


#============================================
def test_pyinstaller_command_adds_staged_wheel_metadata_without_legacy_hook(
		tmp_path: pathlib.Path,
		) -> None:
	"""The command consumes staged frontend metadata as ordinary top-level bundle data."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "run")
	staged_metadata = layout.metadata_dir / "bkchem_qt-26.2a1.dist-info"
	command = build_qt_app.make_pyinstaller_args(plan, layout, staged_metadata)
	command_text = " ".join(command)

	assert all(value in command_text for value in (
		"--windowed", "--onedir", "--target-architecture arm64",
		"bkchem_qt.bridge.worker", "PySide6.QtWidgets", plan.entry_script,
	))
	assert f"{staged_metadata}:{staged_metadata.name}" in command
	assert "--copy-metadata" not in command
	assert "--clean" not in command and "--noconfirm" not in command and "tkinter" not in command_text


#============================================
def test_pyinstaller_config_parent_is_fresh_and_child_environment_preserves_parent_values(
		tmp_path: pathlib.Path,
		) -> None:
	"""PyInstaller receives one run-local cache parent without altering its parent environment."""
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "run")
	layout.run_root.mkdir(parents=True)
	inherited = {"PATH": "/example/bin", "KEEP_ME": "value", "PYINSTALLER_CONFIG_DIR": "/old"}

	prepared = build_qt_app.prepare_pyinstaller_config_parent(layout)
	environment = build_qt_app.make_pyinstaller_environment(layout, inherited)

	assert prepared == layout.run_root / "pyinstaller_config"
	assert prepared.is_dir()
	assert inherited == {"PATH": "/example/bin", "KEEP_ME": "value", "PYINSTALLER_CONFIG_DIR": "/old"}
	assert environment == {
		"PATH": "/example/bin",
		"KEEP_ME": "value",
		"PYINSTALLER_CONFIG_DIR": str(prepared),
	}


#============================================
def test_pyinstaller_config_parent_rejects_missing_root_existing_parent_and_invalid_layout(
		tmp_path: pathlib.Path,
		) -> None:
	"""The cache parent requires the planned fresh directory inside a real run root."""
	missing_layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "missing")
	with pytest.raises(RuntimeError, match="run root is missing"):
		build_qt_app.prepare_pyinstaller_config_parent(missing_layout)

	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "existing")
	layout.run_root.mkdir(parents=True)
	layout.pyinstaller_config_parent.mkdir()
	with pytest.raises(RuntimeError, match="must be new"):
		build_qt_app.prepare_pyinstaller_config_parent(layout)

	invalid_layout = dataclasses.replace(
		layout, pyinstaller_config_parent=tmp_path / "outside_config",
	)
	with pytest.raises(RuntimeError, match="planned run-root location"):
		build_qt_app.make_pyinstaller_environment(invalid_layout, {})


#============================================
def test_checked_pyinstaller_invocation_receives_only_the_prepared_child_environment(
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The subprocess seam receives the copied run-local configuration environment."""
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "captured")
	layout.run_root.mkdir(parents=True)
	build_qt_app.prepare_pyinstaller_config_parent(layout)
	environment = build_qt_app.make_pyinstaller_environment(layout, {"KEEP_ME": "value"})
	captured: dict[str, object] = {}

	def record_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
		"""Capture the checked subprocess child environment without starting a process."""
		captured["command"] = args[0]
		captured["env"] = kwargs["env"]
		return subprocess.CompletedProcess(args[0], 0, "", "")

	monkeypatch.setattr(build_qt_app.subprocess, "run", record_run)
	command = (sys.executable, "-m", "PyInstaller", "--version")
	build_qt_app._run_checked(command, tmp_path, env=environment)

	assert captured == {"command": command, "env": environment}


#============================================
def test_checked_pyinstaller_failure_keeps_child_diagnostics(
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed isolated PyInstaller child retains its command and captured diagnostics."""
	command = (sys.executable, "-m", "PyInstaller", "--version")

	def failed_run(*args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
		"""Return the controlled child failure used to verify error reporting."""
		return subprocess.CompletedProcess(args[0], 7, "child stdout", "child stderr")

	monkeypatch.setattr(build_qt_app.subprocess, "run", failed_run)
	with pytest.raises(RuntimeError, match="Command failed \\(7\\)") as error:
		build_qt_app._run_checked(command, tmp_path, env={"PYINSTALLER_CONFIG_DIR": "/run"})

	assert "PyInstaller --version" in str(error.value)
	assert "child stdout" in str(error.value)
	assert "child stderr" in str(error.value)


#============================================
def test_frontend_wheel_staging_extracts_complete_matching_metadata(
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""One local wheel produces a complete top-level metadata record for frozen lookup."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "metadata")
	version = "26.02a1"
	_write_frontend_wheel(layout.wheel_dir, version, metadata_version="26.2a1")

	stage = build_qt_app.stage_frontend_metadata(plan, layout, version)

	assert stage.dist_info_path == layout.metadata_dir / "bkchem_qt-26.2a1.dist-info"
	assert {
		path.name for path in stage.dist_info_path.iterdir()
	} >= {"METADATA", "WHEEL", "RECORD"}
	monkeypatch.syspath_prepend(str(layout.metadata_dir))
	assert importlib.metadata.version("bkchem-qt") == "26.2a1"


#============================================
@pytest.mark.parametrize(
	"kind, expected_message",
	(
		("wrong_name", "METADATA Name"),
		("wrong_version", "METADATA Version"),
		("missing_metadata", "incomplete"),
		("traversal", "unsafe ZIP member"),
		("ambiguous", "ambiguous"),
	),
)
def test_frontend_wheel_staging_rejects_invalid_or_ambiguous_archives(
		tmp_path: pathlib.Path, kind: str, expected_message: str,
		) -> None:
	"""The metadata boundary rejects malformed archives before source analysis can begin."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / kind)
	version = "26.02a1"
	if kind == "wrong_name":
		_write_frontend_wheel(layout.wheel_dir, version, metadata_name="other-project")
	elif kind == "wrong_version":
		_write_frontend_wheel(layout.wheel_dir, version, metadata_version="0.0")
	elif kind == "missing_metadata":
		_write_frontend_wheel(layout.wheel_dir, version, include_metadata=False)
	elif kind == "traversal":
		_write_frontend_wheel(
			layout.wheel_dir, version, extra_members=(("../outside.txt", b"escape"),),
		)
	else:
		_write_frontend_wheel(layout.wheel_dir, version)
		wheel_version = build_qt_app._canonical_pep440_version(version)
		second = layout.wheel_dir / f"bkchem_qt-{wheel_version}-py2-none-any.whl"
		second.write_bytes((layout.wheel_dir / f"bkchem_qt-{wheel_version}-py3-none-any.whl").read_bytes())

	with pytest.raises(RuntimeError, match=expected_message):
		build_qt_app.stage_frontend_metadata(plan, layout, version)


#============================================
@pytest.mark.parametrize(
	"member_kind, member_name",
	(
		("directory", "METADATA"),
		("directory", "WHEEL"),
		("directory", "RECORD"),
		("link", "WHEEL"),
		("dos_directory", "WHEEL"),
		("special", "WHEEL"),
	),
)
def test_frontend_wheel_staging_requires_regular_direct_metadata_members(
		tmp_path: pathlib.Path, member_kind: str, member_name: str,
		) -> None:
	"""Each required dist-info record is one direct regular archive member."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	layout = build_qt_app.make_build_layout(
		tmp_path, tmp_path / "tmp" / f"{member_kind}_{member_name}",
	)
	if member_kind == "directory":
		_write_frontend_wheel(
			layout.wheel_dir, "26.02a1", directory_required_member=member_name,
		)
	elif member_kind == "link":
		_write_frontend_wheel(
			layout.wheel_dir, "26.02a1", link_required_member=member_name,
		)
	elif member_kind == "dos_directory":
		_write_frontend_wheel(
			layout.wheel_dir, "26.02a1", dos_directory_required_member=member_name,
		)
	else:
		_write_frontend_wheel(
			layout.wheel_dir, "26.02a1", special_required_member=member_name,
		)

	with pytest.raises(RuntimeError, match="incomplete or has non-regular"):
		build_qt_app.stage_frontend_metadata(plan, layout, "26.02a1")


#============================================
def test_frontend_wheel_command_is_local_and_has_no_installation_phase(
		tmp_path: pathlib.Path,
		) -> None:
	"""The wheel stage builds only the checked-out frontend into the retained run root."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "wheel")
	command = build_qt_app.make_frontend_wheel_args(plan, layout)

	assert command == (
		sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir",
		str(layout.wheel_dir), plan.frontend_project_dir,
	)


#============================================
def test_icon_specs_follow_the_complete_macos_iconset_filename_contract() -> None:
	"""The icon source produces every standard macOS point-size and Retina member."""
	assert build_qt_app.ICON_SPECS == (
		("icon_16x16.png", 16),
		("icon_16x16@2x.png", 32),
		("icon_32x32.png", 32),
		("icon_32x32@2x.png", 64),
		("icon_128x128.png", 128),
		("icon_128x128@2x.png", 256),
		("icon_256x256.png", 256),
		("icon_256x256@2x.png", 512),
		("icon_512x512.png", 512),
		("icon_512x512@2x.png", 1024),
	)


#============================================
def test_icon_commands_render_qt_source_then_convert_the_standard_iconset(
		tmp_path: pathlib.Path,
		) -> None:
	"""The planned conversion consumes the generated iconset and writes the required ICNS."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "icon_run")
	commands = build_qt_app.make_icon_commands(plan, layout)

	assert commands[0] == (
		"rsvg-convert", "-w", "16", "-h", "16", plan.icon_source,
		"-o", str(layout.iconset_dir / "icon_16x16.png"),
	)
	assert commands[-1] == (
		"iconutil", "-c", "icns", str(layout.iconset_dir), "-o", str(layout.icon_path),
	)


#============================================
def test_fallback_icns_writer_frames_all_distinct_png_sizes_in_standard_order(
		tmp_path: pathlib.Path,
		) -> None:
	"""Fallback output has exact ICNS framing and each required PNG representation."""
	png_paths = []
	for chunk_type, size in build_qt_app.FALLBACK_ICNS_SPECS:
		png_path = tmp_path / f"icon_{size}.png"
		png_path.write_bytes(_valid_rgba_png(size, size))
		png_paths.append((chunk_type, size, png_path))
	output = tmp_path / "BKChem.icns"

	build_qt_app.write_multiresolution_icns(tuple(png_paths), output)

	data = output.read_bytes()
	assert data[:4] == b"icns"
	assert struct.unpack(">I", data[4:8])[0] == len(data)
	chunks = _parse_icns_chunks(data)
	assert [(chunk_type, length) for chunk_type, length, _payload in chunks] == [
		(chunk_type, len(payload) + 8)
		for chunk_type, _size, payload in [
			(chunk_type, size, _valid_rgba_png(size, size))
			for chunk_type, size in build_qt_app.FALLBACK_ICNS_SPECS
		]
	]
	assert [
		struct.unpack(">II", payload[16:24]) for _chunk_type, _length, payload in chunks
	] == [(size, size) for _chunk_type, size in build_qt_app.FALLBACK_ICNS_SPECS]


#============================================
def test_fallback_icns_writer_rejects_wrong_png_dimensions(tmp_path: pathlib.Path) -> None:
	"""The binary encoder rejects a valid PNG whose rendered geometry is wrong."""
	png_paths = []
	for chunk_type, size in build_qt_app.FALLBACK_ICNS_SPECS:
		png_path = tmp_path / f"icon_{size}.png"
		actual_size = 17 if size == 16 else size
		png_path.write_bytes(_valid_rgba_png(actual_size, actual_size))
		png_paths.append((chunk_type, size, png_path))

	with pytest.raises(RuntimeError, match="expected 16x16"):
		build_qt_app.write_multiresolution_icns(tuple(png_paths), tmp_path / "bad.icns")


#============================================
def test_iconutil_self_test_reports_system_source_and_encoder_failures(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
		) -> None:
	"""The selected fallback has distinct diagnostics for absent source and failed encoding."""
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "self_test")
	layout.icon_dir.mkdir(parents=True)
	monkeypatch.setattr(build_qt_app.shutil, "which", lambda _program: None)
	unavailable = build_qt_app._iconutil_self_test(layout, tmp_path)

	assert unavailable.usable is False and "not on PATH" in unavailable.diagnostic

	monkeypatch.setattr(build_qt_app.shutil, "which", lambda _program: "iconutil")
	missing = build_qt_app._iconutil_self_test(layout, tmp_path, tmp_path / "no-system-icon.icns")
	assert missing.usable is False
	assert "system icon is missing" in missing.diagnostic
	icon = tmp_path / "SystemIcon.icns"
	icon.write_bytes(b"source")
	monkeypatch.setattr(
		build_qt_app.subprocess,
		"run",
		lambda *_args, **_kwargs: subprocess.CompletedProcess(("iconutil",), 1, "", "Invalid Iconset"),
	)

	failed = build_qt_app._iconutil_self_test(layout, tmp_path, icon)

	assert failed.usable is False
	assert "decoding system icon" in failed.diagnostic and "Invalid Iconset" in failed.diagnostic


#============================================
@pytest.mark.parametrize("stage", ("decode", "encode"))
def test_iconutil_self_test_timeout_uses_the_fallback_diagnostic(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, stage: str,
		) -> None:
	"""Each system-icon probe has one terminal timeout outcome rather than a hang."""
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "timeout")
	layout.icon_dir.mkdir(parents=True)
	icon = tmp_path / "SystemIcon.icns"
	icon.write_bytes(b"source")
	seen_timeouts: list[float] = []
	monkeypatch.setattr(build_qt_app.shutil, "which", lambda _program: "iconutil")

	def timeout_probe(
			command: tuple[str, ...], **kwargs: object,
			) -> subprocess.CompletedProcess[str]:
		"""Record the requested deadline and time out the selected probe direction."""
		timeout_seconds = kwargs["timeout"]
		if not isinstance(timeout_seconds, float):
			raise TypeError("timeout must be a float")
		seen_timeouts.append(timeout_seconds)
		if (stage == "decode" and command[2] == "iconset") or (
				stage == "encode" and command[2] == "icns"
				):
			raise subprocess.TimeoutExpired(command, timeout_seconds)
		return subprocess.CompletedProcess(command, 0, "", "")

	monkeypatch.setattr(build_qt_app.subprocess, "run", timeout_probe)
	result = build_qt_app._iconutil_self_test(layout, tmp_path, icon)

	assert result.usable is False
	assert "timed out while" in result.diagnostic and all(timeout > 0.0 for timeout in seen_timeouts)


#============================================
@pytest.mark.parametrize(
	"kind",
	(
		"truncated",
		"malformed",
		"corrupt_crc",
		"missing_iend",
		"nonconsecutive_idat",
		"empty_idat",
		"duplicate_ihdr",
		"iend_before_idat",
	),
)
def test_png_validator_rejects_incomplete_or_corrupt_png_structure(kind: str) -> None:
	"""ICNS framing rejects damaged renderer output before copying its bytes."""
	with pytest.raises(RuntimeError, match="PNG"):
		build_qt_app._png_dimensions(_invalid_png(kind), pathlib.Path(f"{kind}.png"))


#============================================
def test_png_validator_accepts_a_complete_rgba_png() -> None:
	"""The fallback boundary accepts a complete generated 8-bit RGBA PNG."""
	dimensions = build_qt_app._png_dimensions(_valid_rgba_png(32, 32), pathlib.Path("valid.png"))

	assert dimensions == (32, 32)


#============================================
def test_icon_encoder_uses_standard_route_only_after_self_test_passes(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture,
		) -> None:
	"""A healthy system encoder retains the standard ten-member iconset route."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "standard")
	commands: list[tuple[str, ...]] = []
	monkeypatch.setattr(
		build_qt_app, "_iconutil_self_test",
		lambda _layout, _root: build_qt_app.IconutilSelfTestResult(True, "verified"),
	)
	monkeypatch.setattr(build_qt_app.shutil, "which", lambda _program: "rsvg-convert")
	monkeypatch.setattr(
		build_qt_app, "_run_checked", lambda command, _root: commands.append(command),
	)

	build_qt_app._create_icon(plan, layout, tmp_path)

	assert commands == list(build_qt_app.make_icon_commands(plan, layout))
	assert "standard iconutil" in capsys.readouterr().out


#============================================
def test_icon_encoder_uses_qt_png_chunk_route_after_self_test_fails(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture,
		) -> None:
	"""A failed host self-test renders Qt source and emits the complete ICNS fallback."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	layout = build_qt_app.make_build_layout(tmp_path, tmp_path / "tmp" / "fallback")
	commands: list[tuple[str, ...]] = []
	monkeypatch.setattr(
		build_qt_app, "_iconutil_self_test",
		lambda _layout, _root: build_qt_app.IconutilSelfTestResult(False, "known host failure"),
	)

	def render_png(command: tuple[str, ...], _root: pathlib.Path) -> None:
		"""Record controlled render calls and write the requested complete test PNG."""
		commands.append(command)
		size = int(command[command.index("--size") + 1])
		output = pathlib.Path(command[command.index("--output") + 1])
		output.write_bytes(_valid_rgba_png(size, size))

	monkeypatch.setattr(build_qt_app, "_run_checked", render_png)

	build_qt_app._create_icon(plan, layout, tmp_path)

	assert len(commands) == len(build_qt_app.FALLBACK_ICNS_SPECS)
	assert all(command[1] == str(build_qt_app.QT_ICON_RENDERER) for command in commands)
	assert layout.icon_path.read_bytes()[:4] == b"icns"
	assert "Qt PNG-chunk fallback" in capsys.readouterr().out


#============================================
def test_smoke_command_uses_launchservices_and_orders_app_arguments(
		tmp_path: pathlib.Path,
		) -> None:
	"""A macOS smoke opens the app before passing its timer and receipt args."""
	smoke_root = tmp_path / "smoke"
	command = build_qt_app.make_smoke_args(tmp_path / "BKChem.app", 2.0, smoke_root)

	assert command == (
		"/usr/bin/open", "-W", "-n", "-F", "-g", "--stdout", str(smoke_root / "stdout.log"),
		"--stderr", str(smoke_root / "stderr.log"), str(tmp_path / "BKChem.app"), "--args",
		"--smoke-exit", "2.0", "--smoke-receipt", str(smoke_root / "completion.json"),
	)


#============================================
def test_smoke_receipt_validator_requires_the_fixed_success_schema(tmp_path: pathlib.Path) -> None:
	"""Only an exact zero-exit app receipt proves controlled lifecycle completion."""
	receipt_path = tmp_path / "completion.json"
	receipt_path.write_text('{"schema":"bkchem-smoke-1","exit_code":0}', encoding="utf-8")

	build_qt_app._validate_smoke_receipt(receipt_path)


#============================================
@pytest.mark.parametrize("payload", ('{}', '{"schema":"bkchem-smoke-1","exit_code":1}'))
def test_smoke_receipt_validator_rejects_non_success_payloads(
		tmp_path: pathlib.Path, payload: str,
		) -> None:
	"""A malformed or nonzero receipt cannot turn an incomplete smoke into success."""
	receipt_path = tmp_path / "completion.json"
	receipt_path.write_text(payload, encoding="utf-8")

	with pytest.raises(RuntimeError, match="Invalid smoke receipt"):
		build_qt_app._validate_smoke_receipt(receipt_path)


#============================================
def test_macos_smoke_rejects_missing_receipt_after_launcher_success(tmp_path: pathlib.Path) -> None:
	"""LaunchServices success alone is not application lifecycle completion."""
	def successful_launcher(
			_command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Return a successful launcher result without creating an app receipt."""
		return subprocess.CompletedProcess(_command, 0, "", "")

	with pytest.raises(RuntimeError, match="Missing or invalid smoke receipt"):
		build_qt_app.run_macos_smoke(
			tmp_path / "BKChem.app", 2.0, tmp_path / "smoke", tmp_path, tmp_path,
			successful_launcher,
		)


#============================================
def test_macos_smoke_reports_launcher_timeout(tmp_path: pathlib.Path) -> None:
	"""A bounded launcher timeout retains its command and diagnostic locations."""
	def timed_out_launcher(
			command: tuple[str, ...], _cwd: pathlib.Path, timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Raise the controlled timeout used by the dedicated smoke runner."""
		raise subprocess.TimeoutExpired(command, timeout)

	with pytest.raises(RuntimeError, match="launcher timed out"):
		build_qt_app.run_macos_smoke(
			tmp_path / "BKChem.app", 2.0, tmp_path / "smoke", tmp_path, tmp_path,
			timed_out_launcher,
		)


#============================================
def test_macos_smoke_rejects_launcher_failure_before_receipt_inspection(tmp_path: pathlib.Path) -> None:
	"""A failed app launch is terminal even when no receipt decision is available."""
	def failed_launcher(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Return the controlled nonzero LaunchServices result."""
		return subprocess.CompletedProcess(command, 1, "", "")

	with pytest.raises(RuntimeError, match="launcher failed"):
		build_qt_app.run_macos_smoke(
			tmp_path / "BKChem.app", 2.0, tmp_path / "smoke", tmp_path, tmp_path,
			failed_launcher,
		)


#============================================
def test_macos_smoke_rejects_fatal_diagnostic_after_valid_receipt(tmp_path: pathlib.Path) -> None:
	"""A late fatal app diagnostic remains terminal even after controlled completion."""
	def launcher(
			_command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Create controlled completion evidence plus a retained fatal diagnostic."""
		smoke_root = tmp_path / "smoke"
		(smoke_root / "completion.json").write_text(
			'{"schema":"bkchem-smoke-1","exit_code":0}', encoding="utf-8",
		)
		(smoke_root / "stderr.log").write_text("Abort trap: 6", encoding="utf-8")
		return subprocess.CompletedProcess(_command, 0, "", "")

	with pytest.raises(RuntimeError, match="fatal application diagnostic"):
		build_qt_app.run_macos_smoke(
			tmp_path / "BKChem.app", 2.0, tmp_path / "smoke", tmp_path, tmp_path, launcher,
		)


#============================================
def test_macos_smoke_rejects_traversal_before_creating_or_launching(
		tmp_path: pathlib.Path,
		) -> None:
	"""A relative traversal cannot place smoke artifacts outside its retained run."""
	run_root = tmp_path / "run"
	run_root.mkdir()
	launcher_calls: list[tuple[str, ...]] = []

	def launcher(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Record an unexpected launcher request."""
		launcher_calls.append(command)
		return subprocess.CompletedProcess(command, 0, "", "")

	with pytest.raises(build_qt_app.SmokePathError, match="escapes selected build run root"):
		build_qt_app.run_macos_smoke(
			tmp_path / "BKChem.app", 2.0, run_root / "smoke" / ".." / ".." / "outside",
			run_root, tmp_path, launcher,
		)

	assert launcher_calls == []
	assert not (tmp_path / "outside").exists()


#============================================
def test_macos_smoke_rejects_escaping_symlink_before_creating_or_launching(
		tmp_path: pathlib.Path,
		) -> None:
	"""A smoke directory symlink must resolve below the selected retained run."""
	run_root = tmp_path / "run"
	run_root.mkdir()
	external_root = tmp_path / "external"
	external_root.mkdir()
	(run_root / "escape").symlink_to(external_root, target_is_directory=True)
	launcher_calls: list[tuple[str, ...]] = []

	def launcher(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Record an unexpected launcher request."""
		launcher_calls.append(command)
		return subprocess.CompletedProcess(command, 0, "", "")

	with pytest.raises(build_qt_app.SmokePathError, match="escapes selected build run root"):
		build_qt_app.run_macos_smoke(
			tmp_path / "BKChem.app", 2.0, run_root / "escape" / "smoke",
			run_root, tmp_path, launcher,
		)

	assert launcher_calls == []
	assert not (external_root / "smoke").exists()


#============================================
def test_macos_smoke_uses_contained_resolved_paths_for_its_valid_launcher(
		tmp_path: pathlib.Path,
		) -> None:
	"""A valid nested smoke root creates and launches only its contained artifact paths."""
	run_root = tmp_path / "run"
	run_root.mkdir()
	smoke_root = run_root / "checks" / "smoke"
	commands: list[tuple[str, ...]] = []

	def launcher(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Publish the controlled app observations through the supplied fixed paths."""
		commands.append(command)
		(smoke_root / "completion.json").write_text(
			'{"schema":"bkchem-smoke-1","exit_code":0}', encoding="utf-8",
		)
		(smoke_root / "stderr.log").write_text("", encoding="utf-8")
		return subprocess.CompletedProcess(command, 0, "", "")

	build_qt_app.run_macos_smoke(
		tmp_path / "BKChem.app", 2.0, smoke_root, run_root, tmp_path, launcher,
	)

	assert commands == [build_qt_app.make_smoke_args(tmp_path / "BKChem.app", 2.0, smoke_root)]


#============================================
def test_dry_run_prints_commands_without_creating_requested_output(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture,
		) -> None:
	"""Dry run is a source-compatible preview that leaves its requested run root absent."""
	output = tmp_path / "tmp" / "preview"
	monkeypatch.setattr(build_qt_app, "resolve_repo_root", lambda: REPO_ROOT)
	monkeypatch.setattr(
		sys, "argv", ["build_qt_app.py", "--output", str(output), "--dry-run"],
	)
	monkeypatch.setattr(
		build_qt_app, "make_build_layout",
		lambda _root, _output: build_qt_app.QtBuildLayout(
			run_root=output,
			app_dist_dir=output / "app",
			work_dir=output / "work",
			spec_dir=output / "spec",
			icon_dir=output / "icon",
			iconset_dir=output / "icon" / "BKChem.iconset",
			icon_path=output / "icon" / "BKChem.icns",
			wheel_dir=output / "wheel",
			metadata_dir=output / "metadata",
			pyinstaller_config_parent=output / "pyinstaller_config",
			app_path=output / "app" / "BKChem.app",
		),
	)
	def reject_icon_self_test(_layout: build_qt_app.QtBuildLayout, _root: pathlib.Path) -> None:
		"""Fail the test if a preview tries to execute a real-build capability probe."""
		raise AssertionError("dry run ran icon self-test")

	monkeypatch.setattr(
		build_qt_app, "_iconutil_self_test", reject_icon_self_test,
	)

	build_qt_app.main()
	output_text = capsys.readouterr().out

	assert "Frontend wheel command:" in output_text
	assert "Frontend metadata stage:" in output_text
	assert "PyInstaller config parent:" in output_text
	assert "PyInstaller stage:" in output_text and "Future smoke command:" in output_text
	assert not output.exists()


#============================================
def test_post_build_inspection_checks_payload_identity_and_bounded_version_query(
		tmp_path: pathlib.Path,
		) -> None:
	"""Inspection accepts a complete plan-shaped bundle and its public version result."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	seen: list[tuple[tuple[str, ...], pathlib.Path, float]] = []

	def version_runner(
			command: tuple[str, ...], cwd: pathlib.Path, timeout_seconds: float,
			) -> subprocess.CompletedProcess[str]:
		"""Record the requested bounded version check and return a synthetic success."""
		seen.append((command, cwd, timeout_seconds))
		return _successful_version_result(command, cwd, timeout_seconds)

	_inspect(plan, app_path, "26.07", version_runner)

	assert seen == [
		(build_qt_app.make_version_args(app_path), app_path, build_qt_app.VERSION_CHECK_TIMEOUT_SECONDS)
	]


#============================================
def test_post_build_metadata_patch_makes_frozen_identity_match_the_plan(
		tmp_path: pathlib.Path,
		) -> None:
	"""The actual builder phase writes plan identity before inspection requires it."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")

	build_qt_app.patch_built_app_metadata(plan, app_path, _release("26.07"), "26.7.1")

	with (app_path / "Contents" / "Info.plist").open("rb") as info_file:
		info = plistlib.load(info_file)
	assert (
		info["CFBundleIdentifier"], info["BKChemReleaseVersion"],
		info["CFBundleShortVersionString"], info["CFBundleVersion"],
	) == (
		plan.bundle_identifier, "26.07", "26.7.0", "26.7.1",
	)


#============================================
@pytest.mark.parametrize(("plist_key", "bad_value", "diagnostic"), (
	("BKChemReleaseVersion", "26.7", "BKChemReleaseVersion"),
	("CFBundleShortVersionString", "26.07", "CFBundleShortVersionString"),
	("CFBundleVersion", "26.7a1", "CFBundleVersion"),
))
def test_post_build_inspection_checks_each_plist_version_representation(
		tmp_path: pathlib.Path, plist_key: str, bad_value: str, diagnostic: str,
		) -> None:
	"""Display, short release, and build keys fail independently at their own boundary."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	info_path = app_path / "Contents" / "Info.plist"
	with info_path.open("rb") as info_file:
		info = plistlib.load(info_file)
	info[plist_key] = bad_value
	with info_path.open("wb") as info_file:
		plistlib.dump(info, info_file)

	with pytest.raises(RuntimeError, match=diagnostic):
		_inspect(plan, app_path, "26.07")


#============================================
def test_post_build_inspection_requires_normalized_distribution_metadata(
		tmp_path: pathlib.Path,
		) -> None:
	"""Wheel metadata stays normalized even though public release text is padded."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.02a1")
	dist_info = app_path / "Contents" / "Resources" / build_qt_app._expected_dist_info_name(
		plan, _release("26.02a1"),
	)
	(dist_info / "METADATA").write_text(
		"Name: bkchem-qt\nVersion: 26.02a1\n", encoding="utf-8",
	)
	wrong_output = subprocess.CompletedProcess(("BKChem", "--version"), 0, "BKChem-Qt 26.02a1\n", "")

	with pytest.raises(RuntimeError, match="normalized distribution"):
		build_qt_app.inspect_built_app(
			plan, app_path, _release("26.02a1"), "26.7.1", lambda *_arguments: wrong_output,
		)


#============================================
def test_real_build_requires_explicit_bundle_build_before_creating_output(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
		) -> None:
	"""A real build stops before output creation until its macOS build identity is supplied."""
	output = tmp_path / "tmp" / "missing-build"
	monkeypatch.setattr(build_qt_app, "resolve_repo_root", lambda: REPO_ROOT)
	monkeypatch.setattr(
		build_qt_app,
		"make_build_layout",
		lambda _root, _output: build_qt_app.QtBuildLayout(
			run_root=output, app_dist_dir=output / "app", work_dir=output / "work",
			spec_dir=output / "spec", icon_dir=output / "icon",
			iconset_dir=output / "icon" / "BKChem.iconset", icon_path=output / "icon" / "BKChem.icns",
			wheel_dir=output / "wheel", metadata_dir=output / "metadata",
			pyinstaller_config_parent=output / "pyinstaller_config", app_path=output / "app" / "BKChem.app",
		),
	)
	monkeypatch.setattr(sys, "argv", ["build_qt_app.py", "--output", str(output)])

	with pytest.raises(RuntimeError, match="require --bundle-build"):
		build_qt_app.main()

	assert not output.exists()


#============================================
@pytest.mark.parametrize("missing_path", (
	"Contents/MacOS/BKChem", "Contents/Info.plist", "Contents/Frameworks",
	"Contents/Resources/bkchem_qt/resources/menus.yaml",
	"Contents/Resources/oasa_data/isotopes.json",
	"Contents/Frameworks/PySide6/Qt/plugins/platforms/libqcocoa.dylib",
	"Contents/Frameworks/rdkit/rdBase.abi3.so",
	"Contents/Frameworks/cairo/_cairo.abi3.so",
	"Contents/Frameworks/rustworkx/rustworkx.abi3.so",
))
def test_post_build_inspection_rejects_missing_or_corrupt_required_paths(
		tmp_path: pathlib.Path, missing_path: str,
		) -> None:
	"""Inspection fails clearly before launching when required bundle material is absent."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	target_path = app_path / missing_path
	if target_path.is_dir():
		for child_path in sorted(target_path.rglob("*"), reverse=True):
			if child_path.is_file():
				child_path.unlink()
			else:
				child_path.rmdir()
		target_path.rmdir()
	else:
		target_path.unlink()

	with pytest.raises(RuntimeError, match="Missing|corrupt|non-executable|Unsupported"):
		_inspect(plan, app_path, "26.07")


#============================================
def test_post_build_inspection_rejects_nonexecutable_python_runtime_leaf(
		tmp_path: pathlib.Path,
		) -> None:
	"""The inspected Python framework provides an executable regular runtime leaf."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	python_binary = app_path / "Contents/Frameworks/Python.framework/Versions/3.12/Python"
	python_binary.chmod(0o644)

	with pytest.raises(RuntimeError, match="Python runtime executable native payload"):
		_inspect(plan, app_path, "26.07")


#============================================
@pytest.mark.parametrize(("owned_path", "outside_path", "description"), (
	(
		"PySide6/QtCore.abi3.so", "lookalike/QtCore.abi3.so", "PySide6 QtCore",
	),
	(
		"rdkit/rdBase.abi3.so", "lookalike/rdBase.abi3.so", "rdkit",
	),
	(
		"cairo/_cairo.abi3.so", "lookalike/_cairo.abi3.so", "cairo",
	),
	(
		"rustworkx/rustworkx.abi3.so", "lookalike/rustworkx.abi3.so", "rustworkx",
	),
))
def test_post_build_inspection_rejects_native_capability_lookalike_outside_owner_root(
		tmp_path: pathlib.Path, owned_path: str, outside_path: str, description: str,
		) -> None:
	"""A native filename outside its declared package root cannot satisfy a capability."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	frameworks_root = app_path / "Contents" / "Frameworks"
	owned_payload = frameworks_root / owned_path
	owned_payload.unlink()
	lookalike = frameworks_root / outside_path
	lookalike.parent.mkdir(parents=True)
	lookalike.write_text("lookalike native payload", encoding="utf-8")

	with pytest.raises(RuntimeError, match=rf"{description} native payload below declared owner root"):
		_inspect(plan, app_path, "26.07")


#============================================
@pytest.mark.parametrize("root_name", ("MacOS", "Frameworks", "Resources"))
def test_macos_layout_classifier_rejects_missing_native_root_without_onedir_repair(
		tmp_path: pathlib.Path, root_name: str,
		) -> None:
	"""A sibling one-dir collection cannot satisfy the self-contained app contract."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	(tmp_path / plan.app_name / "_internal").mkdir(parents=True)
	(app_path / "Contents" / root_name).rename(app_path / "Contents" / f"missing-{root_name}")

	with pytest.raises(RuntimeError, match="Unsupported or missing"):
		_inspect(plan, app_path, "26.07")


#============================================
def test_post_build_inspection_accepts_contained_resource_framework_link(
		tmp_path: pathlib.Path,
		) -> None:
	"""A legal PyInstaller cross-link remains valid when its target stays in Contents."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	resources_root = app_path / "Contents" / "Resources"
	frameworks_root = app_path / "Contents" / "Frameworks"
	(resources_root / "bkchem_qt").rename(frameworks_root / "frontend_resources")
	(resources_root / "bkchem_qt").symlink_to("../Frameworks/frontend_resources", target_is_directory=True)

	_inspect(plan, app_path, "26.07")


#============================================
@pytest.mark.parametrize("link_kind", ("dangling", "escaping"))
def test_post_build_inspection_rejects_dangling_or_escaping_payload_link(
		tmp_path: pathlib.Path, link_kind: str,
		) -> None:
	"""Resource links must resolve to ordinary payloads contained by the app bundle."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	resource_path = app_path / "Contents" / "Resources" / "oasa_data" / "isotopes.json"
	resource_path.unlink()
	if link_kind == "dangling":
		resource_path.symlink_to("missing-isotopes.json")
	else:
		external_payload = tmp_path / "external-isotopes.json"
		external_payload.write_text("external", encoding="utf-8")
		resource_path.symlink_to(external_payload)

	with pytest.raises(RuntimeError, match="dangling|Required application payload escapes"):
		_inspect(plan, app_path, "26.07")


#============================================
@pytest.mark.parametrize("metadata_failure", ("missing_record", "wrong_name", "wrong_version"))
def test_post_build_inspection_rejects_invalid_staged_distribution_metadata(
		tmp_path: pathlib.Path, metadata_failure: str,
		) -> None:
	"""The app carries a complete wheel-produced frontend identity record."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	dist_info = app_path / "Contents" / "Resources" / build_qt_app._expected_dist_info_name(plan, "26.07")
	if metadata_failure == "missing_record":
		(dist_info / "RECORD").unlink()
	elif metadata_failure == "wrong_name":
		(dist_info / "METADATA").write_text("Name: other-project\nVersion: 26.07\n", encoding="utf-8")
	else:
		(dist_info / "METADATA").write_text("Name: bkchem-qt\nVersion: 0.0\n", encoding="utf-8")

	with pytest.raises(RuntimeError, match="Missing|METADATA (Name|Version)"):
		_inspect(plan, app_path, "26.07")


#============================================
def test_post_build_inspection_rejects_wrong_identity_version_and_version_output(
		tmp_path: pathlib.Path,
		) -> None:
	"""Inspection diagnoses malformed metadata and a mismatched frozen version contract."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	info_path = app_path / "Contents" / "Info.plist"
	with info_path.open("wb") as info_file:
		plistlib.dump({"CFBundleIdentifier": "wrong", "CFBundleVersion": "26.07"}, info_file)

	with pytest.raises(RuntimeError, match="bundle identifier"):
		_inspect(plan, app_path, "26.07")

	_make_synthetic_bundle(tmp_path / "second", plan, "26.07")
	second_app = tmp_path / "second" / plan.bundle_name
	wrong_output = subprocess.CompletedProcess(("BKChem", "--version"), 0, "BKChem-Qt 0.0\n", "")
	with pytest.raises(RuntimeError, match="version output"):
		_inspect(plan, second_app, "26.07", lambda *_arguments: wrong_output)


#============================================
def test_post_build_inspection_rejects_corrupt_plist_and_timed_out_version_query(
		tmp_path: pathlib.Path,
		) -> None:
	"""Inspection reports malformed metadata and preserves the bounded version failure."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	info_path = app_path / "Contents" / "Info.plist"
	info_path.write_text("not a plist", encoding="utf-8")

	with pytest.raises(RuntimeError, match="Corrupt application Info.plist"):
		_inspect(plan, app_path, "26.07")

	second_app = _make_synthetic_bundle(tmp_path / "second", plan, "26.07")
	def timeout_runner(
			command: tuple[str, ...], _cwd: pathlib.Path, timeout_seconds: float,
			) -> subprocess.CompletedProcess[str]:
		"""Raise the exact bounded subprocess failure expected by the inspection seam."""
		raise subprocess.TimeoutExpired(command, timeout_seconds)

	with pytest.raises(RuntimeError, match="version check timed out"):
		_inspect(plan, second_app, "26.07", timeout_runner)


#============================================
def test_post_build_inspection_rejects_unexpected_app_path_and_failed_version_query(
		tmp_path: pathlib.Path,
		) -> None:
	"""Inspection reports invalid plan paths and nonzero frozen-version queries."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")
	wrong_app = app_path.with_name("Other.app")
	app_path.rename(wrong_app)

	with pytest.raises(RuntimeError, match="Unexpected macOS app bundle path"):
		_inspect(plan, wrong_app, "26.07")
	wrong_app.rename(app_path)

	failed_result = subprocess.CompletedProcess(("BKChem", "--version"), 1, "", "missing metadata")
	with pytest.raises(RuntimeError, match="version check failed"):
		_inspect(plan, app_path, "26.07", lambda *_arguments: failed_result)


#============================================
def test_post_build_smoke_starts_only_after_successful_inspection(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
		) -> None:
	"""A rejected post-build inspection prevents the timer-backed smoke command."""
	plan = qt_bundle_plan.make_qt_bundle_plan(REPO_ROOT)
	smoke_calls: list[tuple[str, ...]] = []

	def reject_inspection(*_arguments: object) -> None:
		"""Raise the post-build failure used to prove smoke gating."""
		raise RuntimeError("inspection failed")

	def record_smoke(
			command: tuple[str, ...], _cwd: pathlib.Path, _timeout: float,
			) -> subprocess.CompletedProcess[str]:
		"""Record a smoke command if the builder reaches the smoke phase."""
		smoke_calls.append(command)
		return subprocess.CompletedProcess(command, 0, "", "")

	monkeypatch.setattr(build_qt_app, "inspect_built_app", reject_inspection)
	app_path = _make_synthetic_bundle(tmp_path, plan, "26.07")

	with pytest.raises(RuntimeError, match="inspection failed"):
		build_qt_app.run_post_build_checks(
			plan, app_path, _release("26.07"), "26.7.1", 2.0, tmp_path / "smoke", tmp_path,
			tmp_path, record_smoke,
		)

	assert smoke_calls == []
