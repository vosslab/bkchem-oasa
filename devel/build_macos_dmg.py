#!/usr/bin/env python3

"""Build a macOS .dmg installer for BKChem.

Produces a self-contained BKChem.app bundle with embedded Python 3.12,
Tcl/Tk, all pip dependencies, oasa, and all data files, then wraps
it in a BKChem-VERSION.dmg disk image.
"""

# Standard Library
import os
import sys
import shutil
import pathlib
import plistlib
import argparse
import tempfile
import subprocess

# PIP3 modules
import rich.console

console = rich.console.Console()
error_console = rich.console.Console(stderr=True)

#============================================

def print_step(message: str) -> None:
	"""Print a step header in cyan.

	Args:
		message: The step message to print.
	"""
	console.print(message, style="bold cyan")

#============================================

def print_info(message: str) -> None:
	"""Print a normal info message.

	Args:
		message: The info message to print.
	"""
	console.print(message)

#============================================

def print_warning(message: str) -> None:
	"""Print a warning message in yellow.

	Args:
		message: The warning message to print.
	"""
	console.print(message, style="yellow")

#============================================

def print_error(message: str) -> None:
	"""Print an error message in red to stderr.

	Args:
		message: The error message to print.
	"""
	error_console.print(message, style="bold red")

#============================================

def fail(message: str) -> None:
	"""Print an error and exit.

	Args:
		message: The error message to print.
	"""
	print_error(message)
	raise SystemExit(1)

#============================================

def run_command(args: list, cwd: str, capture: bool) -> subprocess.CompletedProcess:
	"""Run a command and fail on error.

	Args:
		args: Command arguments.
		cwd: Working directory.
		capture: Whether to capture output.

	Returns:
		The completed process.
	"""
	result = subprocess.run(
		args,
		cwd=cwd,
		text=True,
		capture_output=capture,
	)
	if result.returncode != 0:
		command_text = " ".join(str(a) for a in args)
		stderr_text = ""
		if capture and result.stderr:
			stderr_text = f"\n{result.stderr}"
		fail(f"Command failed: {command_text}{stderr_text}")
	return result

#============================================

def run_command_allow_fail(args: list, cwd: str, capture: bool) -> subprocess.CompletedProcess:
	"""Run a command and return the result, even if it fails.

	Args:
		args: Command arguments.
		cwd: Working directory.
		capture: Whether to capture output.

	Returns:
		The completed process.
	"""
	result = subprocess.run(
		args,
		cwd=cwd,
		text=True,
		capture_output=capture,
	)
	return result

#============================================

def format_bytes(size_bytes: int) -> str:
	"""Format byte counts for human-readable output.

	Args:
		size_bytes: Size in bytes.

	Returns:
		The formatted size.
	"""
	size = float(size_bytes)
	units = ["B", "KB", "MB", "GB"]
	unit_index = 0
	while size >= 1024.0 and unit_index < len(units) - 1:
		size = size / 1024.0
		unit_index += 1
	formatted = f"{size:.1f} {units[unit_index]}"
	return formatted

#============================================

def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments.

	Returns:
		The parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Build a macOS .dmg installer for BKChem.",
	)

	output_group = parser.add_argument_group("output")
	output_group.add_argument(
		"-o", "--output",
		dest="output_dir",
		default="dist",
		help="Output directory for the .app and .dmg (default: dist).",
	)

	behavior_group = parser.add_argument_group("behavior")
	behavior_group.add_argument(
		"-n", "--dry-run",
		dest="dry_run",
		action="store_true",
		help="Preview the build steps without executing them.",
	)

	args = parser.parse_args()
	return args

#============================================

def resolve_repo_root() -> str:
	"""Resolve the repository root using git.

	Returns:
		Absolute path to the repo root.
	"""
	# use git rev-parse per REPO_STYLE.md
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
	)
	if result.returncode == 0 and result.stdout.strip():
		repo_root = result.stdout.strip()
		return repo_root
	# fallback: parent of this script
	repo_root = str(pathlib.Path(__file__).resolve().parents[1])
	return repo_root

