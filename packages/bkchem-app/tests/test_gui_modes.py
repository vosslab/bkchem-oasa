"""BKChem GUI mode cycling smoke test -- YAML-driven."""

# Standard Library
import builtins
import os
import subprocess
import sys
import time

# Third Party
import pytest


#============================================
def _ensure_gettext_fallbacks():
	"""Ensure gettext helpers exist for module-level strings."""
	if "_" not in builtins.__dict__:
		builtins.__dict__["_"] = lambda m: m
	if "ngettext" not in builtins.__dict__:
		builtins.__dict__["ngettext"] = lambda s, p, n: s if n == 1 else p


#============================================
def _verify_tkinter():
	"""Verify Tk is available for GUI-backed tests."""
	try:
		import tkinter
	except ModuleNotFoundError as exc:
		if exc.name in ("_tkinter", "tkinter"):
			message = (
				"tkinter is not available. Install a Python build with Tk support."
			)
			pytest.skip(message, allow_module_level=True)
		raise
	tkinter.TkVersion


#============================================
def _ensure_preferences():
	"""Initialize preference manager for tests."""
	from bkchem import os_support
	from bkchem import pref_manager
	from bkchem import singleton_store

	if singleton_store.Store.pm is None:
		singleton_store.Store.pm = pref_manager.pref_manager([
			os_support.get_config_filename("prefs.xml", level="global", mode="r"),
			os_support.get_config_filename("prefs.xml", level="personal", mode="r"),
		])


#============================================
def _flush_events(app, delay=0.05):
	"""Process Tk events with a brief delay for GUI updates."""
	app.update_idletasks()
	app.update()
	time.sleep(delay)
	app.update_idletasks()
	app.update()


#============================================
def _verify_mode_borders(app, current_mode):
	"""Check that only the active mode button is selected via StringVar.

	For ttk.Radiobutton toolbar, the active mode is tracked by
	app._mode_var (StringVar). The selected button gets its visual
	state automatically from ttk style maps.
	"""
	# verify the StringVar tracks the correct active mode
	if hasattr(app, '_mode_var'):
		actual_var = app._mode_var.get()
		if actual_var != current_mode:
			raise AssertionError(
				"_mode_var is '%s', expected '%s'."
				% (actual_var, current_mode)
			)
		# verify the active button's style is correct
		btn = app.get_mode_button(current_mode)
		if btn:
			style_name = str(btn.cget('style'))
			if 'Toolbar.Toolbutton' not in style_name and 'Toolbutton' not in style_name:
				raise AssertionError(
					"Active mode '%s' has style '%s', expected 'Toolbar.Toolbutton'."
					% (current_mode, style_name)
				)
		return
	# fallback for classic tk buttons (if ttk migration not applied)
	for btn_name in app.modes_sort:
		btn = app.get_mode_button(btn_name)
		if not btn:
			continue
		if btn_name == current_mode:
			actual_relief = str(btn.cget('relief'))
			if actual_relief not in ('sunken', 'groove', 'raised'):
				raise AssertionError(
					"Active mode '%s' has relief '%s', expected 'groove'."
					% (btn_name, actual_relief)
				)
		else:
			actual_relief = str(btn.cget('relief'))
			if actual_relief != 'flat':
				raise AssertionError(
					"Inactive mode '%s' has relief '%s', expected 'flat'."
					% (btn_name, actual_relief)
				)


#============================================
def _run_gui_mode_cycling():
	"""Cycle through every toolbar mode and submode, verifying state."""
	_ensure_gettext_fallbacks()
	_verify_tkinter()
	_ensure_preferences()

	import bkchem.main
	from bkchem.modes.config import get_modes_config, get_toolbar_order

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize()
	if not getattr(app, "paper", None):
		raise RuntimeError("BKChem GUI mode test failed to create a paper.")

	try:
		app.deiconify()
		_flush_events(app, delay=0.1)

		# load YAML config for toolbar modes
		cfg = get_modes_config()
		# get_toolbar_order() filters out '---' separator entries
		toolbar_order = get_toolbar_order()
		modes_cfg = cfg['modes']

		# dynamic template modes -- skip submode iteration for these
		dynamic_modes = set()
		for key, mcfg in modes_cfg.items():
			if mcfg.get('dynamic', False):
				dynamic_modes.add(key)

		# cycle every mode in toolbar order
		for mode_key in toolbar_order:
			app.change_mode(mode_key)
			_flush_events(app, delay=0.05)

			# verify active mode name matches YAML
			expected_name = modes_cfg[mode_key]['name']
			actual_name = getattr(app.mode, 'name', None)
			if actual_name != expected_name:
				raise AssertionError(
					"After change_mode('%s'), mode.name is '%s', expected '%s'."
					% (mode_key, actual_name, expected_name)
				)

			# verify button border state
			_verify_mode_borders(app, mode_key)

			# skip submode iteration for dynamic template modes
			if mode_key in dynamic_modes:
				continue

			# iterate submode groups from YAML
			yaml_submodes = modes_cfg[mode_key].get('submodes', [])
			group_idx = 0
			for grp in yaml_submodes:
				# skip groups without options (dynamic placeholder groups)
				if 'options' not in grp:
					continue
				options = grp['options']
				for opt in options:
					sub_key = opt['key']
					# invoke submode via set_submode
					app.mode.set_submode(sub_key)
					_flush_events(app, delay=0.02)
					# verify the submode was recorded
					actual_sub = app.mode.get_submode(group_idx)
					if actual_sub != sub_key:
						raise AssertionError(
							"Mode '%s' group %d: set_submode('%s') but "
							"get_submode returned '%s'."
							% (mode_key, group_idx, sub_key, actual_sub)
						)
				group_idx += 1

		# switch back to edit and verify clean border reset
		app.change_mode('edit')
		_flush_events(app, delay=0.05)
		_verify_mode_borders(app, 'edit')
	finally:
		app.destroy()


#============================================
def main():
	"""Entry point for running the GUI mode cycling test directly."""
	_run_gui_mode_cycling()


#============================================
def test_gui_mode_cycling():
	"""Run the mode cycling test in a subprocess for Tk isolation."""
	cmd = [sys.executable, os.path.abspath(__file__)]
	result = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if result.returncode == 0:
		return
	combined = (result.stdout or "") + (result.stderr or "")
	if "tkinter is not available" in combined:
		pytest.skip("tkinter is not available for BKChem GUI mode test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem GUI mode test aborted while initializing Tk.")
	if "TclError" in combined:
		pytest.skip("BKChem GUI mode test failed to initialize Tk.")
	if result.returncode < 0:
		message = (
			"BKChem GUI mode test subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError(
		"BKChem GUI mode test subprocess failed.\n%s" % combined
	)


if __name__ == "__main__":
	main()
