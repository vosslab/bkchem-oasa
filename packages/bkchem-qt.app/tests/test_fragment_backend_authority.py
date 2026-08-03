"""Focused synchronized authority checks for ordinary fragment metadata."""

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.models.document_session


_CDML = """<cdml><molecule id="m1"><atom id="a1" name="C"><point x="0cm" y="0cm"/></atom><atom id="a2" name="O"><point x="1cm" y="0cm"/></atom><bond id="b1" start="a1" end="a2" type="n1"/></molecule></cdml>"""


#============================================
def _native_session(main_window: object) -> object:
	"""Register one ordinary projected molecule session."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._register_session(
		main_window._construct_session(prepared_native_cdml=prepared), activate=True,
	)
	if not main_window._replace_session_projection(session, session.backend_snapshot):
		raise AssertionError("Native fragment CDML projection is unavailable")
	return session


#============================================
def _item(session: object, item_type: type, durable_id: str) -> object:
	"""Return one current atom or bond projection by durable backend ID."""
	for item in session.scene.items():
		model = getattr(item, "atom_model", getattr(item, "bond_model", None))
		if isinstance(item, item_type) and getattr(model, "backend_durable_id", None) == durable_id:
			return item
	raise AssertionError("Projected CDML did not produce the requested durable item")


#============================================
def test_synchronized_fragment_metadata_uses_backend_history(main_window: object) -> None:
	"""Create and delete reproject one backend-owned fragment without Qt undo."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._register_session(
		main_window._construct_session(prepared_native_cdml=prepared), activate=True,
	)
	try:
		assert main_window._replace_session_projection(session, session.backend_snapshot)
		created = session.submit_persistent_operation(
			bkchem_qt.models.document_session.build_fragment_create_request(
				session.backend_snapshot.revision, "m1", "pair", "explicit",
				("a1", "a2"), ("b1",),
			),
		)
		assert created.status == "accepted" and not session.document.undo_stack.canUndo()
		fragment_id = next(
			fragment.fragment_id for molecule in session.document.molecules
			for fragment in molecule.fragments if fragment.name == "pair"
		)
		deleted = session.submit_persistent_operation(
			bkchem_qt.models.document_session.build_fragment_delete_request(
				session.backend_snapshot.revision, "m1", fragment_id,
			),
		)
		assert deleted.status == "accepted" and fragment_id not in session.backend_snapshot.cdml
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_create_fragment_uses_origin_tab_and_authoritative_member_order(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The modal action submits source-ordered durable members to its origin tab."""
	origin = _native_session(main_window)
	other = None
	try:
		_item(origin, bkchem_qt.canvas.items.atom_item.AtomItem, "a2").setSelected(True)
		_item(origin, bkchem_qt.canvas.items.bond_item.BondItem, "b1").setSelected(True)

		def choose_name(*_args: object, **_kwargs: object) -> tuple[str, bool]:
			"""Switch tabs while the captured action awaits its name."""
			main_window.on_new()
			return "pair", True

		monkeypatch.setattr(PySide6.QtWidgets.QInputDialog, "getText", choose_name)
		monkeypatch.setattr(
			PySide6.QtWidgets.QInputDialog, "getItem",
			lambda *_args, **_kwargs: ("explicit", True),
		)
		bkchem_qt.actions.chemistry_actions._create_fragment(main_window)
		other = next(session for session in main_window.sessions if session is not origin)

		assert origin.backend_snapshot.cdml.index('<vertex id="a1"') < origin.backend_snapshot.cdml.index('<vertex id="a2"')
		assert "fragment" not in other.backend_snapshot.cdml
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)


#============================================
def test_view_fragments_delete_stays_with_its_captured_tab(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The delete dialog keeps durable intent when activation changes mid-modal."""
	origin = _native_session(main_window)
	other = None
	try:
		created = origin.submit_persistent_operation(
			bkchem_qt.models.document_session.build_fragment_create_request(
				origin.backend_snapshot.revision, "m1", "pair", "explicit",
				("a1", "a2"), ("b1",),
			),
		)
		if created.commit is None:
			raise AssertionError("Fragment creation did not produce an accepted snapshot")

		def choose_fragment(*args: object, **_kwargs: object) -> tuple[str, bool]:
			"""Select the offered durable fragment after changing the active tab."""
			main_window.on_new()
			return args[3][1], True

		monkeypatch.setattr(PySide6.QtWidgets.QInputDialog, "getItem", choose_fragment)
		bkchem_qt.actions.chemistry_actions._view_fragments(main_window)
		other = next(session for session in main_window.sessions if session is not origin)

		assert "fragment" not in origin.backend_snapshot.cdml
		assert other.backend_snapshot.revision == 0
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)


#============================================
def test_native_synchronized_staging_uses_plain_fragment_facts_only(
		main_window: object,
		) -> None:
	"""Initial native staging uses backend facts before a later reprojection exists."""
	text = _CDML.replace(
		"</molecule>",
		'<fragment id="f1" type="explicit"><name>pair</name><vertex id="a1"/></fragment>'
		'<fragment id="f2" type="linear_form"><name>generated</name><vertex id="a1"/></fragment>'
		'<v:fragment id="foreign"><name>extension</name></v:fragment>'
		"</molecule>",
	).replace("<cdml>", '<cdml xmlns:v="urn:vendor">')
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(text)
	session = main_window._register_session(
		main_window._construct_session(prepared_native_cdml=prepared), activate=True,
	)
	try:
		molecule = session.document.molecules[0]
		assert ([fragment.name for fragment in molecule.fragments], any(
			("linear-form" in notice for notice in molecule.fragment_notices),
		)) == (["pair"], True)
		assert molecule.compatibility_source_xml is None
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
