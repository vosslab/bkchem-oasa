#!/usr/bin/env python3

"""Run the legacy batch script examples against a sample file."""

# Standard Library
import argparse
import builtins
import os
import shutil
import sys
import tempfile


#============================================
def parse_args():
	"""Parse command-line arguments.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Run BKChem batch script examples against a temporary CDML file."
	)
	parser.add_argument(
		'-i', '--input',
		dest='input_file',
		default=None,
		help='Input CDML file to copy into a temp workspace'
	)
	args = parser.parse_args()
	return args


#============================================
def ensure_sys_path(root_dir):
	"""Ensure BKChem package paths are on sys.path."""
	bkchem_pkg_dir = os.path.join(root_dir, 'packages', 'bkchem')
	if bkchem_pkg_dir not in sys.path:
		sys.path.insert(0, bkchem_pkg_dir)
	bkchem_module_dir = os.path.join(bkchem_pkg_dir, 'bkchem')
	if bkchem_module_dir not in sys.path:
		sys.path.append(bkchem_module_dir)


#============================================
def ensure_gettext_fallbacks():
	"""Ensure gettext helpers exist for module-level strings."""
	if '_' not in builtins.__dict__:
		builtins.__dict__['_'] = lambda m: m
	if 'ngettext' not in builtins.__dict__:
		builtins.__dict__['ngettext'] = lambda s, p, n: s if n == 1 else p


#============================================
def verify_tkinter():
	"""Verify Tk is available for GUI-backed scripts."""
	try:
		import tkinter
	except ModuleNotFoundError as exc:
		if exc.name in ('_tkinter', 'tkinter'):
			raise RuntimeError(
				"tkinter is not available. Install a Python build with Tk support "
				"(tcl/tk) and rerun this test."
			) from exc
		raise
	tkinter.TkVersion


#============================================
def ensure_preferences():
	"""Initialize preference manager for tests."""
	import os_support
	import pref_manager
	import singleton_store

	if singleton_store.Store.pm is None:
		singleton_store.Store.pm = pref_manager.pref_manager([
			os_support.get_config_filename("prefs.xml", level="global", mode='r'),
			os_support.get_config_filename("prefs.xml", level="personal", mode='r'),
		])


#============================================
#============================================
def run_batch_demo(input_path):
	"""Run a batch-mode update similar to the legacy demo script."""
	import bkchem.main

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize_batch()
	if not getattr(app, 'paper', None):
		raise RuntimeError("BKChem batch example failed to create a paper.")
	if app.load_CDML(input_path, replace=1):
		for mol in app.paper.molecules:
			for atom in mol.atoms:
				atom.font_size = 12
		app.save_CDML()
	app.destroy()


#============================================
def run_script1(input_path):
	"""Run a batch-style update similar to the legacy script1."""
	import bkchem.main

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize_batch()
	if not getattr(app, 'paper', None):
		raise RuntimeError("BKChem script1 example failed to create a paper.")
	if app.load_CDML(input_path, replace=1):
		for mol in app.paper.molecules:
			for bond in mol.bonds:
				if bond.order == 2:
					bond.line_color = "#aa0000"
					bond.redraw()
		app.update_idletasks()
		app.save_CDML()
	app.destroy()


#============================================
def main():
	"""Run batch script examples on a temporary CDML copy."""
	args = parse_args()
	root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	ensure_sys_path(root_dir)
	ensure_gettext_fallbacks()
	verify_tkinter()
	ensure_preferences()

	default_input = os.path.join(
		root_dir,
		'packages',
		'bkchem',
		'bkchem_data',
		'templates',
		'templates.cdml'
	)
	input_path = args.input_file or default_input
	if not os.path.isfile(input_path):
		raise FileNotFoundError(f"Input file does not exist: {input_path}")

	with tempfile.TemporaryDirectory() as temp_dir:
		temp_input = os.path.join(temp_dir, os.path.basename(input_path))
		shutil.copy2(input_path, temp_input)

		run_batch_demo(temp_input)
		run_script1(temp_input)

		if not os.path.isfile(temp_input):
			raise RuntimeError("BKChem batch examples did not preserve the input file.")
		if os.path.getsize(temp_input) == 0:
			raise RuntimeError("BKChem batch examples wrote an empty output file.")
		print("BKChem batch examples OK.")


if __name__ == '__main__':
	main()