#============================================

def read_version(repo_root: str) -> str:
	"""Read the version string from the VERSION file.

	Args:
		repo_root: Path to the repository root.

	Returns:
		The version string (e.g. '26.02').
	"""
	version_path = os.path.join(repo_root, "VERSION")
	if not os.path.isfile(version_path):
		fail(f"VERSION file not found: {version_path}")
	with open(version_path, "r") as handle:
		for line in handle:
			text = line.strip()
			if not text or text.startswith("#"):
				continue
			if "=" not in text:
				continue
			name, value = [part.strip() for part in text.split("=", 1)]
			if name.lower() == "version" and value:
				return value
	fail(f"No version= line found in {version_path}")
	# unreachable but satisfies type checker
	return ""

#============================================

def require_pyinstaller() -> None:
	"""Check that PyInstaller is importable, print install hint if not."""
	result = subprocess.run(
		[sys.executable, "-c", "import PyInstaller"],
		capture_output=True,
		text=True,
	)
	if result.returncode != 0:
		fail(
			"PyInstaller is not installed. Install it with:\n"
			"  pip3 install pyinstaller\n"
			"  or: pip3 install -r pip_requirements-dev.txt"
		)

#============================================

def generate_icns(repo_root: str, dry_run: bool) -> str:
	"""Generate a .icns icon file from the SVG source.

	Renders bkchem.svg via rsvg-convert at required sizes, then
	uses iconutil to produce the .icns file.

	Args:
		repo_root: Path to the repository root.
		dry_run: If True, only preview the steps.

	Returns:
		Path to the generated .icns file.
	"""
	svg_path = os.path.join(
		repo_root, "packages", "bkchem", "bkchem_data", "images", "bkchem.svg"
	)
	if not os.path.isfile(svg_path):
		fail(f"SVG icon not found: {svg_path}")

	# output .icns alongside the SVG for reuse
	icns_path = os.path.join(
		repo_root, "packages", "bkchem", "bkchem_data", "images", "bkchem.icns"
	)

	# check for rsvg-convert
	if not shutil.which("rsvg-convert"):
		fail(
			"rsvg-convert not found. Install it with:\n"
			"  brew install librsvg"
		)

	print_step("Generating .icns icon from SVG...")

	if dry_run:
		print_info(f"  [dry-run] Would render {svg_path} to iconset and .icns")
		return icns_path

	# create temporary iconset directory
	with tempfile.TemporaryDirectory(prefix="bkchem_icon_") as temp_dir:
		iconset_dir = os.path.join(temp_dir, "bkchem.iconset")
		os.makedirs(iconset_dir)

		# Apple iconset sizes: standard and @2x Retina variants
		# icon_16x16.png (16), icon_16x16@2x.png (32),
		# icon_32x32.png (32), icon_32x32@2x.png (64),
		# icon_128x128.png (128), icon_128x128@2x.png (256),
		# icon_256x256.png (256), icon_256x256@2x.png (512),
		# icon_512x512.png (512), icon_512x512@2x.png (1024)
		icon_specs = [
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
		]

		for filename, size in icon_specs:
			output_path = os.path.join(iconset_dir, filename)
			run_command(
				[
					"rsvg-convert",
					"-w", str(size),
					"-h", str(size),
					svg_path,
					"-o", output_path,
				],
				cwd=repo_root,
				capture=True,
			)
			print_info(f"  Rendered {filename} ({size}x{size})")

		# convert iconset to icns
		run_command(
			["iconutil", "-c", "icns", iconset_dir, "-o", icns_path],
			cwd=repo_root,
			capture=True,
		)

	print_info(f"  Icon saved: {icns_path}")
	return icns_path

#============================================

