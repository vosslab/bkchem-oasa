"""Behavior and import-boundary coverage for Qt CDML compatibility inspection."""

# Standard Library
import ast
import pathlib

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.property_editing
import bkchem_qt.io.cdml_inspection
import bkchem_qt.models.document
import bkchem_qt.models.molecule_model


#============================================
def test_direct_ftext_text_keeps_direct_text_and_cdata_in_authored_order() -> None:
	"""Plain Configure receives only direct retained character data."""
	text = bkchem_qt.io.cdml_inspection.direct_ftext_text(
		"first<![CDATA[ second]]> third",
	)

	assert text == "first second third"


#============================================
def test_direct_ftext_text_does_not_flatten_nested_markup() -> None:
	"""Nested rich content remains outside the existing plain-text extraction rule."""
	text = bkchem_qt.io.cdml_inspection.direct_ftext_text("before<b>nested</b>after")

	assert text == "beforeafter"


#============================================
def test_direct_ftext_text_reports_malformed_compatibility_content() -> None:
	"""Malformed retained content cannot be mistaken for editable plain text."""
	text = bkchem_qt.io.cdml_inspection.direct_ftext_text("before<broken>")

	assert text is None


#============================================
def test_root_id_preserves_exact_nonempty_compatibility_identifier() -> None:
	"""Compatibility ID planning retains the authored root ID spelling."""
	identifier = bkchem_qt.io.cdml_inspection.root_id('<fragment id="legacy:one"/>')

	assert identifier == "legacy:one"


#============================================
def test_root_id_ignores_missing_empty_and_malformed_compatibility_content() -> None:
	"""Only valid nonempty root IDs reserve an isolated compatibility identifier."""
	identifiers = (
		bkchem_qt.io.cdml_inspection.root_id("<fragment/>"),
		bkchem_qt.io.cdml_inspection.root_id('<fragment id=""/>'),
		bkchem_qt.io.cdml_inspection.root_id("<fragment>"),
	)

	assert identifiers == (None, None, None)


#============================================
def test_root_id_does_not_reserve_nested_or_namespaced_lookalike_ids() -> None:
	"""Only an exact direct-root ``id`` attribute participates in local planning."""
	identifiers = (
		bkchem_qt.io.cdml_inspection.root_id('<fragment><child id="nested"/></fragment>'),
		bkchem_qt.io.cdml_inspection.root_id(
			'<fragment xmlns:v="urn:vendor" v:id="lookalike"/>',
		),
	)

	assert identifiers == (None, None)


#============================================
def test_document_id_planning_reserves_valid_retained_id_and_ignores_malformed_xml(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Compatibility XML reserves only a valid root ID during local ID planning."""
	document = bkchem_qt.models.document.Document()
	molecule = bkchem_qt.models.molecule_model.MoleculeModel(document)
	molecule.retain_unsupported_fragment_xml('<fragment id="fragment1"/>')
	molecule.retain_unsupported_fragment_xml('<fragment><child id="fragment2"/></fragment>')
	molecule.retain_unsupported_fragment_xml("<fragment>")
	document.add_molecule(molecule, mark_dirty=False)
	candidate = document.unique_cdml_id("fragment")

	assert candidate == "fragment2"
	document.deleteLater()
	qapp.processEvents()


#============================================
def _implementation_imports(module: object) -> set[str]:
	"""Return OASA or XML implementation imports declared by one UI consumer."""
	source_path = pathlib.Path(module.__file__)
	tree = ast.parse(source_path.read_text(encoding="utf-8"))
	imports = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			imports.update(
				alias.name for alias in node.names
				if alias.name.split(".")[0] in {"oasa", "xml", "lxml", "defusedxml"}
			)
		if isinstance(node, ast.ImportFrom) and node.module is not None:
			if node.module.split(".")[0] in {"oasa", "xml", "lxml", "defusedxml"}:
				imports.add(node.module)
	return imports


#============================================
def test_plain_qt_consumers_keep_xml_implementation_inside_cdml_io_boundary() -> None:
	"""The action and model consume only scalar CDML inspection facts."""
	imports = (
		_implementation_imports(bkchem_qt.actions.property_editing)
		| _implementation_imports(bkchem_qt.models.document)
	)

	assert not imports
