"""Public behavior coverage for backend-authoritative partial structural Copy."""

# Standard Library
import pathlib

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.io.clipboard_manager
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
	"""Return one live projected atom or bond by durable identity."""
	attribute = "atom_model" if item_type is bkchem_qt.canvas.items.atom_item.AtomItem else "bond_model"
	item = next(
		candidate for candidate in session.scene.items()
		if isinstance(candidate, item_type)
		and getattr(candidate, attribute).backend_durable_id == durable_id
	)
	return item


#============================================
def _clipboard_fragment() -> str:
	"""Return the public raw CDML currently owned by the native clipboard."""
	status, fragment = bkchem_qt.io.clipboard_manager.ClipboardManager().read_fragment()
	assert status == "ok" and fragment is not None
	return fragment


#============================================
def _records(fragment: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	"""Read structural IDs through the hardened CDML entry point."""
	accepted = oasa.cdml_document.CDMLDocument.parse(fragment, validation="compat")
	root = oasa.safe_xml.parse_dom_from_string(accepted.serialize()).documentElement
	molecule = next(
		child for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.localName == "molecule"
	)
	atom_ids = tuple(
		child.getAttribute("id") for child in molecule.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.localName == "atom"
	)
	bond_ids = tuple(
		child.getAttribute("id") for child in molecule.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.localName == "bond"
	)
	return atom_ids, bond_ids


#============================================
@pytest.mark.parametrize(
	("item_type", "durable_id", "expected"),
	(
		(bkchem_qt.canvas.items.atom_item.AtomItem, "a2", (("a2",), ())),
		(bkchem_qt.canvas.items.bond_item.BondItem, "b1", (("a1", "a2"), ("b1",))),
	),
)
def test_partial_copy_extracts_authoritative_atoms_and_bond_closure_without_mutation(
		main_window: object, tmp_path: pathlib.Path, item_type: type,
		durable_id: str, expected: tuple[tuple[str, ...], tuple[str, ...]],
		) -> None:
	"""Exact structural Copy publishes the backend fragment without any local edit."""
	session = _open(main_window, tmp_path, "partial-copy.cdml")
	try:
		before = session.backend_snapshot
		undo_count = session.document.undo_stack.count()
		_item(session, item_type, durable_id).setSelected(True)
		main_window.on_copy()
		fragment = _clipboard_fragment()
		after = session.backend_snapshot
		after_undo_count = session.document.undo_stack.count()
		after_dirty = session.document.dirty
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert _records(fragment) == expected
	assert (after, after_undo_count, after_dirty) == (before, undo_count, False)


#============================================
def test_invalid_structural_copy_preserves_the_existing_clipboard(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""Disconnected and ID-less current structural selections never fall back to roots."""
	session = _open(main_window, tmp_path, "invalid-copy.cdml")
	prior_fragment = "<cdml><plus id=\"preserved\"><point x=\"0cm\" y=\"0cm\"/></plus></cdml>"
	try:
		main_window._clipboard_manager.publish_fragment(prior_fragment)
		before = session.backend_snapshot
		_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "a1").setSelected(True)
		_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "a3").setSelected(True)
		main_window.on_copy()
		disconnected_fragment = _clipboard_fragment()
		for item in session.scene.selectedItems():
			item.setSelected(False)
		idless = _item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "a2")
		idless.atom_model.bind_backend_durable_id(None)
		idless.setSelected(True)
		main_window.on_copy()
		idless_fragment = _clipboard_fragment()
		idless.setSelected(False)
		foreign = bkchem_qt.canvas.items.atom_item.AtomItem(
			_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "a1").atom_model,
		)
		session.scene.addItem(foreign)
		foreign.setSelected(True)
		main_window.on_copy()
		foreign_fragment = _clipboard_fragment()
		session.scene.removeItem(foreign)
		foreign.dispose()
		after = session.backend_snapshot
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert (disconnected_fragment, idless_fragment, foreign_fragment, after) == (
		prior_fragment, prior_fragment, prior_fragment, before,
	)


#============================================
def test_mixed_structural_and_presentation_copy_keeps_existing_root_behavior(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""A legitimate mixed selection remains a complete molecule-plus-root Copy."""
	cdml = _CHAIN.replace("</cdml>", '<plus id="plus1"><point x="0cm" y="3cm"/></plus></cdml>')
	session = _open(main_window, tmp_path, "mixed-copy.cdml", cdml)
	try:
		before = session.backend_snapshot
		_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)
		plus = next(
			item for item in session.scene.items()
			if getattr(getattr(item, "document_object_model", None), "object_id", None) == "plus1"
		)
		plus.setSelected(True)
		main_window.on_copy()
		fragment = _clipboard_fragment()
		after = session.backend_snapshot
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert 'id="a1"' in fragment and 'id="a3"' in fragment and 'id="plus1"' in fragment
	assert after == before


#============================================
def test_multi_molecule_structural_copy_keeps_existing_whole_root_behavior(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""Current atoms from two molecules remain a top-level molecule Copy."""
	cdml = _CHAIN.replace(
		"</cdml>",
		'<molecule id="m2"><atom id="m2a1" name="N"><point x="4cm" y="0cm"/>'
		"</atom></molecule></cdml>",
	)
	session = _open(main_window, tmp_path, "multi-root-copy.cdml", cdml)
	try:
		before = session.backend_snapshot
		_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)
		_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "m2a1").setSelected(True)
		main_window.on_copy()
		fragment = _clipboard_fragment()
		after = session.backend_snapshot
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert 'id="m1"' in fragment and 'id="m2"' in fragment and after == before


#============================================
@pytest.mark.parametrize("duplicate_root_id", (False, True))
def test_multi_molecule_copy_rejects_invalid_durable_root_identity(
		main_window: object, tmp_path: pathlib.Path, duplicate_root_id: bool,
		) -> None:
	"""Malformed or aliased selected roots preserve the existing clipboard."""
	cdml = _CHAIN.replace(
		"</cdml>",
		'<molecule id="m2"><atom id="m2a1" name="N"><point x="4cm" y="0cm"/>'
		"</atom></molecule></cdml>",
	)
	session = _open(main_window, tmp_path, "invalid-multi-copy.cdml", cdml)
	prior_fragment = '<cdml><plus id="preserved"><point x="0cm" y="0cm"/></plus></cdml>'
	try:
		main_window._clipboard_manager.publish_fragment(prior_fragment)
		first = next(molecule for molecule in session.document.molecules if molecule.mol_id == "m1")
		second = next(molecule for molecule in session.document.molecules if molecule.mol_id == "m2")
		second.mol_id = first.mol_id if duplicate_root_id else ""
		_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)
		_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "m2a1").setSelected(True)
		main_window.on_copy()
		fragment = _clipboard_fragment()
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert fragment == prior_fragment


#============================================
def test_partial_copy_releases_the_origin_before_clipboard_callbacks_close_its_tab(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Native clipboard callbacks may close the origin after read-only extraction."""
	origin = _open(main_window, tmp_path, "closing-copy.cdml")
	other = _open(main_window, tmp_path, "other-copy.cdml", "<cdml/>")
	original_publish = bkchem_qt.io.clipboard_manager.ClipboardManager.publish_fragment
	try:
		assert main_window.open_file_path(str(tmp_path / "closing-copy.cdml"))
		_item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)

		def publish_then_close(manager: object, fragment: str) -> None:
			"""Publish raw text, then retire the originating tab synchronously."""
			original_publish(manager, fragment)
			assert main_window.close_session_at(main_window.sessions.index(origin))

		monkeypatch.setattr(
			bkchem_qt.io.clipboard_manager.ClipboardManager,
			"publish_fragment", publish_then_close,
		)
		main_window.on_copy()
		fragment = _clipboard_fragment()
	finally:
		if not other.is_disposed:
			main_window._on_new()
			main_window._remove_session(other)

	assert origin.is_disposed and _records(fragment) == (("a2",), ())


#============================================
def test_legacy_copy_keeps_its_whole_root_when_clipboard_callbacks_activate_another_tab(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Legacy whole-root Copy remains origin-owned across tab activation."""
	origin = _open(main_window, tmp_path, "legacy-closing-copy.cdml")
	other = _open(main_window, tmp_path, "legacy-other-copy.cdml", "<cdml/>")
	other_before = other.backend_snapshot
	original_publish = bkchem_qt.io.clipboard_manager.ClipboardManager.publish_fragment
	try:
		assert main_window.open_file_path(str(tmp_path / "legacy-closing-copy.cdml"))
		origin.document.mark_dirty()
		origin.document.molecules[0].compatibility_source_xml = "<molecule/>"
		_item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)

		def publish_then_activate(manager: object, fragment: str) -> None:
			"""Publish raw text, then activate the already-open other tab."""
			original_publish(manager, fragment)
			assert main_window.open_file_path(str(tmp_path / "legacy-other-copy.cdml"))

		monkeypatch.setattr(
			bkchem_qt.io.clipboard_manager.ClipboardManager,
			"publish_fragment", publish_then_activate,
		)
		main_window.on_copy()
		fragment = _clipboard_fragment()
		legacy_isolated = origin.legacy_isolated
		other_after = other.backend_snapshot
	finally:
		if not origin.is_disposed:
			main_window._on_new()
			main_window._remove_session(origin)
		if not other.is_disposed:
			main_window._on_new()
			main_window._remove_session(other)

	atom_ids, bond_ids = _records(fragment)
	assert set(atom_ids) == {"a1", "a2", "a3"}
	assert set(bond_ids) == {"b1", "b2"}
	assert (legacy_isolated, other_after) == (True, other_before)
