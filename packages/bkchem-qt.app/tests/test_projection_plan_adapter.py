"""Fixture-free behavior checks for OASA-to-Qt projection-plan adaptation."""

# local repo modules
import bkchem_qt.io.cdml_document_io
import oasa.cdml_document
import oasa.cdml_presentation_properties


#============================================
def _hydrate(session: object) -> object:
	"""Hydrate one disposable Qt document from the current immutable OASA plan."""
	return bkchem_qt.io.cdml_document_io.hydrate_synchronized_cdml_document(
		session.projection_snapshot(),
	)


#============================================
def test_projection_adapter_uses_backend_normalized_appearance() -> None:
	"""Qt receives effective style facts without interpreting authored defaults."""
	cdml = (
		'<cdml><standard line_width="2px" line_color="#123"/>'
		'<arrow id="arrow1"><point x="0cm" y="0cm"/>'
		'<point x="1cm" y="0cm"/></arrow></cdml>'
	)
	document = _hydrate(oasa.cdml_document.CDMLDocumentSession.load(cdml))
	arrow = document.presentation_objects[0]
	assert (arrow.effective_line_width, arrow.effective_line_color) == (2.0, "#112233")


#============================================
def test_projection_replacement_preserves_durable_identity_with_fresh_wrapper() -> None:
	"""An accepted backend result replaces wrappers while retaining its durable ID."""
	cdml = (
		'<cdml><arrow id="arrow1" width="2"><point x="0cm" y="0cm"/>'
		'<point x="1cm" y="0cm"/></arrow></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	first = _hydrate(session).presentation_objects[0]
	patch = oasa.cdml_presentation_properties.CDMLArrowPropertiesPatch(
		session.revision, "arrow1", (("line_width", 3.0),),
	)
	oasa.cdml_presentation_properties.patch_arrow_properties(session, patch)
	second = _hydrate(session).presentation_objects[0]
	assert first is not second and first.object_id == second.object_id == "arrow1"
	assert second.effective_line_width == 3.0