def _write_bootstrap_script(temp_dir: str) -> str:
	"""Write the PyInstaller bootstrap entry point script.

	The bootstrap adds the bkchem package directory to sys.path so
	that bare imports in bkchem.py (import os_support, import config,
	from main import BKChem) resolve correctly in the frozen app.

	Args:
		temp_dir: Temporary directory to write the script into.

	Returns:
		Path to the bootstrap script.
	"""
	bootstrap_path = os.path.join(temp_dir, "bkchem_bootstrap.py")
	# write the bootstrap script that fixes sys.path for frozen apps
	lines = [
		"import sys",
		"import os",
		"",
		"if getattr(sys, 'frozen', False):",
		"    bundle_dir = sys._MEIPASS",
		"    bkchem_dir = os.path.join(bundle_dir, 'bkchem')",
		"    if bkchem_dir not in sys.path:",
		"        sys.path.insert(0, bkchem_dir)",
		"",
		"from bkchem.cli import main",
		"main()",
		"",
	]
	content = "\n".join(lines)
	with open(bootstrap_path, "w") as handle:
		handle.write(content)
	return bootstrap_path

#============================================

def build_app(repo_root: str, icns_path: str, output_dir: str, dry_run: bool) -> str:
	"""Build BKChem.app using PyInstaller.

	Args:
		repo_root: Path to the repository root.
		icns_path: Path to the .icns icon file.
		output_dir: Output directory for the built app.
		dry_run: If True, only preview the steps.

	Returns:
		Path to the built .app bundle.
	"""
	print_step("Building BKChem.app with PyInstaller...")

	# resolve data directories
	bkchem_pkg = os.path.join(repo_root, "packages", "bkchem", "bkchem")
	bkchem_data = os.path.join(repo_root, "packages", "bkchem", "bkchem_data")
	addons_dir = os.path.join(repo_root, "packages", "bkchem", "addons")
	oasa_pkg = os.path.join(repo_root, "packages", "oasa", "oasa")
	oasa_data = os.path.join(repo_root, "packages", "oasa", "oasa_data")
	version_file = os.path.join(repo_root, "VERSION")

	# verify all data paths exist
	for label, path in [
		("bkchem package", bkchem_pkg),
		("bkchem_data", bkchem_data),
		("addons", addons_dir),
		("oasa package", oasa_pkg),
		("oasa_data", oasa_data),
		("VERSION", version_file),
	]:
		if not os.path.exists(path):
			fail(f"Required path not found: {label} -> {path}")

	# separator for --add-data is ':' on macOS
	sep = ":"

	# build the PyInstaller command
	with tempfile.TemporaryDirectory(prefix="bkchem_build_") as temp_dir:
		bootstrap_path = _write_bootstrap_script(temp_dir)

		cmd = [
			sys.executable, "-m", "PyInstaller",
			"--name", "BKChem",
			"--windowed",
			"--onedir",
			"--osx-bundle-identifier", "org.bkchem.BKChem",
			# data bundles
			f"--add-data={bkchem_pkg}{sep}bkchem",
			f"--add-data={bkchem_data}{sep}bkchem_data",
			f"--add-data={addons_dir}{sep}addons",
			f"--add-data={oasa_pkg}{sep}oasa",
			f"--add-data={oasa_data}{sep}oasa_data",
			f"--add-data={version_file}{sep}.",
			# hidden imports for packages PyInstaller may miss
			"--hidden-import=bkchem",
			"--hidden-import=oasa",
			"--hidden-import=defusedxml",
			"--hidden-import=yaml",
			"--hidden-import=cairo",
			# collect-all for tricky packages
			"--collect-all=cairo",
			# output directories
			"--distpath", output_dir,
			"--workpath", os.path.join(output_dir, "build_temp"),
			"--specpath", os.path.join(output_dir, "build_temp"),
			# clean build
			"--clean",
			"--noconfirm",
		]

		# add icon if it exists
		if os.path.isfile(icns_path):
			cmd.append(f"--icon={icns_path}")

		# entry point
		cmd.append(bootstrap_path)

		if dry_run:
			# show the command that would be run
			cmd_text = " \\\n    ".join(str(c) for c in cmd)
			print_info(f"  [dry-run] Would run:\n    {cmd_text}")
			app_path = os.path.join(output_dir, "BKChem.app")
			return app_path

		print_info("  Running PyInstaller (this may take a few minutes)...")
		run_command(cmd, cwd=repo_root, capture=False)

	app_path = os.path.join(output_dir, "BKChem.app")
	# PyInstaller --onedir with --windowed puts the .app in distpath
	if not os.path.isdir(app_path):
		# check inside a BKChem subfolder
		alt_path = os.path.join(output_dir, "BKChem", "BKChem.app")
		if os.path.isdir(alt_path):
			# move it up to output_dir
			shutil.move(alt_path, app_path)
		else:
			fail(f"BKChem.app not found at {app_path} or {alt_path}")

	print_info(f"  App bundle: {app_path}")
	return app_path

