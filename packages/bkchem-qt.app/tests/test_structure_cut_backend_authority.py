"""Public behavior coverage for backend-authoritative partial structural Cut."""

# Standard Library
import pathlib

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.io.clipboard_manager
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import oasa.cdml_document
import oasa.safe_xml


_CHAIN = """<cdml><molecule id="m1">
<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>
<atom id="a2" name="C"><point x="1cm" y="0cm"/></atom>
<atom id="a3" name="O"><point x="2cm" y="0cm"/></atom>
<bond id="b1" start="a1" end="a2" type="n1"/>
<bond id="b2" start="a2" end="a3" type="n1"/>
</molecule></cdml>"""


#============================================
def _open(main_window: object, tmp_path: pathlib.Path, name: str, cdml: str = _CHAIN) -> object:
	"""Open one native CDML document through the public file action."""
	path = tmp_path / name
	path.write_text(cdml, encoding="utf-8")
	assert main_window.open_file_path(str(path))
	return main_window._active_session


#============================================
def _item(session: object, item_type: type, durable_id: str) -> object:
	"""Find one current atom or bond item by its durable backend identity."""
	attribute = "atom_model" if item_type is bkchem_qt.canvas.items.atom_item.AtomItem else "bond_model"
	return next(
		item for item in session.scene.items()
		if isinstance(item, item_type) and getattr(item, attribute).backend_durable_id == durable_id
	)


