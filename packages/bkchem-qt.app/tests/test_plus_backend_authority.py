"""Focused backend-authority checks for creation-only Plus placement."""

# Standard Library
import xml.dom.minidom

# PIP3 modules
import pytest
import PySide6.QtCore

# local repo modules
import bkchem_qt.io.cdml_candidate
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import oasa.cdml_document
import oasa.cdml_writer
import oasa.safe_xml


_MIXED_CDML = '''<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml"
xmlns:vendor="urn:example:vendor" version="0.15"><bk:molecule id="molecule_1"><bk:atom
id="atom_1" name="C"><bk:point x="1cm" y="1cm" /></bk:atom></bk:molecule><bk:text
id="text_1"><bk:ftext>yield</bk:ftext></bk:text><vendor:note keep="yes">opaque
<vendor:child flag="keep">child text</vendor:child></vendor:note></bk:cdml>'''


#============================================
def _direct_elements(root: xml.dom.minidom.Element) -> list[xml.dom.minidom.Element]:
	"""Return direct element children in source order."""
	children = [
		child for child in root.childNodes
		if isinstance(child, xml.dom.minidom.Element)
	]
	return children


#============================================
def _direct_child(
		element: xml.dom.minidom.Element, name: str,
		) -> xml.dom.minidom.Element:
	"""Return one direct child with the requested local name."""
	child = next(child for child in _direct_elements(element) if child.localName == name)
	return child


#============================================
def _text_value(element: xml.dom.minidom.Element) -> str:
	"""Return direct formatted-text content for one text record."""
	ftext = _direct_child(element, "ftext")
	value = "".join(
		child.data for child in ftext.childNodes if child.nodeType == child.TEXT_NODE
	)
	return value


#============================================
def _direct_text(element: xml.dom.minidom.Element) -> str:
	"""Return direct text while retaining nested opaque elements separately."""
	value = "".join(
		child.data for child in element.childNodes if child.nodeType == child.TEXT_NODE
	).strip()
	return value


#============================================
def _submit_rejected_plus_request(
		session: bkchem_qt.models.document_session.DocumentSession,
		payload: tuple[tuple[str, object], ...],
		) -> str:
	"""Return the public rejection route for one malformed Plus payload."""
	try:
		request = bkchem_qt.models.document_session.PersistentOperationRequest(
			"plus.add", "Plus", payload,
		)
	except TypeError:
		return "construction-rejected"
	outcome = session.submit_persistent_operation(request)
	return outcome.status


