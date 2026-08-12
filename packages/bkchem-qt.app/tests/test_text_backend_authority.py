"""Focused backend-authority checks for plain Text creation."""

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import oasa.cdml_document
import oasa.cdml_presentation_insert
import oasa.cdml_writer
import oasa.safe_xml


_MIXED_CDML = '''<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml"
xmlns:vendor="urn:example:vendor" version="0.15"><bk:molecule id="molecule_1"><bk:atom
id="atom_1" name="C"><bk:point x="1cm" y="1cm" /></bk:atom></bk:molecule><bk:text
id="text_1"><bk:ftext>yield</bk:ftext></bk:text><vendor:note keep="yes">opaque
<vendor:child flag="keep" /></vendor:note></bk:cdml>'''


#============================================
#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, deliver)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(snapshot: object) -> object:
	"""Report one deliberately unavailable typed projection outcome."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
	)


def _direct_elements(root: object) -> list[object]:
	"""Return direct element children in source order."""
	children = [
		child for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE
	]
	return children


#============================================
def _text_child(
		element: object, name: str,
		) -> object:
	"""Return one direct named child from a CDML text element."""
	child = next(child for child in _direct_elements(element) if child.localName == name)
	return child


#============================================
def _text_value(element: object) -> str:
	"""Return one ftext node's semantic plain content."""
	ftext = _text_child(element, "ftext")
	value = "".join(child.data for child in ftext.childNodes if child.nodeType == child.TEXT_NODE)
	return value


#============================================
def test_text_insertion_preserves_existing_mixed_cdml() -> None:
	"""Text insertion retains ordered typed and opaque sibling semantics."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_MIXED_CDML)
	result = oasa.cdml_presentation_insert.insert_text(
		session,
		oasa.cdml_presentation_insert.CDMLTextInsertRequest(
			session.revision, (72.0, 36.0), "A & B",
		),
	)
	root = oasa.safe_xml.parse_dom_from_string(result.snapshot.cdml).documentElement
	elements = _direct_elements(root)
	vendor_note = elements[2]
	vendor_child = _direct_elements(vendor_note)[0]
	vendor_text = "".join(
		child.data for child in vendor_note.childNodes
		if child.nodeType == child.TEXT_NODE
	).strip()

	assert (
		{
			"ordered_children": [
				(element.localName, element.getAttribute("id"))
				for element in elements[:-1]
			],
			"existing_text": _text_value(elements[1]),
			"opaque_attribute": vendor_note.getAttribute("keep"),
			"opaque_text": vendor_text,
			"opaque_child": (
				vendor_child.localName, vendor_child.getAttribute("flag"),
			),
		}
		== {
			"ordered_children": [
				("molecule", "molecule_1"), ("text", "text_1"), ("note", ""),
			],
			"existing_text": "yield",
			"opaque_attribute": "yes",
			"opaque_text": "opaque",
			"opaque_child": ("child", "keep"),
		}
	)


#============================================
def test_text_insertion_uses_backend_id_and_canonical_plain_defaults() -> None:
	"""The accepted Text has a durable ID and semantic default presentation."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_MIXED_CDML)
	result = oasa.cdml_presentation_insert.insert_text(
		session,
		oasa.cdml_presentation_insert.CDMLTextInsertRequest(
			session.revision, (72.0, 36.0), "A & B",
		),
	)
	root = oasa.safe_xml.parse_dom_from_string(result.snapshot.cdml).documentElement
	new_text = _direct_elements(root)[-1]
	point = _text_child(new_text, "point")
	font = _text_child(new_text, "font")
	projected_point = (
		float(point.getAttribute("x")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
		float(point.getAttribute("y")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
	)

	assert new_text.getAttribute("id") == result.presentation_ids[0]
	assert (
		{
			"content": _text_value(new_text),
			"font": {
				name: font.getAttribute(name)
				for name in ("family", "size", "color")
			},
		}
		== {
			"content": "A & B",
			"font": {"family": "helvetica", "size": "12", "color": "#000000"},
		}
		and projected_point == pytest.approx((72.0, 36.0), abs=0.02)
	)


#============================================
def test_text_request_rejects_malformed_payload_without_backend_mutation(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Text only accepts exactly one stripped string and finite tuple position."""
	session = main_window._active_session
	before_revision = session.backend_snapshot.revision
	requests = (
		bkchem_qt.models.document_session.PersistentOperationRequest(
			"text.add", "Text", (("text", "plain"), ("position", (0.0, float("inf")))),
		),
		bkchem_qt.models.document_session.PersistentOperationRequest(
			"text.add", "Text", (("text", " plain"), ("position", (0.0, 0.0))),
		),
		bkchem_qt.models.document_session.PersistentOperationRequest(
			"text.add", "Text", (("text", "plain"), ("position", (0.0, 0.0)), ("extra", 1)),
		),
	)
	outcomes = [session.submit_persistent_operation(request) for request in requests]

	assert [outcome.status for outcome in outcomes] == ["rejected", "rejected", "rejected"]
	assert session.backend_snapshot.revision == before_revision


#============================================
def test_accepted_text_projection_retry_uses_current_snapshot_once(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An accepted Text commit retries its canonical snapshot without resubmitting."""
	main_window._on_new()
	session = main_window._active_session
	restore_delivery = lambda snapshot: main_window._replace_session_projection(session, snapshot)
	removed = False

	try:
		_install_projection_port(session, _projection_unavailable)
		request = bkchem_qt.models.document_session.PersistentOperationRequest(
			"text.add", "Text", (("text", "Retry me"), ("position", (18.0, 24.0))),
		)
		accepted = session.submit_persistent_operation(request)
		accepted_revision = session.backend_snapshot.revision
		_install_projection_port(session, restore_delivery)
		retry = session.retry_current_backend_projection()
		retried_revision = session.backend_snapshot.revision
		root = oasa.safe_xml.parse_dom_from_string(
			session.backend_snapshot.cdml,
		).documentElement
		texts = [element for element in _direct_elements(root) if element.localName == "text"]
	finally:
		if not session.is_disposed:
			_install_projection_port(session, restore_delivery)
			removed = main_window._remove_session(session)

	assert (accepted.status, accepted.submitted, retry.status) == (
		"unavailable", True, "accepted",
	)
	assert accepted_revision == retried_revision == 1
	assert _text_value(texts[-1]) == "Retry me" and removed