#============================================
def _fragment_records(fragment: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
	"""Read one accepted clipboard fragment through the CDML-owned boundary."""
	accepted = oasa.cdml_document.CDMLDocument.parse(fragment, validation="compat")
	root = oasa.safe_xml.parse_dom_from_string(accepted.serialize()).documentElement
	objects = tuple(
		child for child in root.childNodes if child.nodeType == child.ELEMENT_NODE
	)
	molecule = next((child for child in objects if child.localName == "molecule"), None)
	if molecule is None:
		return tuple(child.localName for child in objects), (), ()
	return (
		("molecule",),
		tuple(child.getAttribute("id") for child in molecule.childNodes
			if child.nodeType == child.ELEMENT_NODE and child.localName == "atom"),
		tuple(child.getAttribute("id") for child in molecule.childNodes
			if child.nodeType == child.ELEMENT_NODE and child.localName == "bond"),
	)


#============================================
def _clipboard_fragment() -> str:
	"""Return the public raw CDML payload currently owned by the clipboard."""
	status, fragment = bkchem_qt.io.clipboard_manager.ClipboardManager().read_fragment()
	assert status == "ok" and fragment is not None
	return fragment


#============================================
def _close(main_window: object, session: object, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Release one remaining test tab through the established Qt lifetime reaper."""
	if session in main_window.sessions:
		if main_window.document is session.document:
			main_window._on_new()
		main_window._remove_session(session)


#============================================
def test_atom_and_bond_cut_publish_the_insertable_fragment_before_delete(
		main_window: object, qapp: object, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Atom and bond requests retain distinct clipboard/deletion semantics."""
	atom_origin = _open(main_window, tmp_path, "atom-cut-chain.cdml")
	bond_origin = _open(main_window, tmp_path, "bond-cut-chain.cdml")
	try:
		assert main_window.open_file_path(str(tmp_path / "atom-cut-chain.cdml"))
		_item(atom_origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)
		qapp.processEvents()
		main_window.on_cut()
		atom_fragment = _fragment_records(_clipboard_fragment())
		atom_snapshot = atom_origin.backend_snapshot
		assert main_window.open_file_path(str(tmp_path / "bond-cut-chain.cdml"))
		_item(bond_origin, bkchem_qt.canvas.items.bond_item.BondItem, "b1").setSelected(True)
		main_window.on_cut()
		bond_fragment = _fragment_records(_clipboard_fragment())
		bond_snapshot = bond_origin.backend_snapshot
	finally:
		_close(main_window, atom_origin, monkeypatch)
		_close(main_window, bond_origin, monkeypatch)

	assert atom_fragment == (("molecule",), ("a2",), ()) and 'id="a2"' not in atom_snapshot.cdml
	assert bond_fragment == (("molecule",), ("a1", "a2"), ("b1",)) and 'id="b1"' not in bond_snapshot.cdml


#============================================
def test_mixed_structure_and_presentation_cut_is_inert_but_presentation_cut_remains_available(
		main_window: object, qapp: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Partial Cut does not promote a structural/presentation mixture to roots."""
	cdml = _CHAIN.replace("</cdml>", '<plus id="plus1"><point x="0cm" y="3cm"/></plus></cdml>')
	origin = _open(main_window, tmp_path, "mixed-cut.cdml", cdml)
	qapp.clipboard().clear()
	before = origin.backend_snapshot
	try:
		_item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)
		plus = next(
			item for item in origin.scene.items()
			if getattr(getattr(item, "document_object_model", None), "object_id", None) == "plus1"
		)
		plus.setSelected(True)
		main_window.on_cut()
		mixed_status, _mixed_fragment = bkchem_qt.io.clipboard_manager.ClipboardManager().read_fragment()
		mixed_snapshot = origin.backend_snapshot
		_item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(False)
		plus.setSelected(True)
		main_window.on_cut()
		presentation_fragment = _fragment_records(_clipboard_fragment())
		presentation_snapshot = origin.backend_snapshot
	finally:
		_close(main_window, origin, monkeypatch)

	assert mixed_status == "no_data" and mixed_snapshot == before
	assert presentation_fragment[0] == ("plus",) and 'id="plus1"' not in presentation_snapshot.cdml


#============================================
def test_foreign_structural_wrapper_is_not_a_current_projection_target(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The public structural classifier rejects an unregistered lookalike wrapper."""
	origin = _open(main_window, tmp_path, "stale-cut.cdml")
	try:
		current_atom = _item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2")
		foreign_atom = bkchem_qt.canvas.items.atom_item.AtomItem(current_atom.atom_model)
		targets = bkchem_qt.canvas.document_projection.structure_delete_targets_for_items(
			origin.document, (foreign_atom,),
		)
		foreign_atom.dispose()
	finally:
		_close(main_window, origin, monkeypatch)

	assert targets is None


#============================================
def test_clipboard_publish_keeps_cut_bound_to_its_origin_tab(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Activating another tab during publication cannot redirect structural Cut."""
	origin = _open(main_window, tmp_path, "origin-cut.cdml")
	other = _open(main_window, tmp_path, "other-cut.cdml", "<cdml/>")
	other_before = other.backend_snapshot
	original_publish = bkchem_qt.io.clipboard_manager.ClipboardManager.publish_fragment
	try:
		assert main_window.open_file_path(str(tmp_path / "origin-cut.cdml"))
		_item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)

		def publish_then_activate(manager: object, fragment: str) -> None:
			"""Publish raw text, then activate the already-open other tab."""
			original_publish(manager, fragment)
			main_window.open_file_path(str(tmp_path / "other-cut.cdml"))

		monkeypatch.setattr(
			bkchem_qt.io.clipboard_manager.ClipboardManager,
			"publish_fragment", publish_then_activate,
		)
		main_window.on_cut()
	finally:
		_close(main_window, origin, monkeypatch)
		_close(main_window, other, monkeypatch)

	assert 'id="a2"' not in origin.backend_snapshot.cdml
	assert other.backend_snapshot == other_before


#============================================
def test_origin_close_during_fragment_publication_prevents_delete(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A disposed origin retains the published fragment but never receives Delete."""
	origin = _open(main_window, tmp_path, "closing-cut.cdml")
	other = _open(main_window, tmp_path, "remaining-cut.cdml", "<cdml/>")
	original_publish = bkchem_qt.io.clipboard_manager.ClipboardManager.publish_fragment
	try:
		assert main_window.open_file_path(str(tmp_path / "closing-cut.cdml"))
		_item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)

		def publish_then_close(manager: object, fragment: str) -> None:
			"""Deliver the fragment before closing the still-clean origin tab."""
			original_publish(manager, fragment)
			assert main_window.close_session_at(main_window.sessions.index(origin))

		monkeypatch.setattr(
			bkchem_qt.io.clipboard_manager.ClipboardManager,
			"publish_fragment", publish_then_close,
		)
		main_window.on_cut()
		fragment = _fragment_records(_clipboard_fragment())
	finally:
		_close(main_window, other, monkeypatch)

	assert origin.is_disposed and 'id="a2"' in origin.backend_snapshot.cdml
	assert fragment == (("molecule",), ("a2",), ())


#============================================
def test_projection_recovery_uses_the_accepted_cut_snapshot_without_resubmission(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Post-acceptance projection loss blocks writes until snapshot-only recovery."""
	origin = _open(main_window, tmp_path, "retry-cut.cdml")
	try:
		origin.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				origin,
				lambda _snapshot: bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
					bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
					bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
				),
			),
		)
		_item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)
		main_window.on_cut()
		accepted_snapshot = origin.backend_snapshot
		blocked_delete = origin.submit_persistent_operation(
			bkchem_qt.models.document_session.build_structure_delete_request(
				accepted_snapshot.revision, "m1", ("a1",), (),
			),
		)
		blocked_paste = origin.submit_clipboard_fragment("<cdml><plus><point x=\"0cm\" y=\"0cm\"/></plus></cdml>")

		def raise_after_acceptance(*_args: object, **_kwargs: object) -> object:
			"""Fail an entry point if retry incorrectly attempts to replay Cut intent."""
			raise RuntimeError("accepted Cut intent must not be replayed")

		monkeypatch.setattr(origin, "extract_structure_fragment", raise_after_acceptance)
		monkeypatch.setattr(
			bkchem_qt.io.clipboard_manager.ClipboardManager,
			"publish_fragment", raise_after_acceptance,
		)
		monkeypatch.setattr(origin, "submit_persistent_operation", raise_after_acceptance)
		origin.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				origin,
				lambda snapshot: main_window._replace_session_projection(origin, snapshot),
			),
		)
		retry = origin.retry_current_backend_projection()
	finally:
		_close(main_window, origin, monkeypatch)

	assert 'id="a2"' not in accepted_snapshot.cdml and (blocked_delete.status, blocked_paste.status) == ("unavailable", "unavailable")
	assert retry.status == "accepted" and origin.backend_snapshot == accepted_snapshot
