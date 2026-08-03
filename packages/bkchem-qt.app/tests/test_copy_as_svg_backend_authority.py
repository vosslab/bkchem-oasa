"""Focused authoritative Copy as SVG behavior checks."""

# PIP3 modules
import PySide6.QtWidgets
import lxml.etree

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import oasa.cdml_render


_CDML = """<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
<molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="2cm"/></atom><atom id="a2" name="O"><point x="2cm" y="2cm"/></atom><bond id="b1" start="a1" end="a2" type="n1"/></molecule>
<arrow id="arrow1"><point x="4cm" y="2cm"/><point x="6cm" y="2cm"/></arrow>
<molecule id="m2"><atom id="a3" name="C"><point x="12cm" y="2cm"/></atom><atom id="a4" name="O"><point x="13cm" y="2cm"/></atom><bond id="b2" start="a3" end="a4" type="n1"/></molecule>
</cdml>"""


#============================================
def _native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Install one native projection with separated durable drawable roots."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise RuntimeError("Native CDML projection is unavailable")
	return registered


#============================================
def _clear_selection(session: object) -> None:
	"""Clear only items obtained through the safe captured-scene helper."""
	for item in bkchem_qt.canvas.graphics_retirement.selected_items_from_captured_scene(
		session.scene,
	):
		item.setSelected(False)


#============================================
def _atom_item(session: object, identifier: str) -> object:
	"""Return one projected atom wrapper by its durable backend identifier."""
	for item in session.scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == identifier
		):
			return item
	raise RuntimeError("Durable atom projection is unavailable: %s" % identifier)


#============================================
def _arrow_item(session: object) -> object:
	"""Return the projected durable presentation arrow."""
	for item in session.scene.items():
		model = getattr(item, "document_object_model", None)
		if getattr(model, "object_id", None) == "arrow1":
			return item
	raise RuntimeError("Durable arrow projection is unavailable")


#============================================
def _clipboard_view_box(main_window: bkchem_qt.main_window.MainWindow) -> tuple[float, ...]:
	"""Run the registered action and read its SVG bounds through hardened lxml."""
	main_window._registry.get("edit.selected_to_svg").handler()
	payload = bytes(
		PySide6.QtWidgets.QApplication.clipboard().mimeData().data("image/svg+xml"),
	)
	parser = lxml.etree.XMLParser(
		resolve_entities=False, no_network=True, load_dtd=False,
	)
	root = lxml.etree.fromstring(payload, parser=parser)
	view_box = root.get("viewBox", "").split()
	if len(view_box) != 4:
		raise RuntimeError("Clipboard SVG has no four-value viewBox")
	return tuple(float(value) for value in view_box)


#============================================
def _right_edge(bounds: tuple[float, ...]) -> float:
	"""Return the semantic right edge of one parsed SVG view box."""
	return bounds[0] + bounds[2]


#============================================
def _clipboard_text() -> str:
	"""Return the current plain clipboard payload for failure preservation checks."""
	return PySide6.QtWidgets.QApplication.clipboard().text()


#============================================
def test_copy_as_svg_uses_registered_current_selection_and_backend_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Selected atom exports its molecule while the arrow joins no distant molecule."""
	session = _native_session(main_window)
	try:
		before_snapshot = session.backend_snapshot
		before_document = session.document
		_atom_item(session, "a1").setSelected(True)
		molecule_bounds = _clipboard_view_box(main_window)
		_arrow_item(session).setSelected(True)
		mixed_bounds = _clipboard_view_box(main_window)
		_clear_selection(session)
		_atom_item(session, "a3").setSelected(True)
		distant_bounds = _clipboard_view_box(main_window)

		assert _right_edge(molecule_bounds) < _right_edge(mixed_bounds) < distant_bounds[0]
		assert (
			session.backend_snapshot == before_snapshot
			and session.document is before_document
			and session.backend_projection_synchronized
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_selection_export_requires_reprojection_after_backend_acceptance(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Page export remains snapshot-available when selection projection is stale."""
	session = _native_session(main_window)
	try:
		_atom_item(session, "a1").setSelected(True)
		candidate = session.backend_snapshot.cdml.replace(
			"</cdml>", '<plus id="plus1"><point x="8cm" y="2cm"/></plus></cdml>',
		)
		commit = session.commit_complete_candidate(candidate)
		selection = session.capture_visual_render_request("svg", "selection")
		page = session.capture_visual_render_request("svg", "page")

		assert (
			isinstance(selection, oasa.cdml_render.CDMLRenderFailure)
			and selection.code == "selection-unavailable"
		)
		assert (
			isinstance(page, oasa.cdml_render.CDMLRenderRequest)
			and page.snapshot == commit.snapshot
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_stale_selection_export_preserves_existing_clipboard(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An accepted backend change makes old selected wrappers ineligible to publish."""
	session = _native_session(main_window)
	try:
		_atom_item(session, "a1").setSelected(True)
		candidate = session.backend_snapshot.cdml.replace(
			"</cdml>", '<plus id="plus1"><point x="8cm" y="2cm"/></plus></cdml>',
		)
		session.commit_complete_candidate(candidate)
		PySide6.QtWidgets.QApplication.clipboard().setText("clipboard-before-stale-svg")
		failure = session.capture_visual_render_request("svg", "selection")
		main_window._registry.get("edit.selected_to_svg").handler()

		assert (
			isinstance(failure, oasa.cdml_render.CDMLRenderFailure)
			and failure.code == "selection-unavailable"
		)
		assert _clipboard_text() == "clipboard-before-stale-svg"
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_foreign_selection_export_preserves_existing_clipboard(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A foreign scene item has no authority to publish a visual artifact."""
	session = _native_session(main_window)
	try:
		foreign = PySide6.QtWidgets.QGraphicsRectItem(0, 0, 10, 10)
		foreign.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
		session.scene.addItem(foreign)
		foreign.setSelected(True)
		PySide6.QtWidgets.QApplication.clipboard().setText("clipboard-before-foreign-svg")
		failure = session.capture_visual_render_request("svg", "selection")
		main_window._registry.get("edit.selected_to_svg").handler()

		assert (
			isinstance(failure, oasa.cdml_render.CDMLRenderFailure)
			and failure.code == "selection-unavailable"
		)
		assert _clipboard_text() == "clipboard-before-foreign-svg"
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_unmappable_registered_selection_preserves_existing_clipboard(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A current registered wrapper still needs a durable CDML render key."""
	session = _native_session(main_window)
	try:
		unmappable = PySide6.QtWidgets.QGraphicsRectItem(0, 0, 10, 10)
		unmappable.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
		session.scene.addItem(unmappable)
		session.document.register_current_projection_items((unmappable,))
		unmappable.setSelected(True)
		PySide6.QtWidgets.QApplication.clipboard().setText("clipboard-before-unmappable-svg")
		failure = session.capture_visual_render_request("svg", "selection")
		main_window._registry.get("edit.selected_to_svg").handler()

		assert (
			isinstance(failure, oasa.cdml_render.CDMLRenderFailure)
			and failure.code == "selection-unavailable"
		)
		assert _clipboard_text() == "clipboard-before-unmappable-svg"
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
