#!/usr/bin/env python3

"""Plugin smoke test for BKChem."""

import argparse
import builtins
import importlib
import os
import sys
import tempfile
import traceback


#============================================
def parse_args():
	"""Parse command-line arguments.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Import BKChem plugins and report loaded modules."
	)
	parser.add_argument(
		'--debug',
		action='store_true',
		help='Print full tracebacks for plugin import failures'
	)
	parser.add_argument(
		'--summary',
		action='store_true',
		help='Print only the one-line plugin summary'
	)
	parser.add_argument(
		'--export',
		action='store_true',
		help='Export a sample molecule and report file sizes'
	)
	parser.add_argument(
		'-i', '--input',
		dest='input_file',
		default=None,
		help='CDML file to open for export checks'
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
def load_plugins(plugin_names, debug=False):
	"""Load BKChem plugins by name.

	Args:
		plugin_names (list[str]): Plugin module names.
		debug (bool): True to print tracebacks for failures.

	Returns:
		tuple[list[str], list[tuple[str, Exception]]]: Loaded names and failures.
	"""
	loaded = []
	plugin_info = {}
	failures = []
	for name in plugin_names:
		try:
			module = importlib.import_module(f"bkchem.plugins.{name}")
			loaded.append(name)
			plugin_info[name] = describe_plugin(module)
		except Exception as exc:
			failures.append((name, exc))
			if debug:
				traceback.print_exc()
	return loaded, plugin_info, failures


#============================================
def prepare_app(input_path):
	"""Create a BKChem app and load a file for export checks."""
	import bkchem.main

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize_batch()
	if not getattr(app, 'paper', None):
		raise RuntimeError("BKChem plugin smoke test failed to create a paper.")
	if not app.load_CDML(input_path, replace=1):
		raise RuntimeError(f"BKChem plugin smoke test failed to load {input_path}.")
	if not app.paper.molecules:
		raise RuntimeError("BKChem plugin smoke test found no molecules to export.")
	app.paper.unselect_all()
	if app.paper.molecules[0].atoms:
		app.paper.select([app.paper.molecules[0].atoms[0]])
	return app


#============================================
def export_plugins(app, plugins, output_dir):
	"""Export using available exporters and report sizes."""
	results = []
	for plugin_name in plugins:
		module = plugins[plugin_name]
		exporter_cls = getattr(module, "exporter", None)
		if not exporter_cls:
			continue
		if module.__name__.endswith(".inchi"):
			from singleton_store import Store
			if not Store.pm.get_preference("inchi_program_path"):
				results.append({
					"name": module.name,
					"status": "skipped",
					"reason": "missing inchi_program_path",
				})
				continue
		extension = ""
		extensions = getattr(module, "extensions", []) or []
		if extensions:
			extension = extensions[0]
		filename = os.path.join(
			output_dir,
			f"bkchem_plugin_{module.name.lower()}{extension}"
		)
		exporter = exporter_cls(app.paper)
		exporter.interactive = False
		if not exporter.on_begin():
			results.append({
				"name": module.name,
				"status": "skipped",
				"reason": "exporter.on_begin returned False",
			})
			continue
		try:
			exporter.write_to_file(filename)
		except Exception as exc:
			results.append({
				"name": module.name,
				"status": "failed",
				"reason": f"{exc.__class__.__name__}: {exc}",
			})
			continue
		size = os.path.getsize(filename) if os.path.exists(filename) else 0
		results.append({
			"name": module.name,
			"status": "ok",
			"file": filename,
			"size": size,
		})
	return results


#============================================
def describe_plugin(module):
	"""Extract metadata from a plugin module."""
	name = getattr(module, "name", module.__name__)
	local_name = getattr(module, "local_name", name)
	extensions = getattr(module, "extensions", []) or []
	importer = getattr(module, "importer", None)
	exporter = getattr(module, "exporter", None)
	modes = []
	if importer:
		modes.append("import")
	if exporter:
		modes.append("export")
	import_doc = None
	export_doc = None
	if importer:
		import_doc = getattr(importer, "doc_string", None) or getattr(importer, "__doc__", None)
	if exporter:
		export_doc = getattr(exporter, "doc_string", None) or getattr(exporter, "__doc__", None)
	return {
		"name": name,
		"local_name": local_name,
		"extensions": extensions,
		"modes": modes,
		"import_doc": _cleanup_doc(import_doc),
		"export_doc": _cleanup_doc(export_doc),
	}


#============================================
def _cleanup_doc(doc):
	"""Normalize doc strings for single-line output."""
	if not doc:
		return None
	return " ".join(str(doc).split())


#============================================
def main():
	"""Run the plugin smoke test."""
	args = parse_args()
	root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	ensure_sys_path(root_dir)
	ensure_gettext_fallbacks()
	if args.export:
		verify_tkinter()
		ensure_preferences()
	plugin_names = [
		"gtml",
	]
	loaded, plugin_info, failures = load_plugins(plugin_names, debug=args.debug)
	loaded_line = ", ".join(loaded) if loaded else "none"
	print(f"Loaded plugins ({len(loaded)}): {loaded_line}")
	if not args.summary:
		for name in plugin_names:
			info = plugin_info.get(name)
			if not info:
				continue
			modes = ", ".join(info["modes"]) if info["modes"] else "unknown"
			extensions = ", ".join(info["extensions"]) if info["extensions"] else "n/a"
			print(f"{info['name']}: {modes} [{extensions}]")
			if info["import_doc"]:
				print(f"  import: {info['import_doc']}")
			if info["export_doc"]:
				print(f"  export: {info['export_doc']}")
	if failures:
		for name, exc in failures:
			sys.stderr.write(
				f"Plugin load failed: {name}: {exc.__class__.__name__}: {exc}\n"
			)
		return 1
	if args.export:
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
		app = prepare_app(input_path)
		with tempfile.TemporaryDirectory() as output_dir:
			results = export_plugins(app, plugin_info, output_dir)
			if results:
				print("Export check results:")
				for result in results:
					if result["status"] == "ok":
						print(
							f"{result['name']}: {result['size']} bytes -> {result['file']}"
						)
					elif result["status"] == "skipped":
						print(f"{result['name']}: skipped ({result['reason']})")
					else:
						print(f"{result['name']}: failed ({result['reason']})")
			else:
				print("Export check results: no exporters found.")
		app.destroy()
	print("BKChem plugin smoke test OK.")
	return 0


if __name__ == '__main__':
	sys.exit(main())