#============================================

def patch_info_plist(app_path: str, version: str, dry_run: bool) -> None:
	"""Patch the Info.plist in the app bundle with BKChem metadata.

	Args:
		app_path: Path to the .app bundle.
		version: Version string to embed.
		dry_run: If True, only preview the steps.
	"""
	print_step("Patching Info.plist...")

	plist_path = os.path.join(app_path, "Contents", "Info.plist")

	if dry_run:
		print_info(f"  [dry-run] Would patch {plist_path}")
		return

	if not os.path.isfile(plist_path):
		print_warning(f"  Info.plist not found at {plist_path}, skipping patch.")
		return

	with open(plist_path, "rb") as handle:
		plist_data = plistlib.load(handle)

	# set BKChem metadata
	plist_data["CFBundleName"] = "BKChem"
	plist_data["CFBundleDisplayName"] = "BKChem"
	plist_data["CFBundleVersion"] = version
	plist_data["CFBundleShortVersionString"] = version
	plist_data["CFBundleIdentifier"] = "org.bkchem.BKChem"
	plist_data["NSHighResolutionCapable"] = True
	plist_data["LSMinimumSystemVersion"] = "11.0"

	# associate .cdml files with BKChem
	plist_data["CFBundleDocumentTypes"] = [
		{
			"CFBundleTypeName": "BKChem Document",
			"CFBundleTypeExtensions": ["cdml", "cdgz"],
			"CFBundleTypeRole": "Editor",
			"LSHandlerRank": "Owner",
		},
	]

	with open(plist_path, "wb") as handle:
		plistlib.dump(plist_data, handle)

	print_info(f"  Patched: version={version}, bundle ID=org.bkchem.BKChem")

#============================================

