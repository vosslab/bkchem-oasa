"""Tests for the truthful Qt file-import capability registry."""

# Standard Library
import pathlib

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.actions.file_actions
import bkchem_qt.bridge.worker
import bkchem_qt.io.import_capabilities
import bkchem_qt.models.document_session
import oasa.cdml


#============================================
class _SessionAwareHost:
	"""Minimal session-owning host used to verify action delegation."""

	#============================================
	def __init__(self) -> None:
		"""Start with no delegated paths."""
		self.paths: list[str] = []

	#============================================
	def open_file_path(self, file_path: str) -> None:
		"""Record the path that the action delegates to this host."""
		self.paths.append(file_path)


#============================================
def _staged_structure_signature(main_window: object, prepared_cdml: str) -> tuple:
	"""Stage complete CDML, then summarize its authoritative chemistry."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_imported_cdml(
		prepared_cdml,
	)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window,
		theme_manager=main_window._theme_manager,
		prefs=main_window._prefs,
		mode_host=main_window,
		prepared_imported_cdml=prepared,
	)
	try:
		molecules = list(oasa.cdml.read_cdml(session.backend_snapshot.cdml))
		return session.backend_snapshot.is_dirty, tuple(
			(
				tuple(atom.symbol for atom in molecule.vertices),
				tuple(
					(
						molecule.vertices.index(bond.vertices[0]),
						molecule.vertices.index(bond.vertices[1]),
						bond.order,
					)
					for bond in molecule.edges
				),
			)
			for molecule in molecules
		)
	finally:
		session.dispose()


def test_import_chooser_delegates_to_the_session_loader(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A selected external structure opens through the owning session."""
	def choose_file(*args: object, **kwargs: object) -> tuple[str, str]:
		"""Return one path for each dialog invocation."""
		return ("example.smi", "")

	monkeypatch.setattr(
		bkchem_qt.actions.file_actions.PySide6.QtWidgets.QFileDialog,
		"getOpenFileName",
		choose_file,
	)
	host = _SessionAwareHost()
	capability = bkchem_qt.io.import_capabilities.capability_for_extension(".smi")
	bkchem_qt.actions.file_actions.import_capability(host, capability)
	assert host.paths == ["example.smi"]


#============================================
def test_cdxml_import_capability_stages_a_dirty_authoritative_snapshot(
		tmp_path: pathlib.Path, main_window: object,
		) -> None:
	"""CDXML opens as a dirty authoritative document with its bond topology."""
	cdxml_path = tmp_path / "structure.cdxml"
	cdxml_path.write_text(
		"<CDXML><page><fragment id='f1'>"
		"<n id='a1' p='10 20'/><n id='a2' p='30 20'>"
		"<t><s>O</s></t></n><b id='b1' B='a1' E='a2' Order='2'/>"
		"</fragment></page></CDXML>",
		encoding="utf-8",
	)
	capability = bkchem_qt.io.import_capabilities.capability_for_extension(
		".cdxml",
	)
	prepared = bkchem_qt.bridge.worker._read_and_prepare_import(
		capability.codec_name, str(cdxml_path),
	)
	assert isinstance(prepared, bkchem_qt.bridge.worker.PreparedCompleteCDML)
	assert _staged_structure_signature(main_window, prepared.complete_cdml) == (True, (
		(("C", "O"), ((0, 1, 2),)),
	))


#============================================
def test_cml_import_capability_stages_a_dirty_authoritative_snapshot(
		tmp_path: pathlib.Path, main_window: object,
		) -> None:
	"""CML opens as a dirty authoritative document with its bond topology."""
	cml_path = tmp_path / "structure.cml"
	cml_path.write_text(
		"<cml><molecule><atomArray>"
		"<atom id='a1' elementType='C' x2='1.5' y2='2.5'/>"
		"<atom id='a2' elementType='N' x2='3.5' y2='2.5'/>"
		"</atomArray><bondArray>"
		"<bond atomRefs2='a1 a2' order='3'/>"
		"</bondArray></molecule></cml>",
		encoding="utf-8",
	)
	capability = bkchem_qt.io.import_capabilities.capability_for_extension(
		".cml",
	)
	prepared = bkchem_qt.bridge.worker._read_and_prepare_import(
		capability.codec_name, str(cml_path),
	)
	assert isinstance(prepared, bkchem_qt.bridge.worker.PreparedCompleteCDML)
	assert _staged_structure_signature(main_window, prepared.complete_cdml) == (True, (
		(("C", "N"), ((0, 1, 3),)),
	))


#============================================
def test_xml_extension_is_not_a_qt_import_capability() -> None:
	"""Generic XML remains out of the UI despite OASA's legacy CML alias."""
	with pytest.raises(ValueError, match="Unsupported chemistry import extension"):
		bkchem_qt.io.import_capabilities.capability_for_extension(".xml")
