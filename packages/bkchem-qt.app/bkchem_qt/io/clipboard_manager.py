"""Clipboard support for complete BKChem top-level CDML objects."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.io.cdml_fragment_builder
import bkchem_qt.io.clipboard_mime


# Custom MIME type for BKChem CDML clipboard data.
CDML_MIME_TYPE = "application/x-bkchem-cdml"

#============================================
class ClipboardManager:
	"""Copy selection and read raw CDML through the Qt clipboard adapter."""

	#============================================
	def copy_selection(self, document: object) -> int:
		"""Copy selected molecules and presentation objects in document order.

		Selection is resolved by ``Document.selected_top_level_objects`` so a
		selected atom, bond, or atom-attached mark means copy its entire owning
		molecule.  The serializer reads original models only; it never reparents
		them into a temporary document.
		"""
		objects = document.selected_top_level_objects
		if not objects:
			return 0
		cdml_text = bkchem_qt.io.cdml_fragment_builder.build_top_level_fragment(
			document, objects,
		)
		object_count = len(objects)
		# ``setMimeData`` can synchronously notify application observers.  Preserve
		# only the completed plain fragment across that native callback boundary so
		# it cannot retain a projection document or selected model wrappers.
		del objects
		del document
		self.publish_fragment(cdml_text)
		return object_count

	#============================================
	def publish_fragment(self, cdml_text: str) -> None:
		"""Publish already-authoritative raw CDML without inspecting a projection."""
		if not isinstance(cdml_text, str):
			raise TypeError("Clipboard CDML fragment must be text")
		clipboard = PySide6.QtWidgets.QApplication.clipboard()
		mime_data = PySide6.QtCore.QMimeData()
		mime_data.setData(
			CDML_MIME_TYPE,
			PySide6.QtCore.QByteArray(cdml_text.encode("utf-8")),
		)
		mime_data.setText(cdml_text)
		mime_data.setProperty(
			bkchem_qt.io.clipboard_mime.BKCHEM_OWNED_MIME_PROPERTY, True,
		)
		clipboard.setMimeData(mime_data)

	#============================================
	def read_fragment(self) -> tuple[str, str | None]:
		"""Read raw CDML once, leaving all validation to the backend."""
		return _read_cdml_from_clipboard()

	#============================================
	def can_paste(self) -> bool:
		"""Return whether the system clipboard appears to contain CDML content."""
		clipboard = PySide6.QtWidgets.QApplication.clipboard()
		mime_data = clipboard.mimeData()
		if mime_data is None:
			return False
		if mime_data.hasFormat(CDML_MIME_TYPE):
			return True
		if mime_data.hasText():
			text = mime_data.text()
			return "<cdml" in text or "<molecule" in text
		return False


#============================================
def _read_cdml_from_clipboard() -> tuple[str, str | None]:
	"""Read custom CDML data first, then a plain-text CDML fallback."""
	clipboard = PySide6.QtWidgets.QApplication.clipboard()
	mime_data = clipboard.mimeData()
	if mime_data is None:
		return ("no_data", None)
	if mime_data.hasFormat(CDML_MIME_TYPE):
		raw = mime_data.data(CDML_MIME_TYPE)
		try:
			cdml_text = bytes(raw).decode("utf-8")
		except UnicodeDecodeError:
			return ("decode_error", None)
		return ("ok", cdml_text)
	if mime_data.hasText():
		text = mime_data.text()
		if "<cdml" in text or "<molecule" in text:
			return ("ok", text)
	return ("no_data", None)


#============================================
