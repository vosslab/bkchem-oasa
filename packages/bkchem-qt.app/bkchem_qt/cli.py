"""Command-line interface for BKChem-Qt."""

# Standard Library
import argparse
import math
import sys

# local repo modules
import bkchem_qt.versioning


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
		version=f"BKChem-Qt {bkchem_qt.versioning.application_version()}",
	)
	parser.add_argument(
		'--smoke-exit',
		type=float,
		default=None,
		help="Exit normally after this many seconds; used by controlled bundle smoke checks.",
	)
	parser.add_argument(
		'--smoke-receipt',
		default=None,
		help="Write a successful controlled-smoke completion receipt to this path.",
	)
	parser.add_argument(
		'files',
		nargs='*',
		help="Supported chemistry or document files to open on launch",
	)
	args = parser.parse_args()
	if args.smoke_exit is not None and (
		not math.isfinite(args.smoke_exit) or args.smoke_exit <= 0.0
	):
		parser.error("--smoke-exit must be a finite positive number of seconds")
	if args.smoke_receipt is not None and args.smoke_exit is None:
		parser.error("--smoke-receipt requires --smoke-exit")
	return args


#============================================
def main() -> None:
	"""Entry point for the BKChem-Qt CLI."""
	args = parse_args()
	# Import PySide6-dependent startup only after lightweight CLI handling.
	import bkchem_qt.app
	exit_code = bkchem_qt.app.main(args.files, args.smoke_exit, args.smoke_receipt)
	sys.exit(exit_code)