#============================================
def test_plus_candidate_preserves_mixed_cdml_and_uses_backend_identity() -> None:
	"""A Plus candidate preserves old semantics and appends one durable record."""
	token = "__bkchem_new__plus-r0-1"
	session = oasa.cdml_document.CDMLDocumentSession.load(_MIXED_CDML)
	candidate = bkchem_qt.io.cdml_candidate.append_plus_candidate(
		session.snapshot().cdml, token, (72.0, 36.0),
	)
	commit = session.commit(expected_revision=0, complete_cdml=candidate)
	elements = _direct_elements(
		oasa.safe_xml.parse_dom_from_string(commit.cdml).documentElement,
	)
	vendor_note = elements[2]
	vendor_child = _direct_elements(vendor_note)[0]
	plus = elements[-1]
	point = _direct_child(plus, "point")
	center = (
		float(point.getAttribute("x")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
		float(point.getAttribute("y")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
	)

	assert {
		"old_sibling_order": [
			(element.localName, element.getAttribute("id")) for element in elements[:-1]
		],
		"existing_text": _text_value(elements[1]),
		"opaque_parent": {
			"attribute": vendor_note.getAttribute("keep"), "text": _direct_text(vendor_note),
		},
		"opaque_child": {
			"local_name": vendor_child.localName,
			"attribute": vendor_child.getAttribute("flag"),
			"text": _direct_text(vendor_child),
		},
	} == {
		"old_sibling_order": [
			("molecule", "molecule_1"), ("text", "text_1"), ("note", ""),
		],
		"existing_text": "yield",
		"opaque_parent": {"attribute": "yes", "text": "opaque"},
		"opaque_child": {
			"local_name": "child", "attribute": "keep", "text": "child text",
		},
	}
	assert {
		"durable_id": plus.getAttribute("id"),
		"defaults": {
			"font_size": plus.getAttribute("font_size"), "color": plus.getAttribute("color"),
		},
		"center": center,
	} == {
		"durable_id": commit.id_map[token],
		"defaults": {"font_size": "18", "color": "#000000"},
		"center": pytest.approx((72.0, 36.0), abs=0.02),
	}


#============================================
@pytest.mark.parametrize("payload, expected_rejection", (
	((("position", (True, 2.0)),), "rejected"),
	((("position", [1.0, 2.0]),), "construction-rejected"),
	((("position", (1.0, float("nan"))),), "rejected"),
	((("position", (1.0, 2.0)), ("extra", 1)), "rejected"),
	((), "rejected"),
))
def test_plus_request_rejects_malformed_payload_without_backend_mutation(
		main_window: bkchem_qt.main_window.MainWindow,
		payload: tuple[tuple[str, object], ...], expected_rejection: str,
		) -> None:
	"""Malformed Plus payloads leave authority, history, and projection unchanged."""
	session = main_window._active_session
	before_snapshot = session.backend_snapshot
	before_document = session.document
	before_history = (session.can_undo_backend, session.can_redo_backend)
	before_synchronized = session.backend_projection_synchronized
	rejection = _submit_rejected_plus_request(session, payload)

	assert {
		"rejection": rejection,
		"snapshot": session.backend_snapshot,
		"history": (session.can_undo_backend, session.can_redo_backend),
		"projection": {
			"same_document": session.document is before_document,
			"synchronized": session.backend_projection_synchronized,
		},
	} == {
		"rejection": expected_rejection,
		"snapshot": before_snapshot,
		"history": before_history,
		"projection": {"same_document": True, "synchronized": before_synchronized},
	}


#============================================
def test_plus_mode_click_projects_backend_plus_without_qt_undo(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""One normal Plus click projects its canonical backend-owned glyph."""
	main_window._on_new()
	session = main_window._active_session
	removed = False
	try:
		main_window._mode_manager.set_mode("plus")
		mode = main_window._mode_manager.current_mode
		mode.mouse_press(PySide6.QtCore.QPointF(70.0, 80.0), object())
		plus_model = main_window.document.presentation_objects[-1]
		plus_item = next(
			item for item in session.scene.items()
			if getattr(item, "document_object_model", None) is plus_model
		)
		center = plus_item.pos() + plus_item.boundingRect().center()
		projected = {
			"kind": plus_model.kind,
			"durable_id": plus_model.object_id,
			"defaults": {
				"font_size": plus_model.attributes["font_size"],
				"color": plus_model.attributes["color"],
			},
			"glyph": plus_item.toPlainText(),
			"center": (center.x(), center.y()),
		}
		root = oasa.safe_xml.parse_dom_from_string(
			session.backend_snapshot.cdml,
		).documentElement
		root_tail = _direct_elements(root)[-1]
		if root_tail.localName != "plus":
			raise RuntimeError("Canonical backend snapshot did not end with a Plus record")
		canonical_point = _direct_child(root_tail, "point")
		canonical_center = (
			float(canonical_point.getAttribute("x")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
			float(canonical_point.getAttribute("y")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
		)
		canonical = {
			"kind": "plus",
			"durable_id": root_tail.getAttribute("id"),
			"defaults": {
				"font_size": root_tail.getAttribute("font_size"),
				"color": root_tail.getAttribute("color"),
			},
			"center": canonical_center,
		}
		qt_undo_available = main_window.document.undo_stack.canUndo()
	finally:
		removed = main_window._remove_session(session)

	assert {
		"canonical": canonical,
		"projected": projected,
	} == {
		"canonical": {
			"kind": "plus",
			"durable_id": canonical["durable_id"],
			"defaults": {"font_size": "18", "color": "#000000"},
			"center": pytest.approx((70.0, 80.0), abs=0.1),
		},
		"projected": {
			"kind": "plus",
			"durable_id": canonical["durable_id"],
			"defaults": {"font_size": "18", "color": "#000000"},
			"glyph": "+",
			"center": pytest.approx((70.0, 80.0), abs=0.1),
		},
	}
	assert not qt_undo_available and removed