def verify_app_bundle(app_path: str, version: str, dry_run: bool) -> None:
	"""Run post-build verification checks on the app bundle.

	Args:
		app_path: Path to the .app bundle.
		version: Expected version string.
		dry_run: If True, only preview the steps.
	"""
	print_step("Verifying app bundle...")

	if dry_run:
		print_info("  [dry-run] Would verify app bundle contents.")
		return

	# check that the main executable exists and is executable
	exe_path = os.path.join(app_path, "Contents", "MacOS", "BKChem")
	if not os.path.isfile(exe_path):
		fail(f"  Executable not found: {exe_path}")
	if not os.access(exe_path, os.X_OK):
		fail(f"  Executable not runnable: {exe_path}")
	print_info("  [OK] Main executable exists and is executable")

	# check Info.plist has correct bundle ID and version
	plist_path = os.path.join(app_path, "Contents", "Info.plist")
	if os.path.isfile(plist_path):
		with open(plist_path, "rb") as handle:
			plist_data = plistlib.load(handle)
		bundle_id = plist_data.get("CFBundleIdentifier", "")
		bundle_version = plist_data.get("CFBundleVersion", "")
		if bundle_id != "org.bkchem.BKChem":
			print_warning(f"  Bundle ID mismatch: {bundle_id}")
		else:
			print_info("  [OK] Bundle ID: org.bkchem.BKChem")
		if bundle_version != version:
			print_warning(f"  Version mismatch: {bundle_version} != {version}")
		else:
			print_info(f"  [OK] Version: {version}")
	else:
		print_warning("  Info.plist not found, skipping plist checks.")

	# check for bundled data directories
	# PyInstaller --onedir puts resources in Contents/Frameworks/ or Contents/Resources/
	frameworks_dir = os.path.join(app_path, "Contents", "Frameworks")
	resources_dir = os.path.join(app_path, "Contents", "Resources")
	# look for data dirs in either location
	search_dirs = []
	if os.path.isdir(frameworks_dir):
		search_dirs.append(frameworks_dir)
	if os.path.isdir(resources_dir):
		search_dirs.append(resources_dir)

	data_dirs_to_check = ["bkchem_data", "oasa_data", "addons"]
	for data_dir_name in data_dirs_to_check:
		found = False
		for search_dir in search_dirs:
			candidate = os.path.join(search_dir, data_dir_name)
			if os.path.isdir(candidate):
				found = True
				break
			# also check one level deeper (inside _internal for onedir)
			for sub in os.listdir(search_dir):
				deep_candidate = os.path.join(search_dir, sub, data_dir_name)
				if os.path.isdir(deep_candidate):
					found = True
					break
			if found:
				break
		if found:
			print_info(f"  [OK] Data directory present: {data_dir_name}")
		else:
			print_warning(f"  Data directory not found in bundle: {data_dir_name}")

	# check for Tcl/Tk libraries
	tcl_found = False
	for search_dir in search_dirs:
		for root, dirs, files in os.walk(search_dir):
			for dirname in dirs:
				if dirname.startswith("tcl") and dirname[3:4].isdigit():
					tcl_found = True
					break
			if tcl_found:
				break
		if tcl_found:
			break
	if tcl_found:
		print_info("  [OK] Tcl/Tk libraries present")
	else:
		print_warning("  Tcl/Tk libraries not detected in bundle")

	# check for libcairo
	cairo_found = False
	for search_dir in search_dirs:
		for root, dirs, files in os.walk(search_dir):
			for filename in files:
				if "libcairo" in filename and filename.endswith(".dylib"):
					cairo_found = True
					break
			if cairo_found:
				break
		if cairo_found:
			break
	if cairo_found:
		print_info("  [OK] libcairo dylib present")
	else:
		print_warning("  libcairo dylib not detected in bundle")

	# print bundle size
	total_size = 0
	for root, dirs, files in os.walk(app_path):
		for filename in files:
			file_path = os.path.join(root, filename)
			total_size += os.path.getsize(file_path)
	print_info(f"  Bundle size: {format_bytes(total_size)}")

#============================================

def create_dmg(app_path: str, version: str, output_dir: str, dry_run: bool) -> str:
	"""Create a .dmg disk image from the app bundle.

	Creates a compressed DMG with the app and an Applications symlink
	for drag-and-drop installation.

	Args:
		app_path: Path to the .app bundle.
		version: Version string for the DMG name.
		output_dir: Directory to place the DMG.
		dry_run: If True, only preview the steps.

	Returns:
		Path to the created .dmg file.
	"""
	print_step("Creating .dmg disk image...")

	dmg_name = f"BKChem-{version}.dmg"
	dmg_path = os.path.join(output_dir, dmg_name)

	if dry_run:
		print_info(f"  [dry-run] Would create {dmg_path}")
		return dmg_path

	with tempfile.TemporaryDirectory(prefix="bkchem_dmg_") as staging_dir:
		# copy app bundle into staging area
		staged_app = os.path.join(staging_dir, "BKChem.app")
		shutil.copytree(app_path, staged_app, symlinks=True)

		# create Applications symlink for drag-and-drop install
		apps_link = os.path.join(staging_dir, "Applications")
		os.symlink("/Applications", apps_link)

		# remove existing DMG if present
		if os.path.isfile(dmg_path):
			os.remove(dmg_path)

		# create a temporary read-write DMG first
		temp_dmg = os.path.join(output_dir, "bkchem_temp.dmg")
		if os.path.isfile(temp_dmg):
			os.remove(temp_dmg)

		vol_name = f"BKChem {version}"
		run_command(
			[
				"hdiutil", "create",
				"-volname", vol_name,
				"-srcfolder", staging_dir,
				"-format", "UDRW",
				temp_dmg,
			],
			cwd=output_dir,
			capture=True,
		)

		# convert to compressed read-only DMG
		run_command(
			[
				"hdiutil", "convert",
				temp_dmg,
				"-format", "UDZO",
				"-o", dmg_path,
			],
			cwd=output_dir,
			capture=True,
		)

		# clean up temporary DMG
		if os.path.isfile(temp_dmg):
			os.remove(temp_dmg)

	# print DMG info
	dmg_size = os.path.getsize(dmg_path)
	print_info(f"  DMG created: {dmg_path}")
	print_info(f"  DMG size: {format_bytes(dmg_size)}")

	return dmg_path

