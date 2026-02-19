#!/usr/bin/env python3
"""OASA command-line helpers."""

# Standard Library
import argparse
import importlib.util
import os
import sys


#============================================
OASA_DIR = os.path.abspath(os.path.dirname(__file__))
if OASA_DIR not in sys.path:
	sys.path.insert(0, OASA_DIR)


# local repo modules
from oasa import haworth
from oasa import render_out
from oasa import smiles_lib as smiles


#============================================
DEFAULT_BOND_LENGTH = 30


#============================================
def parse_args(argv=None):
	"""Parse command-line arguments.

	Args:
		argv (list[str] | None): Optional argument list.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="OASA CLI helpers"
	)
	subparsers = parser.add_subparsers(dest="command", required=True)

	haworth_parser = subparsers.add_parser(
		"haworth",
		help="Render Haworth projection from SMILES"
	)
	haworth_parser.add_argument(
		"-s", "--smiles",
		dest="smiles",
		required=True,
		help="SMILES input for Haworth rendering"
	)
	haworth_parser.add_argument(
		"-o", "--output",
		dest="output",
		required=True,
		help="Output file path (.svg or .png)"
	)
	haworth_parser.add_argument(
		"-m", "--mode",
		dest="mode",
		choices=("pyranose", "furanose"),
		default="pyranose",
		help="Ring mode (default: pyranose)"
	)
	haworth_parser.add_argument(
		"-f", "--format",
		dest="format",
		choices=("svg", "png"),
		default=None,
		help="Output format (default: inferred from output path)"
	)
	haworth_parser.add_argument(
		"-d", "--series",
		dest="series",
		choices=("D", "L"),
		default=None,
		help="Sugar series for substituent placement (default: none)"
	)
	haworth_parser.add_argument(
		"-t", "--stereo",
		dest="stereo",
		choices=("alpha", "beta"),
		default=None,
		help="Anomeric stereo for substituent placement (default: none)"
	)
	args = parser.parse_args(argv)
	return args


#============================================
def _resolve_format(output_path, format_override):
	"""Resolve output format from argument or filename.

	Args:
		output_path (str): Output path.
		format_override (str | None): Requested format override.

	Returns:
		str: "svg" or "png".
	"""
	if format_override:
		return format_override
	extension = os.path.splitext(output_path)[1].lower()
	if extension.startswith("."):
		extension = extension[1:]
	if extension in ("svg", "png"):
		return extension
	raise ValueError(
		"Output format could not be determined; use --format svg|png or a .svg/.png filename."
	)


#============================================
def _ensure_parent_dir(output_path):
	"""Create parent directory when needed."""
	parent_dir = os.path.dirname(output_path)
	if not parent_dir:
		return
	if os.path.isdir(parent_dir):
		return
	os.makedirs(parent_dir, exist_ok=True)


#============================================
def _render_haworth(args):
	"""Render a Haworth projection from SMILES and write output.

	Args:
		args (argparse.Namespace): Parsed arguments.

	Returns:
		str: Output path that was written.
	"""
	output_format = _resolve_format(args.output, args.format)
	if output_format == "png":
		if importlib.util.find_spec("cairo") is None:
			raise RuntimeError("PNG output requires pycairo.")

	# Parse SMILES and generate initial coordinates
	mol = smiles.text_to_mol(args.smiles, calc_coords=DEFAULT_BOND_LENGTH)

	# Apply Haworth layout and optional substituent orientation
	haworth.build_haworth(
		mol,
		mode=args.mode,
		bond_length=DEFAULT_BOND_LENGTH,
		series=args.series,
		stereo=args.stereo,
	)

	# Ensure the output directory exists
	_ensure_parent_dir(args.output)

	render_out.mol_to_output(mol, args.output, format=output_format)
	return args.output


#============================================
def main(argv=None):
	"""Run the CLI entry point."""
	args = parse_args(argv)
	if args.command != "haworth":
		raise ValueError("Only the haworth command is supported.")
	output_path = _render_haworth(args)
	print(f"Wrote {output_path}")


if __name__ == "__main__":
	main()
