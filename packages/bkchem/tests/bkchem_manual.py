#!/usr/bin/env python3

"""Launch BKChem with a sample file for manual testing."""

# Standard Library
import argparse
import builtins
import os
import sys


#============================================
def parse_args():
	"""Parse command-line arguments.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Open BKChem with a sample CDML file for manual testing."
	)
	parser.add_argument(
		'-i', '--input',
		dest='input_file',
		default=None,
		help='CDML file to open in BKChem'
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
def main():
	"""Launch BKChem and keep it open for manual testing."""
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

	import bkchem.main as bkchem_main
	app = bkchem_main.BKChem()
	app.withdraw()
	app.initialize()
	app.load_CDML(input_path, replace=1)
	app.deiconify()
	print("BKChem manual test running. Close the window to exit.")
	app.mainloop()


if __name__ == '__main__':
	main()