#============================================

def main() -> None:
	"""Orchestrate the macOS DMG build process."""
	args = parse_args()
	repo_root = resolve_repo_root()
	version = read_version(repo_root)

	print_step("BKChem macOS DMG Builder")
	print_info(f"  Repo root: {repo_root}")
	print_info(f"  Version: {version}")
	print_info(f"  Output dir: {args.output_dir}")
	print_info(f"  Dry run: {args.dry_run}")

	# resolve output directory as absolute path
	if not os.path.isabs(args.output_dir):
		output_dir = os.path.join(repo_root, args.output_dir)
	else:
		output_dir = args.output_dir

	if not args.dry_run:
		os.makedirs(output_dir, exist_ok=True)

	# pre-checks
	print_step("Pre-checks...")
	if sys.platform != "darwin":
		fail("This script only runs on macOS.")
	if args.dry_run:
		# skip dependency checks in dry-run mode
		result = subprocess.run(
			[sys.executable, "-c", "import PyInstaller"],
			capture_output=True, text=True,
		)
		if result.returncode == 0:
			print_info("  [OK] PyInstaller available")
		else:
			print_warning("  PyInstaller not installed (dry-run continues anyway).")
	else:
		require_pyinstaller()
		print_info("  [OK] PyInstaller available")

	if shutil.which("rsvg-convert"):
		print_info("  [OK] rsvg-convert available")
	else:
		print_warning("  rsvg-convert not found; icon generation will fail.")

	if shutil.which("hdiutil"):
		print_info("  [OK] hdiutil available")
	else:
		print_warning("  hdiutil not found; DMG creation will fail.")

	# step 1: generate .icns icon
	icns_path = generate_icns(repo_root, args.dry_run)

	# step 2: build .app bundle with PyInstaller
	app_path = build_app(repo_root, icns_path, output_dir, args.dry_run)

	# step 3: patch Info.plist
	patch_info_plist(app_path, version, args.dry_run)

	# step 4: verify the app bundle
	verify_app_bundle(app_path, version, args.dry_run)

	# step 5: create .dmg
	dmg_path = create_dmg(app_path, version, output_dir, args.dry_run)
	print_info(f"  DMG at: {dmg_path}")

	# clean up PyInstaller temp files
	build_temp = os.path.join(output_dir, "build_temp")
	if os.path.isdir(build_temp) and not args.dry_run:
		shutil.rmtree(build_temp)
		print_info("  Cleaned up build temp files.")

	# advisory notes
	print_step("Notes")
	print_info("  - This build is arm64 only (Apple Silicon).")
	print_info("  - The app is not code-signed. Users may need to")
	print_info("    right-click > Open on first launch, or run:")
	print_info("    xattr -cr /Applications/BKChem.app")
	print_info("  - Universal binary (arm64+x86_64) is a future enhancement.")

	print_step("Done.")

#============================================

if __name__ == "__main__":
	main()
