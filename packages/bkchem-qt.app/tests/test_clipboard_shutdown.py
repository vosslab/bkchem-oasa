"""Regression coverage for application-owned clipboard MIME teardown."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.app
import bkchem_qt.io.clipboard_mime
import bkchem_qt.io.clipboard_manager


#============================================
def test_shutdown_cleanup_releases_application_owned_cdml_mime_data(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Marked CDML becomes a safe text-only clipboard value at shutdown."""
	clipboard = qapp.clipboard()
	mime_data = PySide6.QtCore.QMimeData()
	mime_data.setData(
		bkchem_qt.io.clipboard_manager.CDML_MIME_TYPE,
		PySide6.QtCore.QByteArray(b"<cdml/>"),
	)
	mime_data.setText("<cdml/>")
	mime_data.setProperty(
		bkchem_qt.io.clipboard_mime.BKCHEM_OWNED_MIME_PROPERTY, True,
	)
	clipboard.setMimeData(mime_data)
	bkchem_qt.app._clear_application_clipboard(qapp)
	assert (
		clipboard.text(),
		clipboard.mimeData().hasFormat(
			bkchem_qt.io.clipboard_manager.CDML_MIME_TYPE,
		),
	) == ("<cdml/>", False)


#============================================
def test_shutdown_cleanup_leaves_unmarked_clipboard_data_unchanged(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Unmarked clipboard data is outside BKChem's shutdown ownership."""
	clipboard = qapp.clipboard()
	mime_data = PySide6.QtCore.QMimeData()
	mime_data.setText("unrelated clipboard text")
	clipboard.setMimeData(mime_data)
	bkchem_qt.app._clear_application_clipboard(qapp)
	assert clipboard.text() == "unrelated clipboard text"
