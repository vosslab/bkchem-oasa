"""Command-line interface for BKChem-Qt."""

# Standard Library
import argparse
import sys

# local repo modules
import bkchem_qt.app

# application version
VERSION = "26.02a1"


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments.

	Returns:
		Parsed argument namespace with version flag and file list.
	"""
	parser = argparse.ArgumentParser(
		description="BKChem-Qt - 2D molecular structure editor",
	)
	parser.add_argument(
		'-v', '--version',
		action='version',
		version=f"BKChem-Qt {VERSION}",
	)
	parser.add_argument(
		'files',
		nargs='*',
		help="CDML files to open on launch",
	)
	args = parser.parse_args()
	return args


#============================================
def main() -> None:
	"""Entry point for the BKChem-Qt CLI."""
	args = parse_args()
	exit_code = bkchem_qt.app.main(args.files)
	sys.exit(exit_code)
