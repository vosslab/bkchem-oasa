#!/usr/bin/env python3

"""GUI smoke test for BKChem."""

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
	parser = argparse.ArgumentParser(description="Open BKChem GUI briefly.")
	parser.add_argument(
		'-s', '--seconds',
		dest='seconds',
		type=float,
		default=2.0,
		help='Seconds to keep the GUI open'
	)
	args = parser.parse_args()
	return args


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
def main():
	"""Run the GUI smoke test."""
	args = parse_args()
	root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	if root_dir not in sys.path:
		sys.path.insert(0, root_dir)
	bkchem_dir = os.path.join(root_dir, 'packages', 'bkchem')
	if bkchem_dir not in sys.path:
		sys.path.insert(0, bkchem_dir)
	bkchem_pkg_dir = os.path.join(bkchem_dir, 'bkchem')
	if bkchem_pkg_dir not in sys.path:
		sys.path.append(bkchem_pkg_dir)
	if '_' not in builtins.__dict__:
		builtins.__dict__['_'] = lambda m: m
	if 'ngettext' not in builtins.__dict__:
		builtins.__dict__['ngettext'] = lambda s, p, n: s if n == 1 else p
	try:
		import tkinter
	except ModuleNotFoundError as exc:
		if exc.name == '_tkinter' or exc.name == 'tkinter':
			sys.stderr.write(
				"tkinter is not available. Install a Python build with Tk support "
				"(tcl/tk) and rerun this test.\n"
			)
			sys.exit(1)
		raise
	tkinter.TkVersion
	ensure_preferences()
	import bkchem.main as bkchem_main
	BKChem = bkchem_main.BKChem
	app = BKChem()
	app.withdraw()
	app.initialize()
	if not getattr(app, 'paper', None):
		raise RuntimeError("BKChem GUI smoke test failed to create a paper.")
	app.deiconify()
	app.after(int(args.seconds * 1000), app.destroy)
	app.mainloop()
	print("BKChem GUI smoke test OK.")


if __name__ == '__main__':
	main()
