"""Focused Qt authority coverage for Convert to Linear Form."""

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.models.document_session


_CDML = """<cdml><molecule id="m1"><atom id="a3" name="O"><point x="20" y="4"/></atom><atom id="a1" name="C"><point x="0" y="0"/></atom><atom id="a2" name="C"><point x="7" y="9"/></atom><bond id="b2" start="a2" end="a3" type="n1"/><bond id="b1" start="a1" end="a2" type="n1"/></molecule></cdml>"""


#============================================
def _session(main_window: object) -> object:
	"""Install one native session with an editable durable path."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._register_session(
		main_window._construct_session(prepared_native_cdml=prepared), activate=True,
	)
	if not main_window._replace_session_projection(session, session.backend_snapshot):
		raise AssertionError("Native linear-form CDML projection is unavailable")
	return session


#============================================
def _item(session: object, item_type: type, durable_id: str) -> object:
	"""Return one currently projected durable atom or bond item."""
	for item in session.scene.items():
		model = getattr(item, "atom_model", getattr(item, "bond_model", None))
		if isinstance(item, item_type) and getattr(model, "backend_durable_id", None) == durable_id:
			return item
	raise AssertionError("Projected linear-form target is unavailable")


#============================================
def test_convert_to_linear_submits_plain_origin_intent_and_restores_atoms(
		main_window: object,
		) -> None:
	"""The real action expands a bond and uses backend history, never Qt undo."""
	session = _session(main_window)
	try:
		_item(session, bkchem_qt.canvas.items.atom_item.AtomItem, "a3").setSelected(True)
		_item(session, bkchem_qt.canvas.items.bond_item.BondItem, "b1").setSelected(True)
		bkchem_qt.actions.chemistry_actions._convert_to_linear(main_window)
		selected = {
			item.atom_model.backend_durable_id for item in session.scene.selectedItems()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		}
		assert "<name>linear_form</name>" in session.backend_snapshot.cdml and not session.document.undo_stack.canUndo()
		assert selected == {"a1", "a2", "a3"}
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_retained_linear_form_capability_is_unavailable_after_close(main_window: object) -> None:
	"""A captured origin session cannot mutate another tab after disposal."""
	session = _session(main_window)
	capability = main_window.persistent_operation_capability_for(session)
	revision = session.backend_snapshot.revision
	main_window.close_session_at(main_window.sessions.index(session))
	outcome = capability(bkchem_qt.models.document_session.build_linear_form_convert_request(
		revision, "m1", ("a1",),
	))
	assert outcome.status == "unavailable" and outcome.commit is None
