"""Native-wrapper teardown regression coverage for document sessions."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window

#============================================
def test_closed_tab_releases_its_detached_native_ownership_graph(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A removed tab closes and drains its QObject reaper."""
	assert main_window._on_new()
	closed = main_window.close_session_at(1)
	drained = bkchem_qt.main_window.drain_pending_session_deletions(
		qapp, main_window,
	)

	assert closed
	assert drained
