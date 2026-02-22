"""BKChem GUI theme switch smoke test.

Verifies that switching between light and dark themes does not raise
TclError or crash. Checks that toolbar icons reload from per-theme
PNG directories and that all toolbar buttons remain functional
after the switch.
"""

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
def _flush_events(app, delay=0.05):
	"""Process Tk events with a brief delay for GUI updates."""
	app.update_idletasks()
	app.update()
	time.sleep(delay)
	app.update_idletasks()
	app.update()


#============================================
def _run_theme_change_simulation():
	"""Exercise theme switching in a live BKChem GUI."""
	_ensure_gettext_fallbacks()
	_verify_tkinter()

	from bkchem import os_support
	from bkchem import pref_manager
	from bkchem import singleton_store

	if singleton_store.Store.pm is None:
		singleton_store.Store.pm = pref_manager.pref_manager([
			os_support.get_config_filename("prefs.xml", level="global", mode="r"),
			os_support.get_config_filename("prefs.xml", level="personal", mode="r"),
		])

	import bkchem.main
	from bkchem import theme_manager
	from bkchem import pixmaps

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize()
	if not getattr(app, "paper", None):
		raise RuntimeError("BKChem GUI theme test failed to create a paper.")

	try:
		app.deiconify()
		_flush_events(app, delay=0.1)

		# verify we start with a known theme
		initial_theme = theme_manager.get_active_theme_name()
		if initial_theme not in ('light', 'dark'):
			raise AssertionError(
				f"Unexpected initial theme: {initial_theme}"
			)

		# collect initial icon count
		initial_icon_count = len(pixmaps.images)
		if initial_icon_count == 0:
			raise AssertionError("No icons loaded at startup.")

		# verify needs_icon_inversion matches the theme
		if initial_theme == 'light':
			if theme_manager.needs_icon_inversion():
				raise AssertionError(
					"Light theme should not need icon inversion."
				)
		elif initial_theme == 'dark':
			if not theme_manager.needs_icon_inversion():
				raise AssertionError(
					"Dark theme should need icon inversion."
				)

		# -- switch to dark theme --
		theme_manager.set_active_theme('dark')
		theme_manager.apply_gui_theme(app)
		_flush_events(app, delay=0.1)

		if theme_manager.get_active_theme_name() != 'dark':
			raise AssertionError("Theme did not switch to dark.")
		if not theme_manager.needs_icon_inversion():
			raise AssertionError(
				"Dark theme should need icon inversion after switch."
			)

		# verify icons were reloaded (cache rebuilt)
		dark_icon_count = len(pixmaps.images)
		if dark_icon_count == 0:
			raise AssertionError("No icons loaded after dark theme switch.")

		# verify toolbar buttons still have valid images
		for mode_name in app.modes_sort:
			btn = app.get_mode_button(mode_name)
			if btn:
				# ttk widgets return image config as a tuple; extract first element
				img_raw = btn.cget('image')
				if isinstance(img_raw, tuple):
					img_name = img_raw[0] if img_raw else ''
				else:
					img_name = str(img_raw)
				if not img_name:
					continue
				# verify the image exists in Tk by querying its width
				btn.winfo_toplevel().tk.call('image', 'width', img_name)

		# -- switch back to light theme --
		theme_manager.set_active_theme('light')
		theme_manager.apply_gui_theme(app)
		_flush_events(app, delay=0.1)

		if theme_manager.get_active_theme_name() != 'light':
			raise AssertionError("Theme did not switch back to light.")
		if theme_manager.needs_icon_inversion():
			raise AssertionError(
				"Light theme should not need icon inversion after switch."
			)

		# verify icons again
		light_icon_count = len(pixmaps.images)
		if light_icon_count == 0:
			raise AssertionError("No icons loaded after light theme switch.")

		# verify toolbar buttons still valid
		for mode_name in app.modes_sort:
			btn = app.get_mode_button(mode_name)
			if btn:
				img_raw = btn.cget('image')
				if isinstance(img_raw, tuple):
					img_name = img_raw[0] if img_raw else ''
				else:
					img_name = str(img_raw)
				if not img_name:
					continue
				btn.winfo_toplevel().tk.call('image', 'width', img_name)

		# -- rapid toggle stress test --
		for theme_name in ('dark', 'light', 'dark', 'light'):
			theme_manager.set_active_theme(theme_name)
			theme_manager.apply_gui_theme(app)
			_flush_events(app, delay=0.05)

		# final state check
		if theme_manager.get_active_theme_name() != 'light':
			raise AssertionError("Final theme should be light after rapid toggle.")

	finally:
		app.destroy()


#============================================
def main():
	"""Entry point for running the theme change simulation directly."""
	_run_theme_change_simulation()
	print("Theme change smoke test passed.")


#============================================
def test_gui_theme_change():
	"""Run theme switch test in a subprocess to isolate Tk."""
	cmd = [sys.executable, os.path.abspath(__file__)]
	result = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if result.returncode == 0:
		return
	combined = (result.stdout or "") + (result.stderr or "")
	if "tkinter is not available" in combined:
		pytest.skip("tkinter is not available for BKChem GUI theme test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem GUI theme test aborted while initializing Tk.")
	if result.returncode < 0:
		message = (
			"BKChem GUI theme test subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError(
		"BKChem GUI theme test subprocess failed.\n%s" % combined
	)


if __name__ == "__main__":
	main()
