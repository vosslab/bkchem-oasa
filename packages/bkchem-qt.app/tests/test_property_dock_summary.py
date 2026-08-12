"""Visible document-summary behavior for the Qt Properties dock."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.widgets.property_dock


#============================================
def test_drawing_only_document_is_not_reported_as_empty(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A persistent presentation root appears in the visible document summary."""
	document = bkchem_qt.models.document.Document()
	document.add_presentation_object(
		bkchem_qt.models.document_object.PresentationObject(
			"plus", attributes={"id": "plus-1"},
		),
		mark_dirty=False,
	)
	dock = bkchem_qt.widgets.property_dock.PropertyDock(document)
	try:
		dock.update_from_selection()
		assert "drawing object" in dock.summary_text
	finally:
		dock.set_document(None)
		dock.close()
		assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, dock)
