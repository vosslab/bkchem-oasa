"""Edit menu action registrations for BKChem-Qt."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.io.clipboard_mime
import bkchem_qt.io.export
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _selected_to_svg(app: object) -> None:
	"""Copy selected durable backend content as snapshot-derived SVG."""
	session = getattr(app, "_active_session", None)
	if session is None:
		app.statusBar().showMessage("Copy as SVG requires an active backend session", 3000)
		return
	result = bkchem_qt.io.export.render_session_snapshot(session, "svg", "selection")
	if not result.succeeded:
		app.statusBar().showMessage(result.message, 3000)
		return
	svg_bytes = result.artifact
	clipboard = PySide6.QtWidgets.QApplication.clipboard()
	mime_data = PySide6.QtCore.QMimeData()
	mime_data.setData("image/svg+xml", svg_bytes)
	mime_data.setText(bytes(svg_bytes).decode("utf-8"))
	mime_data.setProperty(
		bkchem_qt.io.clipboard_mime.BKCHEM_OWNED_MIME_PROPERTY, True,
	)
	clipboard.setMimeData(mime_data)
	message = "Selection copied as SVG"
	if result.warnings:
		message += " (%d unsupported persistent object(s) omitted)" % len(result.warnings)
	app.statusBar().showMessage(message, 3000)


#============================================
def register_edit_actions(registry: object, app: object) -> None:
	"""Register all Edit menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# undo last change
	registry.register(MenuAction(
		id='edit.undo',
		label_key='Undo',
		help_key='Revert the last change made',
		accelerator='(C-z)',
		handler=app.on_undo,
		enabled_when=None,
	))

	# redo last undo
	registry.register(MenuAction(
		id='edit.redo',
		label_key='Redo',
		help_key='Revert the last undo action',
		accelerator='(C-S-z)',
		handler=app.on_redo,
		enabled_when=None,
	))

	# predicate: true when the document has selected items
	def has_selection() -> bool:
		return app.document is not None and app.document.has_selection

	# The MainWindow resolves backend navigation before legacy Qt history, so
	# menu actions and toolbar/shortcut handlers share one authority decision.
	def can_undo() -> bool:
		return app.can_undo()

	# The same single decision prevents fallback into mixed history families.
	def can_redo() -> bool:
		return app.can_redo()

	# update undo/redo predicates
	registry.get('edit.undo').enabled_when = can_undo
	registry.get('edit.redo').enabled_when = can_redo

	# cut selected objects to clipboard
	registry.register(MenuAction(
		id='edit.cut',
		label_key='Cut',
		help_key='Copy the selected objects to clipboard and delete them',
		accelerator='(C-k)',
		handler=app.on_cut,
		enabled_when=has_selection,
	))

	# copy selected objects to clipboard
	registry.register(MenuAction(
		id='edit.copy',
		label_key='Copy',
		help_key='Copy the selected objects to clipboard',
		accelerator='(C-c)',
		handler=app.on_copy,
		enabled_when=has_selection,
	))

	# paste clipboard contents onto paper
	def can_paste() -> bool:
		"""Enable Paste only for a current authoritative session and CDML data."""
		return app.can_paste()

	registry.register(MenuAction(
		id='edit.paste',
		label_key='Paste',
		help_key='Paste the content of clipboard to current paper',
		accelerator='(C-v)',
		handler=app.on_paste,
		enabled_when=can_paste,
	))

	# copy selection as SVG to system clipboard
	registry.register(MenuAction(
		id='edit.selected_to_svg',
		label_key='Copy as SVG',
		help_key='Create SVG for the selected objects and place it to the system clipboard',
		accelerator=None,
		handler=lambda: _selected_to_svg(app),
		enabled_when=has_selection,
	))

	# select all objects on the paper
	registry.register(MenuAction(
		id='edit.select_all',
		label_key='Select All',
		help_key='Select everything on the paper',
		accelerator='(C-S-a)',
		handler=app.on_select_all,
		enabled_when=None,
	))
