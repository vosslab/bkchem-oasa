"""Qt behavior checks for authoritative molecular information."""

# PIP3 modules
import pytest
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.dialogs.molecule_info_dialog
import bkchem_qt.models.document_session
import oasa.cdml_document


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <molecule id="methane" name="Methane">
  <atom id="c1" name="C"><point x="0cm" y="0cm" /></atom>
 </molecule>
 <molecule id="water" name="Water">
  <atom id="o1" name="O"><point x="2cm" y="0cm" /></atom>
 </molecule>
</cdml>
"""


#============================================
def _install_session(main_window: object) -> object:
	"""Install two authoritative molecules through the production session route."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	session = main_window._register_session(session, activate=True)
	if session.retry_current_backend_projection().status != "accepted":
		raise RuntimeError("Molecule information fixture did not project")
	return session


#============================================
def _select_molecules(session: object, molecule_ids: tuple[str, ...]) -> None:
	"""Select one atom from each named direct-root molecule."""
	selected = set()
	for item in session.scene.items():
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			continue
		molecule = session.document.molecule_for_graphics_item(item)
		if molecule.mol_id in molecule_ids and molecule.mol_id not in selected:
			item.setSelected(True)
			selected.add(molecule.mol_id)
	assert selected == set(molecule_ids)


#============================================
def _capture_info_dialogs(
		monkeypatch: pytest.MonkeyPatch,
		) -> list[bkchem_qt.dialogs.molecule_info_dialog.MoleculeInfoDialog]:
	"""Keep the real dialog inspectable while bypassing its modal event loop."""
	dialogs = []

	def record_dialog(dialog: object) -> int:
		"""Record the fully built read-only surface."""
		dialogs.append(dialog)
		return PySide6.QtWidgets.QDialog.DialogCode.Accepted

	monkeypatch.setattr(
		bkchem_qt.dialogs.molecule_info_dialog.MoleculeInfoDialog,
		"exec", record_dialog,
	)
	return dialogs


#============================================
def _capture_messages(
		monkeypatch: pytest.MonkeyPatch,
		) -> list[tuple[str, str, str]]:
	"""Capture actionable modal states without blocking the test event loop."""
	messages = []

	def information(_parent: object, title: str, text: str) -> None:
		messages.append(("information", title, text))

	def warning(_parent: object, title: str, text: str) -> None:
		messages.append(("warning", title, text))

	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "information", information)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", warning)
	return messages


#============================================
def test_info_uses_implicit_hydrogens_without_changing_document_state(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The visible methane result comes from OASA and leaves the edit state intact."""
	session = _install_session(main_window)
	_select_molecules(session, ("methane",))
	dialogs = _capture_info_dialogs(monkeypatch)
	before_snapshot = session.backend_snapshot
	before_undo_count = session.document.undo_stack.count()
	before_selection = session.document.selected_direct_root_molecule_ids

	bkchem_qt.actions.chemistry_actions._chemistry_info(main_window)

	assert len(dialogs) == 1
	text = dialogs[0].details_text
	assert (
		"Name: Methane" in text
		and "ID: methane" in text
		and "Formula: CH4" in text
		and "Average molecular weight: 16.0423" in text
		and "Monoisotopic mass: 16.03130012" in text
		and "C: 74.869%" in text
		and "Implicit hydrogens are included" in dialogs[0].findChild(
			PySide6.QtWidgets.QLabel,
		).text()
		and session.backend_snapshot == before_snapshot
		and session.document.undo_stack.count() == before_undo_count
		and session.document.selected_direct_root_molecule_ids == before_selection
	)


#============================================
def test_info_restores_classic_multi_molecule_combined_summary(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""One batch displays individual facts and the classic combined selection."""
	session = _install_session(main_window)
	_select_molecules(session, ("methane", "water"))
	dialogs = _capture_info_dialogs(monkeypatch)

	bkchem_qt.actions.chemistry_actions._chemistry_info(main_window)

	text = dialogs[0].details_text
	assert (
		"Individual molecules" in text
		and "Formula: CH4" in text
		and "Formula: H2O" in text
		and "Combined selection" in text
		and "Formula: CH6O" in text
		and text.count("Monoisotopic mass:") == 3
	)


#============================================
def test_info_empty_state_is_disabled_and_explains_valid_selection(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The menu prevents empty invocation while its handler remains recoverable."""
	messages = _capture_messages(monkeypatch)

	assert not main_window._registry.is_enabled("chemistry.info", main_window)
	bkchem_qt.actions.chemistry_actions._chemistry_info(main_window)

	assert messages == [(
		"information", "Molecule Information",
		"Select one or more molecules without artwork, then choose Chemistry > Info.",
	)]


#============================================
def test_info_revision_conflict_preserves_selection_and_offers_retry(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A stale observation is a visible recoverable state, never a local fallback."""
	session = _install_session(main_window)
	_select_molecules(session, ("methane",))
	messages = _capture_messages(monkeypatch)
	before = session.backend_snapshot

	def stale_query(_revision: int, _molecule_ids: tuple[str, ...]) -> object:
		"""Simulate an edit landing after the UI captured its revision."""
		raise oasa.cdml_document.CDMLRevisionConflictError(
			"expected revision 0, current revision is 1",
		)

	monkeypatch.setattr(session, "query_molecule_summary", stale_query)
	bkchem_qt.actions.chemistry_actions._chemistry_info(main_window)

	assert (
		messages
		and messages[0][0:2] == ("warning", "Molecule Information")
		and "document changed" in messages[0][2].lower()
		and "try again" in messages[0][2].lower()
		and session.backend_snapshot == before
		and session.document.selected_direct_root_molecule_ids == ("methane",)
	)
