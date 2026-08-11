"""Tests for the truthful Qt file-import capability registry."""

# Standard Library
import gzip
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
@pytest.mark.parametrize("extension", (".svg", ".svgz"))
def test_cdsvg_import_preserves_the_embedded_complete_document(
		tmp_path: pathlib.Path, main_window: object, extension: str,
		) -> None:
	"""Classic CD-SVG opens as dirty backend CDML, including drawing objects."""
	source = (
		'<svg xmlns="http://www.w3.org/2000/svg"><metadata>'
		'<cdml version="26.07"><paper type="A4" orientation="portrait"/>'
		'<molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm"/>'
		'</atom><atom id="a2" name="O"><point x="2cm" y="1cm"/></atom>'
		'<bond id="b1" start="a1" end="a2" type="n2"/></molecule>'
		'<arrow id="arrow1"><point x="3cm" y="1cm"/>'
		'<point x="4cm" y="1cm"/></arrow></cdml></metadata></svg>'
	)
	cdsvg_path = tmp_path / ("classic" + extension)
	if extension == ".svgz":
		with gzip.open(cdsvg_path, "wt", encoding="utf-8") as destination:
			destination.write(source)
	else:
		cdsvg_path.write_text(source, encoding="utf-8")
	capability = bkchem_qt.io.import_capabilities.capability_for_extension(extension)

	prepared = bkchem_qt.bridge.worker._read_and_prepare_import(
		capability.codec_name, str(cdsvg_path),
	)

	assert isinstance(prepared, bkchem_qt.bridge.worker.PreparedCompleteCDML)
	assert '<arrow id="arrow1">' in prepared.complete_cdml
	assert _staged_structure_signature(main_window, prepared.complete_cdml) == (True, (
		(("C", "O"), ((0, 1, 2),)),
	))


#============================================
def test_plain_rendered_svg_is_not_misrepresented_as_an_editable_document(
		tmp_path: pathlib.Path,
		) -> None:
	"""Only SVG with embedded CDML enters the authoritative document route."""
	svg_path = tmp_path / "rendered.svg"
	svg_path.write_text(
		'<svg xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 L 1 1"/></svg>',
		encoding="utf-8",
	)
	capability = bkchem_qt.io.import_capabilities.capability_for_extension(".svg")

	with pytest.raises(ValueError, match="no embedded CDML block"):
		bkchem_qt.bridge.worker._read_and_prepare_import(
			capability.codec_name, str(svg_path),
		)


#============================================
def test_cdsvg_open_file_path_installs_a_dirty_projected_session(
		tmp_path: pathlib.Path, main_window: object, qtbot: object,
		) -> None:
	"""The public file route delivers embedded CDML through its owned worker."""
	cdsvg_path = tmp_path / "open-classic.svg"
	cdsvg_path.write_text(
		'<svg xmlns="http://www.w3.org/2000/svg"><metadata>'
		'<cdml version="26.07"><arrow id="arrow1">'
		'<point x="1cm" y="1cm"/><point x="2cm" y="1cm"/>'
		'</arrow></cdml></metadata></svg>',
		encoding="utf-8",
	)
	target = main_window._active_session

	assert main_window.open_file_path(str(cdsvg_path), replace_current=True)
	qtbot.waitUntil(
		lambda: not target._import_workers and not main_window._retired_import_workers,
		timeout=3000,
	)
	imported = main_window._active_session

	assert imported is not target
	assert imported.backend_snapshot.is_dirty
	assert imported.document.file_path is None
	assert any(
		obj.object_id == "arrow1" for obj in imported.document.presentation_objects
	)


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
