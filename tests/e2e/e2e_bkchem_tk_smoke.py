#!/usr/bin/env python3

"""Launch the deprecated retained-Tk application in a bounded native child."""

# Standard Library
import argparse
import builtins
import faulthandler
import pathlib
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BKCHEM_PACKAGE_ROOT = REPO_ROOT / "packages" / "bkchem-app"


#============================================
def _parse_args() -> argparse.Namespace:
	"""Parse the visible lifetime and isolated-process deadline."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--seconds", type=float, default=2.0,
		help="seconds to keep the retained GUI open",
	)
	parser.add_argument(
		"--deadline", type=float, default=15.0,
		help="maximum seconds allowed for the native child",
	)
	parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
	return parser.parse_args()


#============================================
def _ensure_preferences() -> None:
	"""Initialize preferences required by the retained GUI smoke run."""
	import bkchem.os_support
	import bkchem.pref_manager
	import bkchem.singleton_store

	if bkchem.singleton_store.Store.pm is None:
		bkchem.singleton_store.Store.pm = bkchem.pref_manager.pref_manager([
			bkchem.os_support.get_config_filename("prefs.xml", level="global", mode="r"),
			bkchem.os_support.get_config_filename("prefs.xml", level="personal", mode="r"),
		])


#============================================
def _run_native_child(seconds: float) -> None:
	"""Create, initialize, briefly show, and close the retained application."""
	sys.path.insert(0, str(BKCHEM_PACKAGE_ROOT))
	if "_" not in builtins.__dict__:
		builtins.__dict__["_"] = lambda message: message
	if "ngettext" not in builtins.__dict__:
		builtins.__dict__["ngettext"] = (
			lambda singular, plural, count: singular if count == 1 else plural
		)
	try:
		import tkinter
	except ModuleNotFoundError as error:
		if error.name not in ("_tkinter", "tkinter"):
			raise
		raise RuntimeError("Tk support is unavailable for the retained GUI probe") from error
	tkinter.TkVersion
	_ensure_preferences()
	import bkchem.main

	application = bkchem.main.BKChem()
	application.withdraw()
	application.initialize()
	if not getattr(application, "paper", None):
		raise RuntimeError("Retained BKChem did not create a drawing surface")
	application.deiconify()
	application.after(int(seconds * 1000), application.destroy)
	application.mainloop()


#============================================
def main() -> int:
	"""Run the retained GUI in a child that cannot hang the release workflow."""
	args = _parse_args()
	if args.child:
		faulthandler.enable()
		_run_native_child(args.seconds)
		return 0
	command = (
		sys.executable, str(pathlib.Path(__file__).resolve()), "--child",
		"--seconds", str(args.seconds),
	)
	try:
		completed = subprocess.run(
			command, cwd=REPO_ROOT, capture_output=True, text=True,
			timeout=args.deadline, check=False,
		)
	except subprocess.TimeoutExpired:
		sys.stderr.write(
			f"Retained BKChem smoke exceeded its {args.deadline:.1f} second deadline.\n"
		)
		return 1
	if completed.stdout:
		sys.stdout.write(completed.stdout)
	if completed.stderr:
		sys.stderr.write(completed.stderr)
	if completed.returncode:
		if completed.returncode < 0:
			sys.stderr.write(
				"Retained BKChem child terminated by signal "
				f"{abs(completed.returncode)}.\n"
			)
		else:
			sys.stderr.write(
				f"Retained BKChem child exited with status {completed.returncode}.\n"
			)
		return 1
	sys.stdout.write("Retained BKChem GUI smoke OK.\n")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
