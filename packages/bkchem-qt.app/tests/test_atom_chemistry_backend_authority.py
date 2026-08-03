"""Behavior tests for synchronized chemistry menu observations."""

import ast
import pathlib
from types import SimpleNamespace

from bkchem_qt.actions import chemistry_actions
from oasa import cdml_document


#============================================
class _Session:
	"""Small synchronized-session double with deliberately wrong Qt atom state."""

	def __init__(self) -> None:
		self.document = SimpleNamespace(selected_direct_root_molecule_ids=("m",))
		self.backend_snapshot = SimpleNamespace(revision=7)
		self.is_disposed = False
		self.can_write_authoritative_snapshot = True
		self.scene = object()
		self.view = object()

	def observe_atom_chemistry_facts(
			self, expected_revision: int,
			) -> cdml_document.CDMLAtomChemistryFactsObservation:
		assert expected_revision == 7
		return cdml_document.CDMLAtomChemistryFactsObservation(7, (
			cdml_document.CDMLAtomChemistryFactRecord(
				"m", "a", "C", 0, 1, 1, "usable", 4, 1, 3, 3, -3, 6, None,
			),
		), ())


#============================================
def _synchronized_app(session: _Session) -> object:
	"""Build the public action's required synchronized app envelope."""
	app = SimpleNamespace(
		document=session.document, scene=session.scene, view=session.view,
		_active_session=session, sessions=(session,),
	)
	return app


#============================================
def test_synchronized_chemistry_check_uses_complete_graph_facts(monkeypatch: object) -> None:
	"""The synchronized result reports OASA's bonded-carbon free valency, not 4."""
	shown = []
	monkeypatch.setattr(
		chemistry_actions.PySide6.QtWidgets.QMessageBox, "information",
		lambda _app, _title, text: shown.append(text),
	)
	session = _Session()
	chemistry_actions._chemistry_check(_synchronized_app(session))
	assert shown == ["All selected atoms pass the OASA complete-graph valency check."]


#============================================
def test_synchronized_oxidation_uses_the_same_read_only_facts(monkeypatch: object) -> None:
	"""Oxidation display is derived from the same exact-revision backend observation."""
	shown = []
	monkeypatch.setattr(
		chemistry_actions.PySide6.QtWidgets.QMessageBox, "information",
		lambda _app, _title, text: shown.append(text),
	)
	session = _Session()
	chemistry_actions._oxidation_number(_synchronized_app(session))
	assert "C (a): -III" in shown[0]


#============================================
def test_chemistry_actions_have_no_direct_oasa_imports() -> None:
	"""Chemistry UI reaches OASA implementation only through a named bridge."""
	source_path = pathlib.Path(chemistry_actions.__file__)
	tree = ast.parse(source_path.read_text(encoding="utf-8"))
	modules = [
		alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
		for alias in node.names
	]
	modules += [
		node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
	]
	assert all(module is None or not module.startswith("oasa") for module in modules)
