#!/usr/bin/env python3
"""Convert SVG icon sources to PNG files for BKChem toolbar icons.

Reads all .svg files from the pixmaps source directory and converts
them to square PNG files using rsvg-convert. The PNG files are placed
in the pixmaps output directory where the pixmaps.py loader will
automatically prefer them over legacy GIF files.

Example:
	source source_me.sh && python3 tools/convert_svg_icons.py
	source source_me.sh && python3 tools/convert_svg_icons.py -s 48
"""

# Standard Library
import os
import sys
import glob
import shutil
import argparse
import subprocess


# default icon size in pixels (square)
# slightly larger than the original 24px GIF icons for better
# readability; PNG gives 32-bit RGBA and antialiased SVG edges
DEFAULT_ICON_SIZE = 32


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments.

	Returns:
		argparse.Namespace: parsed arguments
	"""
	parser = argparse.ArgumentParser(
		description="Convert SVG icon sources to PNG files for BKChem toolbar icons.",
	)
	parser.add_argument(
		'-s', '--size', dest='icon_size', type=int, default=DEFAULT_ICON_SIZE,
		help=f"Icon size in pixels, square (default: {DEFAULT_ICON_SIZE})",
	)
	parser.add_argument(
		'-n', '--dry-run', dest='dry_run', action='store_true',
		help="List files that would be converted without writing",
	)
	parser.add_argument(
		'-v', '--verbose', dest='verbose', action='store_true',
		help="Print each conversion as it happens",
	)
	args = parser.parse_args()
	return args


#============================================
def find_rsvg_convert() -> str:
	"""Locate the rsvg-convert binary on the system.

	Returns:
		str: absolute path to rsvg-convert

	Raises:
		FileNotFoundError: if rsvg-convert is not installed
	"""
	path = shutil.which('rsvg-convert')
	if path:
		return path
	# common homebrew location on macOS
	brew_path = '/opt/homebrew/bin/rsvg-convert'
	if os.path.isfile(brew_path):
		return brew_path
	raise FileNotFoundError(
		"rsvg-convert not found. Install it with: brew install librsvg"
	)


#============================================
def get_repo_root() -> str:
	"""Get the repository root directory.

	Returns:
		str: absolute path to repository root
	"""
	result = subprocess.run(
		['git', 'rev-parse', '--show-toplevel'],
		capture_output=True, text=True,
	)
	if result.returncode == 0:
		return result.stdout.strip()
	# fallback: derive from script location
	return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


#============================================
def convert_svg_to_png(
	rsvg_path: str, svg_path: str, png_path: str, size: int
) -> bool:
	"""Convert a single SVG file to PNG using rsvg-convert.

	Args:
		rsvg_path: path to rsvg-convert binary
		svg_path: input SVG file path
		png_path: output PNG file path
		size: icon size in pixels (square)

	Returns:
		bool: True if conversion succeeded
	"""
	result = subprocess.run(
		[rsvg_path, '-w', str(size), '-h', str(size), svg_path, '-o', png_path],
		capture_output=True, text=True,
	)
	if result.returncode != 0:
		print(f"  ERROR converting {os.path.basename(svg_path)}: {result.stderr.strip()}")
		return False
	return True


#============================================
def main():
	"""Convert all SVG icons to PNG files."""
	args = parse_args()

	# locate rsvg-convert
	rsvg_path = find_rsvg_convert()

	# resolve directories
	repo_root = get_repo_root()
	svg_dir = os.path.join(
		repo_root, 'packages', 'bkchem-app', 'bkchem_data', 'pixmaps', 'src',
	)
	png_dir = os.path.join(
		repo_root, 'packages', 'bkchem-app', 'bkchem_data', 'pixmaps',
	)

	if not os.path.isdir(svg_dir):
		print(f"SVG source directory not found: {svg_dir}")
		sys.exit(1)

	# collect all SVG files
	svg_pattern = os.path.join(svg_dir, '*.svg')
	svg_files = sorted(glob.glob(svg_pattern))

	if not svg_files:
		print(f"No SVG files found in {svg_dir}")
		sys.exit(1)

	print(f"Converting {len(svg_files)} SVG icons to {args.icon_size}x{args.icon_size} PNG")
	print(f"  Source: {svg_dir}")
	print(f"  Output: {png_dir}")
	print(f"  Tool:   {rsvg_path}")

	if args.dry_run:
		print("\nDry run -- no files will be written:")
		for svg_path in svg_files:
			name = os.path.splitext(os.path.basename(svg_path))[0]
			print(f"  {name}.svg -> {name}.png")
		return

	# convert each file
	success_count = 0
	error_count = 0
	for svg_path in svg_files:
		name = os.path.splitext(os.path.basename(svg_path))[0]
		png_path = os.path.join(png_dir, name + '.png')
		ok = convert_svg_to_png(rsvg_path, svg_path, png_path, args.icon_size)
		if ok:
			success_count += 1
			if args.verbose:
				print(f"  {name}.svg -> {name}.png")
		else:
			error_count += 1

	print(f"\nDone: {success_count} converted, {error_count} errors")


if __name__ == '__main__':
	main()
