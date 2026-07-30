"""Bounded MainWindow shutdown support for direct Qt E2E programs.

These programs run outside pytest's shared fixture teardown.  They therefore
explicitly use the same production session reaper and QObject-deletion
boundaries before their Python process returns.
"""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window


#============================================
def drain_main_window_deletions(
		app: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bool:
	"""Deliver queued terminal work for one live E2E MainWindow."""
	completed = bkchem_qt.main_window.drain_pending_session_deletions(
		app, main_window,
	)
	return completed


#============================================
def shutdown_main_window(
		app: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Close sessions and delete one E2E window through production ownership.

	The caller arranges any expected Save, Discard, or Recovery Export decision
	before this terminal boundary.  The helper then proves that session reaping
	and MainWindow QObject deletion both complete while the Qt application and
	Python wrappers are live.
	"""
	if not main_window.prepare_application_shutdown():
		raise RuntimeError("E2E MainWindow shutdown was not approved")
	main_window.close()
	if not drain_main_window_deletions(app, main_window):
		raise RuntimeError("E2E MainWindow retained pending session deletion")
	if not bkchem_qt.main_window.delete_qobject_and_wait(app, main_window):
		raise RuntimeError("E2E MainWindow QObject deletion was not delivered")
