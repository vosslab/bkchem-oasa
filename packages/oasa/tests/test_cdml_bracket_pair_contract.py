"""Behavioral checks for the durable top-level CDML bracket-pair contract."""

# local repo modules
import oasa.cdml_document
import oasa.cdml_xml


_PAIR = (
	'<polyline id="left" bracket_pair="left" bracket_side="left" width="2" '
	'line_color="#123456" spline="no"><point x="0" y="0"/>'
	'<point x="0" y="1"/></polyline><polyline id="right" bracket_pair="left" '
	'bracket_side="right" width="2" line_color="#123456" spline="no">'
	'<point x="2" y="0"/><point x="2" y="1"/></polyline>'
)


#============================================
def test_fragment_copy_rewrites_a_complete_pair_to_its_allocated_left_id() -> None:
	"""A copied valid pair cannot retain a source-document membership reference."""
	session = oasa.cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = session.insert_top_level(oasa.cdml_document.CDMLTopLevelInsertionRequest(
		session.revision, f"<cdml>{_PAIR}</cdml>", (0.0, 0.0),
	))
	root = oasa.cdml_xml.parse_cdml_dom(commit.cdml.encode("utf-8")).documentElement
	polylines = tuple(
		child for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	assert (
		polylines[0].getAttribute("bracket_pair") == polylines[0].getAttribute("id")
		and polylines[1].getAttribute("bracket_pair") == polylines[0].getAttribute("id")
		and polylines[0].getAttribute("id") != "left"
	)


#============================================
def test_malformed_pair_markers_are_preserved_without_a_composite_fact() -> None:
	"""A duplicate-side marker remains individual compatible artwork, not a guess."""
	broken = _PAIR.replace('bracket_side="right"', 'bracket_side="left"')
	session = oasa.cdml_document.CDMLDocumentSession.load(f"<cdml>{broken}</cdml>")
	description = session.presentation_description(
		oasa.cdml_document.CDMLPresentationDescriptionQuery(session.revision),
	)
	assert not description.bracket_pairs and 'bracket_pair="left"' in session.snapshot().cdml


#============================================
def test_projection_plan_orders_only_valid_pair_facts_at_its_snapshot_revision() -> None:
	"""Projection receives exact source-ordered pair facts without parsing CDML."""
	second = _PAIR.replace('id="left"', 'id="left2"').replace(
		'id="right"', 'id="right2"',
	).replace('bracket_pair="left"', 'bracket_pair="left2"')
	broken = _PAIR.replace('id="left"', 'id="bad-left"').replace(
		'id="right"', 'id="bad-right"',
	).replace('bracket_pair="left"', 'bracket_pair="bad-left"').replace(
		'bracket_side="right"', 'bracket_side="left"', 1,
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(
		f"<cdml>{_PAIR}{broken}{second}</cdml>",
	)
	projection = session.projection_snapshot()
	assert (
		projection.plan.revision == projection.snapshot.revision
		and tuple(pair.pair_id for pair in projection.plan.presentation_description.bracket_pairs)
		== ("left", "left2")
	)


#============================================
def test_projection_plan_normalizes_bracket_appearance_with_other_roots() -> None:
	"""Bracket Configure and paint receive one normalized backend color fact."""
	short_color = _PAIR.replace("#123456", "#abc")
	session = oasa.cdml_document.CDMLDocumentSession.load(f"<cdml>{short_color}</cdml>")
	pair = session.projection_snapshot().plan.presentation_description.bracket_pairs[0]
	assert pair.line_color == "#aabbcc"


#============================================
def test_malformed_bracket_appearance_does_not_abort_the_projection_plan() -> None:
	"""A malformed member remains a root diagnostic, not a document-wide failure."""
	malformed = _PAIR.replace('line_color="#123456"', 'line_color="bad"', 1)
	session = oasa.cdml_document.CDMLDocumentSession.load(f"<cdml>{malformed}</cdml>")
	description = session.projection_snapshot().plan.presentation_description
	assert not description.bracket_pairs
	assert tuple(issue.identifier for issue in description.issues) == ("left",)
