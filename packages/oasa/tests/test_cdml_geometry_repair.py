"""Behavioral tests for backend-authoritative CDML geometry repair."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.cdml_xml
import oasa.cdml_writer
import oasa.atom_lib
import oasa.bond_lib
import oasa.hex_grid
import oasa.molecule_lib
import oasa.repair_ops


_REPAIR_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1" vendor-flag="keep">
  <atom id="a1" name="C"><point x="1cm" y="1cm" z="0cm"/><v:note>keep</v:note></atom>
  <atom id="a2" name="O"><point x="4cm" y="1cm"/></atom>
  <bond id="b1" start="a1" end="a2" type="n1" vendor-style="keep"/>
 </molecule>
 <arrow id="arrow1"><point x="1cm" y="2cm"/><point x="3cm" y="2cm"/></arrow>
 <v:opaque id="foreign1" value="keep"/>
</cdml>
"""

_OPAQUE_MOLECULE_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <v:molecule id="m1"><v:atom id="a1" name="C"><v:point x="1cm" y="1cm"/></v:atom><v:atom id="a2" name="O"><v:point x="4cm" y="1cm"/></v:atom><v:bond id="b1" start="a1" end="a2" type="n1"/></v:molecule>
</cdml>
"""

_CLEAN_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <!--keep-root--><molecule id="m1" vendor-flag="keep"><v:molecule-extension value="keep"/>
  <atom id="a1" name="C"><point x="1cm" y="1cm" z="7cm"/><v:note>keep</v:note></atom>
  <atom id="a2" name="O"><point x="4cm" y="1cm"/></atom>
  <atom id="a3" name="N"><point x="4cm" y="4cm"/></atom>
  <bond id="b1" start="a1" end="a2" type="n1" vendor-style="keep"/><bond id="b2" start="a2" end="a3" type="w1"/>
 </molecule><v:opaque id="foreign1" value="keep"/><arrow id="arrow1"><point x="1cm" y="2cm"/><point x="3cm" y="2cm"/></arrow>
</cdml>
"""

_MULTI_SNAP_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom><atom id="a2" name="O"><point x="4cm" y="1cm"/></atom><bond id="b1" start="a1" end="a2" type="n1"/></molecule>
 <molecule id="m2"><atom id="a3" name="N"><point x="7cm" y="3cm"/></atom><atom id="a4" name="C"><point x="10cm" y="3cm"/></atom><bond id="b2" start="a3" end="a4" type="n1"/></molecule>
</cdml>
"""

_SIMPLE_RING_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1"><atom id="a" name="C"><point x="0cm" y="0cm"/></atom><atom id="b" name="C"><point x="2cm" y="0cm"/></atom><atom id="c" name="C"><point x="1.5cm" y="1cm"/></atom><atom id="d" name="C"><point x="0cm" y="1cm"/></atom><bond id="ab" start="a" end="b" type="n1"/><bond id="bc" start="b" end="c" type="n1"/><bond id="cd" start="c" end="d" type="n1"/><bond id="da" start="d" end="a" type="n1"/></molecule></cdml>
"""


#============================================
def _repair_request(revision: int, target_length: float = 40.0) -> object:
	"""Create one valid normalized-length repair request."""
	return oasa.cdml_document.CDMLGeometryRepairRequest(
		expected_revision=revision,
		molecule_ids=("m1",),
		kind="normalize-bond-lengths",
		target_spacing_pt=target_length,
	)


#============================================
def _clean_request(revision: int, target_length: float = 40.0) -> object:
	"""Create one valid deterministic clean-geometry repair request."""
	return oasa.cdml_document.CDMLGeometryRepairRequest(
		expected_revision=revision, molecule_ids=("m1",), kind="clean-geometry",
		target_spacing_pt=target_length,
	)


#============================================
def _snap_request(
		revision: int, molecule_ids: tuple[str, ...] = ("m1",), spacing: float = 40.0,
		) -> object:
	"""Create one valid displayed-hex-lattice repair request."""
	return oasa.cdml_document.CDMLGeometryRepairRequest(
		expected_revision=revision,
		molecule_ids=molecule_ids,
		kind="snap-to-hex-grid",
		target_spacing_pt=spacing,
	)


#============================================
def _angle_request(
		revision: int, molecule_ids: tuple[str, ...] = ("m1",), spacing: float = 40.0,
		) -> object:
	"""Create one valid nearest-60-degree angle repair request."""
	return oasa.cdml_document.CDMLGeometryRepairRequest(
		expected_revision=revision,
		molecule_ids=molecule_ids,
		kind="normalize-bond-angles",
		target_spacing_pt=spacing,
	)


#============================================
def _straighten_request(
		revision: int, molecule_ids: tuple[str, ...] = ("m1",), spacing: float = 40.0,
		) -> object:
	"""Create one valid terminal-bond straighten request."""
	return oasa.cdml_document.CDMLGeometryRepairRequest(
		expected_revision=revision,
		molecule_ids=molecule_ids,
		kind="straighten-bonds",
		target_spacing_pt=spacing,
	)


#============================================
def _ring_request(
		revision: int, molecule_ids: tuple[str, ...] = ("m1",), spacing: float = 40.0,
		) -> object:
	"""Create one valid single-simple-ring normalization request."""
	return oasa.cdml_document.CDMLGeometryRepairRequest(
		expected_revision=revision,
		molecule_ids=molecule_ids,
		kind="normalize-rings",
		target_spacing_pt=spacing,
	)


#============================================
def _fingerprint(text: str) -> tuple:
	"""Return the hardened semantic fingerprint for accepted CDML."""
	return oasa.cdml_xml.inspect_cdml_xml(text.encode("utf-8")).semantic_fingerprint


#============================================
def _direct_atom_centroid_cm(text: str) -> tuple[float, float]:
	"""Read direct core atom coordinates after CDML-boundary parsing."""
	document = oasa.cdml_document.CDMLDocument.parse(text, validation="strict")
	root = document._dom_document.documentElement
	molecule = next(
		child for child in root.childNodes
		if (
			child.nodeType == child.ELEMENT_NODE
			and oasa.cdml_document._is_cdml_element(child)
			and child.localName == "molecule"
		)
	)
	coordinates = []
	for atom in molecule.childNodes:
		if (
			atom.nodeType != atom.ELEMENT_NODE
			or not oasa.cdml_document._is_cdml_element(atom)
			or atom.localName != "atom"
			):
			continue
		point = next(
			child for child in atom.childNodes
			if (
				child.nodeType == child.ELEMENT_NODE
				and oasa.cdml_document._is_cdml_element(child)
				and child.localName == "point"
			)
		)
		coordinates.append((
			float(point.getAttribute("x").removesuffix("cm")),
			float(point.getAttribute("y").removesuffix("cm")),
		))
	return (
		sum(x_value for x_value, _y_value in coordinates) / len(coordinates),
		sum(y_value for _x_value, y_value in coordinates) / len(coordinates),
	)


#============================================
def _direct_atom_points(text: str) -> tuple[tuple[float, float], ...]:
	"""Read every direct core atom coordinate after CDML-boundary parsing."""
	document = oasa.cdml_document.CDMLDocument.parse(text, validation="strict")
	coordinates = []
	for molecule in document._dom_document.documentElement.childNodes:
		if (
				molecule.nodeType != molecule.ELEMENT_NODE
				or not oasa.cdml_document._is_cdml_element(molecule)
				or molecule.localName != "molecule"
				):
			continue
		for atom in molecule.childNodes:
			if (
					atom.nodeType != atom.ELEMENT_NODE
					or not oasa.cdml_document._is_cdml_element(atom)
					or atom.localName != "atom"
					):
				continue
			point = next(
				child for child in atom.childNodes
				if (
					child.nodeType == child.ELEMENT_NODE
					and oasa.cdml_document._is_cdml_element(child)
					and child.localName == "point"
				)
			)
			coordinates.append((
				float(point.getAttribute("x").removesuffix("cm")) * oasa.cdml_writer.POINTS_PER_CM,
				float(point.getAttribute("y").removesuffix("cm")) * oasa.cdml_writer.POINTS_PER_CM,
			))
	return tuple(coordinates)


#============================================
def _direct_atom_coordinates_by_id(text: str) -> dict[str, tuple[float, float]]:
	"""Read direct core atom point coordinates by durable ID after CDML parsing."""
	document = oasa.cdml_document.CDMLDocument.parse(text, validation="strict")
	coordinates = {}
	for molecule in document._dom_document.documentElement.childNodes:
		if (
				molecule.nodeType != molecule.ELEMENT_NODE
				or not oasa.cdml_document._is_cdml_element(molecule)
				or molecule.localName != "molecule"
				):
			continue
		for atom in molecule.childNodes:
			if (
					atom.nodeType != atom.ELEMENT_NODE
					or not oasa.cdml_document._is_cdml_element(atom)
					or atom.localName != "atom"
					):
				continue
			point = next(
				child for child in atom.childNodes
				if (
					child.nodeType == child.ELEMENT_NODE
					and oasa.cdml_document._is_cdml_element(child)
					and child.localName == "point"
				)
			)
			coordinates[atom.getAttribute("id")] = (
				float(point.getAttribute("x").removesuffix("cm")) * oasa.cdml_writer.POINTS_PER_CM,
				float(point.getAttribute("y").removesuffix("cm")) * oasa.cdml_writer.POINTS_PER_CM,
			)
	return coordinates


#============================================
def _point_distance(points: dict[str, tuple[float, float]], first: str, second: str) -> float:
	"""Return Euclidean distance between two durable direct atom points."""
	dx = points[first][0] - points[second][0]
	dy = points[first][1] - points[second][1]
	distance = math.hypot(dx, dy)
	return distance


#============================================
def _normalized_direct_sequences(text: str, molecule_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	"""Return root and selected-molecule sequences after permitted point normalization.

	The input first crosses the hardened CDML boundary.  Only x/y attributes on
	direct core atom points of the selected molecule are normalized; every other
	attribute, child, comment, and direct-record order remains observable.
	"""
	document = oasa.cdml_document.CDMLDocument.parse(text, validation="strict")
	root = document._dom_document.documentElement
	molecule = next(
		child for child in root.childNodes
		if (
			child.nodeType == child.ELEMENT_NODE
			and oasa.cdml_document._is_cdml_element(child)
			and child.localName == "molecule"
			and child.getAttribute("id") == molecule_id
		)
	)
	for atom in molecule.childNodes:
		if (
			atom.nodeType != atom.ELEMENT_NODE
			or not oasa.cdml_document._is_cdml_element(atom)
			or atom.localName != "atom"
			):
			continue
		for point in atom.childNodes:
			if (
				point.nodeType == point.ELEMENT_NODE
				and oasa.cdml_document._is_cdml_element(point)
				and point.localName == "point"
				):
				point.setAttribute("x", "normalized")
				point.setAttribute("y", "normalized")
	return (
		tuple(child.toxml() for child in root.childNodes if child.nodeType != child.TEXT_NODE),
		tuple(child.toxml() for child in molecule.childNodes if child.nodeType != child.TEXT_NODE),
	)


#============================================
def _bond_angle_degrees(
		coordinates: dict[str, tuple[float, float]], start_id: str, end_id: str,
		) -> float:
	"""Return one direct point-to-point angle in canonical display degrees."""
	start = coordinates[start_id]
	end = coordinates[end_id]
	return math.degrees(math.atan2(end[1] - start[1], end[0] - start[0])) % 360.0


#============================================
def test_geometry_repair_changes_only_selected_molecule_coordinates() -> None:
	"""Normalization changes the selected molecule while preserving opaque content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_REPAIR_CDML)
	before = session.snapshot()
	result = session.repair_geometry(_repair_request(before.revision))

	assert result.changed and result.snapshot.revision == before.revision + 1
	assert 'x="2.411cm"' in result.snapshot.cdml and 'value="keep"' in result.snapshot.cdml


#============================================
@pytest.mark.parametrize(
	"request_builder",
	(
		lambda revision: oasa.cdml_document.CDMLGeometryRepairRequest(
			revision, ("missing",), "normalize-bond-lengths", 40.0,
		),
		lambda revision: oasa.cdml_document.CDMLGeometryRepairRequest(
			revision, ("m1", "m1"), "normalize-bond-lengths", 40.0,
		),
		lambda revision: oasa.cdml_document.CDMLGeometryRepairRequest(
			revision, ("m1", "missing"), "snap-to-hex-grid", 40.0,
		),
		lambda revision: oasa.cdml_document.CDMLGeometryRepairRequest(
			revision, ("m1",), "snap-to-hex-grid", math.inf,
		),
		lambda revision: oasa.cdml_document.CDMLGeometryRepairRequest(
			revision, ("m1", "missing"), "normalize-bond-angles", 40.0,
		),
	),
)
def test_geometry_repair_rejection_is_atomic(request_builder: object) -> None:
	"""Invalid targets and geometry leave the exact authoritative snapshot intact."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_REPAIR_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLDocumentError):
		session.repair_geometry(request_builder(before.revision))
	assert session.snapshot() == before


#============================================
def test_geometry_repair_never_targets_an_opaque_cdml_shaped_extension() -> None:
	"""A vendor molecule remains opaque even when its local names mimic CDML."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_OPAQUE_MOLECULE_CDML)
	before = session.snapshot()
	with pytest.raises(
			oasa.cdml_document.CDMLValidationError,
			match="direct-root molecule ID: m1",
		):
		session.repair_geometry(_repair_request(before.revision))

	assert session.snapshot() == before
	assert 'x="4cm"' in session.snapshot().cdml


#============================================
def test_geometry_repair_noop_keeps_revision_and_history() -> None:
	"""Already canonical coordinates produce an observation instead of fake history."""
	cdml_text = _REPAIR_CDML.replace('x="4cm"', 'x="2.411cm"')
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()
	result = session.repair_geometry(_repair_request(before.revision))

	assert not result.changed and result.commit is None
	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("request_builder", (_repair_request, _clean_request, _snap_request))
def test_geometry_repair_stale_request_preserves_authoritative_snapshot(
		request_builder: object,
		) -> None:
	"""A request from an older revision cannot overwrite a later accepted edit."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_REPAIR_CDML)
	session.repair_geometry(request_builder(session.revision))
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.repair_geometry(request_builder(0))
	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("request_builder", (_repair_request, _snap_request))
def test_geometry_repair_restore_recovers_original_authoritative_coordinates(
		request_builder: object,
		) -> None:
	"""Backend history, rather than a Qt move command, restores a changed repair."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_REPAIR_CDML)
	result = session.repair_geometry(request_builder(session.revision))
	restored = session.restore(target_revision=0, expected_revision=result.snapshot.revision)

	assert restored.revision == 2
	assert _fingerprint(restored.cdml) == _fingerprint(_REPAIR_CDML)


#============================================
def test_clean_geometry_preserves_centroid_extensions_and_non_xy_content() -> None:
	"""Backend cleaning changes only x/y while retaining complete CDML content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CLEAN_CDML)
	before = session.snapshot()
	result = session.repair_geometry(_clean_request(before.revision))

	assert result.changed
	assert '<v:molecule-extension value="keep"/>' in result.snapshot.cdml
	assert '<v:note>keep</v:note>' in result.snapshot.cdml
	assert 'z="7cm"' in result.snapshot.cdml
	assert 'vendor-style="keep"' in result.snapshot.cdml
	assert '<!--keep-root-->' in result.snapshot.cdml
	assert result.snapshot.cdml.index('foreign1') < result.snapshot.cdml.index('arrow1')
	assert _direct_atom_centroid_cm(result.snapshot.cdml) == pytest.approx((3.0, 2.0))


#============================================
def test_clean_geometry_preserves_direct_foreign_atom_lookalikes() -> None:
	"""Foreign direct atom-shaped children remain opaque while core atoms are repaired."""
	foreign_atom = '<v:atom id="vendor-a1"><v:point x="91cm" y="92cm"/></v:atom>'
	cdml_text = _CLEAN_CDML.replace('<v:molecule-extension value="keep"/>', foreign_atom)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()
	result = session.repair_geometry(_clean_request(before.revision))

	assert result.changed and _direct_atom_centroid_cm(result.snapshot.cdml) == (3.0, 2.0)
	assert foreign_atom in result.snapshot.cdml and foreign_atom in before.cdml


#============================================
def test_clean_geometry_second_request_is_a_backend_noop_and_restore_is_exact() -> None:
	"""A repeated deterministic clean avoids history and backend restore is exact."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CLEAN_CDML)
	first = session.repair_geometry(_clean_request(session.revision))
	second = session.repair_geometry(_clean_request(session.revision))

	assert first.changed and not second.changed and second.snapshot == first.snapshot
	restored = session.restore(target_revision=0, expected_revision=session.revision)
	assert _fingerprint(restored.cdml) == _fingerprint(_CLEAN_CDML)


#============================================
def test_clean_geometry_rejects_core_molecule_semantics_atomically() -> None:
	"""Clean M0 preserves foreign children but rejects unimplemented core semantics."""
	cdml_text = _CLEAN_CDML.replace(
		'<v:molecule-extension value="keep"/>', '<text id="label1">label</text>',
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLValidationError, match="direct core atom and bond"):
		session.repair_geometry(_clean_request(before.revision))
	assert session.snapshot() == before


#============================================
def test_hex_grid_snap_changes_only_coordinates_and_preserves_opaque_content() -> None:
	"""Snap accepts one detached changed document while retaining opaque CDML."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CLEAN_CDML)
	result = session.repair_geometry(_snap_request(session.revision))

	assert (
		result.changed,
		'<v:molecule-extension value="keep"/>' in result.snapshot.cdml,
		'<v:opaque id="foreign1" value="keep"/>' in result.snapshot.cdml,
	) == (True, True, True)


#============================================
def test_hex_grid_snap_preserves_direct_foreign_atom_lookalikes() -> None:
	"""Snap changes core points while preserving a foreign direct atom-shaped child."""
	foreign_atom = '<v:atom id="vendor-a1"><v:point x="91cm" y="92cm"/></v:atom>'
	cdml_text = _CLEAN_CDML.replace('<v:molecule-extension value="keep"/>', foreign_atom)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	result = session.repair_geometry(_snap_request(session.revision))

	assert result.changed and foreign_atom in result.snapshot.cdml


#============================================
def test_hex_grid_snap_lexical_noop_keeps_history_and_source_coordinate_spelling() -> None:
	"""A semantic lattice no-op does not rewrite an equivalent point spelling."""
	canonical = _REPAIR_CDML.replace('x="1cm" y="1cm"', 'x="1.222cm" y="0.706cm"')
	canonical = canonical.replace('x="4cm" y="1cm"', 'x="3.666cm" y="0.706cm"')
	lexical_noop = canonical.replace('x="1.222cm"', 'x="1.2220cm"')
	session = oasa.cdml_document.CDMLDocumentSession.load(lexical_noop)
	result = session.repair_geometry(_snap_request(session.revision))

	assert not result.changed and 'x="1.2220cm"' in result.snapshot.cdml


#============================================
def test_hex_grid_snap_uses_one_global_displayed_lattice_for_multiple_roots() -> None:
	"""Every selected root snaps to the same origin-zero displayed lattice."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_MULTI_SNAP_CDML)
	result = session.repair_geometry(_snap_request(session.revision, ("m1", "m2")))
	coordinates = _direct_atom_points(result.snapshot.cdml)

	assert result.changed and all(
		(x, y) == pytest.approx(
			oasa.hex_grid.snap_to_hex_grid(x, y, 40.0), abs=0.02,
		)
		for x, y in coordinates
	)


#============================================
def test_angle_repair_snaps_branches_and_translates_their_subtrees() -> None:
	"""A nearest-slot branch moves its already canonical two-level subtree rigidly."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom><atom id="a2" name="C"><point x="1.327cm" y="0.483cm"/></atom><atom id="a3" name="C"><point x="-0.706cm" y="1.222cm"/></atom><atom id="a4" name="C"><point x="2.033cm" y="1.705cm"/></atom><atom id="a5" name="C"><point x="3.444cm" y="1.705cm"/></atom>
<bond id="b1" start="a1" end="a2" type="n1"/><bond id="b2" start="a1" end="a3" type="n1"/><bond id="b3" start="a2" end="a4" type="n1"/><bond id="b4" start="a4" end="a5" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _direct_atom_coordinates_by_id(session.snapshot().cdml)
	result = session.repair_geometry(_angle_request(session.revision))
	after = _direct_atom_coordinates_by_id(result.snapshot.cdml)

	assert _bond_angle_degrees(after, "a1", "a2") == pytest.approx(0.0, abs=0.03)
	assert math.dist(after["a1"], after["a2"]) == pytest.approx(math.dist(before["a1"], before["a2"]), abs=0.02)
	assert all(
		(after[atom_id][0] - before[atom_id][0], after[atom_id][1] - before[atom_id][1])
		== pytest.approx(
			(after["a2"][0] - before["a2"][0], after["a2"][1] - before["a2"][1]),
			abs=0.02,
		)
		for atom_id in ("a4", "a5")
	)


#============================================
def test_angle_repair_uses_cdml_sibling_order_to_own_contested_slots() -> None:
	"""The first bond in CDML order owns a shared nearest 60-degree slot."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom><atom id="first" name="C"><point x="1.327cm" y="0.483cm"/></atom><atom id="second" name="C"><point x="1.389cm" y="0.245cm"/></atom><atom id="a4" name="C"><point x="-0.706cm" y="1.222cm"/></atom>
<bond id="b1" start="a1" end="first" type="n1"/><bond id="b2" start="a1" end="second" type="n1"/><bond id="b3" start="a1" end="a4" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	coordinates = _direct_atom_coordinates_by_id(
		session.repair_geometry(_angle_request(session.revision)).snapshot.cdml,
	)

	assert _bond_angle_degrees(coordinates, "a1", "first") == pytest.approx(0.0, abs=0.03)
	assert _bond_angle_degrees(coordinates, "a1", "second") == pytest.approx(60.0, abs=0.03)


#============================================
def test_angle_repair_preserves_triangle_ring_and_its_anchor_bond() -> None:
	"""A singly anchored branch keeps its ring edge fixed before moving outward."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom><atom id="a2" name="C"><point x="1.411cm" y="0cm"/></atom><atom id="a3" name="C"><point x="0.706cm" y="1.222cm"/></atom><atom id="s1" name="C"><point x="-1.058cm" y="0.706cm"/></atom><atom id="s2" name="C"><point x="-1.764cm" y="1.928cm"/></atom>
<bond id="b1" start="a1" end="a2" type="n1"/><bond id="b2" start="a2" end="a3" type="n1"/><bond id="b3" start="a3" end="a1" type="n1"/><bond id="b4" start="a1" end="s1" type="n1"/><bond id="b5" start="s1" end="s2" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _direct_atom_coordinates_by_id(session.snapshot().cdml)
	after = _direct_atom_coordinates_by_id(session.repair_geometry(_angle_request(session.revision)).snapshot.cdml)

	assert all(
		after[atom_id] == pytest.approx(before[atom_id], abs=0.02)
		for atom_id in ("a1", "a2", "a3", "s1")
	)
	assert math.dist(after["a1"], after["s1"]) == pytest.approx(
		math.dist(before["a1"], before["s1"]), abs=0.02,
	)


#============================================
def test_angle_repair_keeps_ring_anchors_fixed_from_a_non_ring_root() -> None:
	"""A degree-four root reserves one triangle anchor and moves a safe subtree."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="root" name="C"><point x="0cm" y="0cm"/></atom><atom id="ring1" name="C"><point x="1.411cm" y="0cm"/></atom><atom id="ring2" name="C"><point x="2.117cm" y="1.222cm"/></atom><atom id="ring3" name="C"><point x="2.822cm" y="0cm"/></atom><atom id="bridge" name="C"><point x="1.400cm" y="0.018cm"/></atom><atom id="deep1" name="C"><point x="2.811cm" y="0.018cm"/></atom><atom id="deep2" name="C"><point x="4.222cm" y="0.018cm"/></atom><atom id="branch2" name="C"><point x="0cm" y="1.411cm"/></atom><atom id="branch3" name="C"><point x="-0.706cm" y="-1.222cm"/></atom>
<bond id="b1" start="root" end="ring1" type="n1"/><bond id="b2" start="ring1" end="ring2" type="n1"/><bond id="b3" start="ring2" end="ring3" type="n1"/><bond id="b4" start="ring3" end="ring1" type="n1"/><bond id="b5" start="root" end="bridge" type="n1"/><bond id="b6" start="bridge" end="deep1" type="n1"/><bond id="b7" start="deep1" end="deep2" type="n1"/><bond id="b8" start="root" end="branch2" type="n1"/><bond id="b9" start="root" end="branch3" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _direct_atom_coordinates_by_id(session.snapshot().cdml)
	after = _direct_atom_coordinates_by_id(session.repair_geometry(_angle_request(session.revision)).snapshot.cdml)

	assert all(after[atom_id] == pytest.approx(before[atom_id], abs=0.02) for atom_id in ("ring1", "ring2", "ring3"))
	assert tuple(_bond_angle_degrees(after, "root", atom_id) for atom_id in ("bridge", "branch2", "branch3")) == pytest.approx((60.0, 120.0, 240.0), abs=0.03)
	assert all(
		(after[atom_id][0] - before[atom_id][0], after[atom_id][1] - before[atom_id][1])
		== pytest.approx(
			(after["bridge"][0] - before["bridge"][0], after["bridge"][1] - before["bridge"][1]),
			abs=0.02,
		)
		for atom_id in ("deep1", "deep2")
	)


#============================================
def test_angle_repair_keeps_deep_single_ring_anchor_fixed() -> None:
	"""A degree-dominant descendant cannot move its component's fixed ring edge."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="r1" name="C"><point x="0cm" y="0cm"/></atom><atom id="r2" name="C"><point x="1.411cm" y="0cm"/></atom><atom id="r3" name="C"><point x="0.706cm" y="1.222cm"/></atom><atom id="a" name="C"><point x="-1.222cm" y="0.706cm"/></atom><atom id="b" name="C"><point x="-2.550cm" y="0.223cm"/></atom><atom id="b1" name="C"><point x="-3.900cm" y="0.223cm"/></atom><atom id="b2" name="C"><point x="-2.550cm" y="1.550cm"/></atom><atom id="b3" name="C"><point x="-1.200cm" y="0.223cm"/></atom>
<bond id="r12" start="r1" end="r2" type="n1"/><bond id="r23" start="r2" end="r3" type="n1"/><bond id="r31" start="r3" end="r1" type="n1"/><bond id="ra" start="r1" end="a" type="n1"/><bond id="ab" start="a" end="b" type="n1"/><bond id="bb1" start="b" end="b1" type="n1"/><bond id="bb2" start="b" end="b2" type="n1"/><bond id="bb3" start="b" end="b3" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _direct_atom_coordinates_by_id(session.snapshot().cdml)
	after = _direct_atom_coordinates_by_id(session.repair_geometry(_angle_request(session.revision)).snapshot.cdml)

	assert all(
		after[atom_id] == pytest.approx(before[atom_id], abs=0.02)
		for atom_id in ("r1", "r2", "r3", "a")
	)
	assert (
		math.dist(after["r1"], after["a"]),
		_bond_angle_degrees(after, "a", "b"),
	) == pytest.approx((math.dist(before["r1"], before["a"]), 180.0), abs=0.03)


#============================================
def test_angle_repair_advances_exact_half_slots_toward_increasing_angles() -> None:
	"""The public session rounds exact half slots forward around zero degrees."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="root" name="C"><point x="0" y="0"/></atom><atom id="a30" name="C"><point x="34.64101615137755" y="20"/></atom><atom id="a90" name="C"><point x="0" y="40"/></atom><atom id="a330" name="C"><point x="34.64101615137755" y="-20"/></atom>
<bond id="b1" start="root" end="a30" type="n1"/><bond id="b2" start="root" end="a90" type="n1"/><bond id="b3" start="root" end="a330" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	result = session.repair_geometry(_angle_request(session.revision))
	points = _direct_atom_coordinates_by_id(result.snapshot.cdml)

	assert result.changed
	assert tuple(_bond_angle_degrees(points, "root", atom_id) for atom_id in ("a30", "a90", "a330")) == pytest.approx((60.0, 120.0, 0.0), abs=0.03)


#============================================
def test_angle_repair_keeps_distinct_sides_of_a_half_slot_nearest() -> None:
	"""Represented angles on either side of 30 degrees keep their true nearest slots."""
	half_slot_delta = 5e-13
	below_half_angle = math.pi / 6.0 - half_slot_delta
	above_half_angle = math.pi / 6.0 + half_slot_delta
	bond_length = 40.0
	cdml_text = f"""\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="root" name="C"><point x="0" y="0"/></atom><atom id="below" name="C"><point x="{bond_length * math.cos(below_half_angle):.17g}" y="{bond_length * math.sin(below_half_angle):.17g}"/></atom><atom id="above" name="C"><point x="{bond_length * math.cos(above_half_angle):.17g}" y="{bond_length * math.sin(above_half_angle):.17g}"/></atom>
<bond id="b1" start="root" end="below" type="n1"/><bond id="b2" start="root" end="above" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _direct_atom_coordinates_by_id(session.snapshot().cdml)
	result = session.repair_geometry(_angle_request(session.revision))
	after = _direct_atom_coordinates_by_id(result.snapshot.cdml)

	assert _bond_angle_degrees(before, "root", "below") < 30.0
	assert _bond_angle_degrees(before, "root", "above") > 30.0
	assert tuple(_bond_angle_degrees(after, "root", atom_id) for atom_id in ("below", "above")) == pytest.approx((0.0, 60.0), abs=0.03)


#============================================
def test_angle_repair_uses_spacing_for_degenerate_sibling_vectors() -> None:
	"""Degenerate siblings use the request spacing and successive free slots."""
	degenerate = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1"><atom id="a1" name="C"><point x="0cm" y="0cm"/></atom><atom id="a2" name="C"><point x="0cm" y="0cm"/></atom><atom id="a3" name="C"><point x="0cm" y="0cm"/></atom><bond id="b1" start="a1" end="a2" type="n1"/><bond id="b2" start="a1" end="a3" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(degenerate)
	points = _direct_atom_coordinates_by_id(session.repair_geometry(_angle_request(session.revision)).snapshot.cdml)

	assert points["a2"] == pytest.approx((40.0, 0.0), abs=0.02) and points["a3"] == pytest.approx((20.0, 34.641), abs=0.02)


#============================================
def test_angle_repair_reserves_the_incoming_edge_slot() -> None:
	"""A descendant advances forward rather than collapsing onto its ancestor."""
	collision = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1"><atom id="a1" name="C"><point x="0cm" y="0cm"/></atom><atom id="a4" name="C"><point x="1.411cm" y="0cm"/></atom><atom id="a5" name="C"><point x="0.706cm" y="1.222cm"/></atom><atom id="a6" name="C"><point x="-0.706cm" y="1.222cm"/></atom><atom id="a3" name="C"><point x="0.085cm" y="0.483cm"/></atom><bond id="b1" start="a1" end="a4" type="n1"/><bond id="b2" start="a1" end="a5" type="n1"/><bond id="b3" start="a1" end="a6" type="n1"/><bond id="b4" start="a4" end="a3" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(collision)
	points = _direct_atom_coordinates_by_id(session.repair_geometry(_angle_request(session.revision)).snapshot.cdml)
	assert _bond_angle_degrees(points, "a4", "a3") == pytest.approx(240.0, abs=0.03)
	assert points["a3"] == pytest.approx((20.0, -34.641), abs=0.03)


#============================================
def test_angle_repair_rejects_a_non_ring_component_with_two_ring_anchors_atomically() -> None:
	"""A bridge between two fixed rings is rejected before either target changes."""
	eligible = """\
<molecule id="m1"><atom id="m1a" name="C"><point x="0cm" y="0cm"/></atom><atom id="m1b" name="C"><point x="1.222cm" y="0.706cm"/></atom><bond id="m1bond" start="m1a" end="m1b" type="n1"/></molecule>
"""
	constrained = """\
<molecule id="m2"><atom id="r1" name="C"><point x="0cm" y="0cm"/></atom><atom id="r2" name="C"><point x="1.411cm" y="0cm"/></atom><atom id="r3" name="C"><point x="0.706cm" y="1.222cm"/></atom><atom id="r4" name="C"><point x="5cm" y="0cm"/></atom><atom id="r5" name="C"><point x="6.411cm" y="0cm"/></atom><atom id="r6" name="C"><point x="5.706cm" y="1.222cm"/></atom><atom id="bridge" name="C"><point x="2.500cm" y="0cm"/></atom><bond id="r1b1" start="r1" end="r2" type="n1"/><bond id="r1b2" start="r2" end="r3" type="n1"/><bond id="r1b3" start="r3" end="r1" type="n1"/><bond id="r2b1" start="r4" end="r5" type="n1"/><bond id="r2b2" start="r5" end="r6" type="n1"/><bond id="r2b3" start="r6" end="r4" type="n1"/><bond id="bridge1" start="r1" end="bridge" type="n1"/><bond id="bridge2" start="bridge" end="r4" type="n1"/></molecule>
"""
	cdml_text = (
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">'
		+ eligible + constrained + '</cdml>'
	)
	document = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	constrained_element = next(
		child for child in document._dom_document.documentElement.childNodes
		if (
			child.nodeType == child.ELEMENT_NODE
			and oasa.cdml_document._is_cdml_element(child)
			and child.getAttribute("id") == "m2"
		)
	)
	direct_molecule = oasa.cdml_writer.read_direct_core_cdml_molecule_element(constrained_element)
	with pytest.raises(
			ValueError,
			match="non-ring component attached to multiple ring anchors",
		):
		oasa.repair_ops.normalize_bond_angles(direct_molecule, 40.0)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()
	request = _angle_request(before.revision, molecule_ids=("m1", "m2"))

	with pytest.raises(
			oasa.cdml_document.CDMLValidationError,
			match="non-ring component attached to multiple ring anchors",
		):
		session.repair_geometry(request)
	assert session.snapshot() == before


#============================================
def test_angle_repair_preserves_opaque_non_targets_and_has_canonical_noop() -> None:
	"""Only selected core x/y changes; repeated repair is history-free."""
	other = '<molecule id="m2"><atom id="x1" name="C"><point x="9cm" y="9cm"/></atom><atom id="x2" name="C"><point x="10cm" y="9cm"/></atom><bond id="x3" start="x1" end="x2" type="n1"/></molecule>'
	session = oasa.cdml_document.CDMLDocumentSession.load(_CLEAN_CDML.replace('</cdml>', other + '</cdml>'))
	before = session.snapshot()
	before_sequences = _normalized_direct_sequences(before.cdml, "m1")
	first = session.repair_geometry(_angle_request(session.revision))
	second = session.repair_geometry(_angle_request(session.revision))

	assert _normalized_direct_sequences(first.snapshot.cdml, "m1") == before_sequences
	assert not second.changed and second.commit is None and second.snapshot == first.snapshot and second.snapshot.revision == first.snapshot.revision == before.revision + 1


#============================================
def test_angle_repair_uses_spacing_only_for_degenerate_vectors() -> None:
	"""Changing spacing leaves a fully nondegenerate angle repair unchanged."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom><atom id="a2" name="C"><point x="1.327cm" y="0.483cm"/></atom><atom id="a3" name="C"><point x="-0.706cm" y="1.222cm"/></atom>
<bond id="b1" start="a1" end="a2" type="n1"/><bond id="b2" start="a1" end="a3" type="n1"/></molecule></cdml>
"""
	first = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	second = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	coordinates_40 = _direct_atom_coordinates_by_id(
		first.repair_geometry(_angle_request(first.revision, spacing=40.0)).snapshot.cdml,
	)
	coordinates_90 = _direct_atom_coordinates_by_id(
		second.repair_geometry(_angle_request(second.revision, spacing=90.0)).snapshot.cdml,
	)

	assert coordinates_90 == pytest.approx(coordinates_40, abs=0.02)


#============================================
def test_angle_repair_rejects_exhausted_root_and_non_root_slots_atomically() -> None:
	"""More than six occupied 60-degree slots is a typed atomic rejection."""
	root_atoms = ''.join(
		f'<atom id="a{index}" name="C"><point x="{index}cm" y="0cm"/></atom>'
		for index in range(1, 8)
	)
	root_bonds = ''.join(
		f'<bond id="b{index}" start="root" end="a{index}" type="n1"/>'
		for index in range(1, 8)
	)
	root_overflow = (
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">'
		f'<atom id="root" name="C"><point x="0cm" y="0cm"/></atom>{root_atoms}{root_bonds}</molecule></cdml>'
	)
	root_leaf_atoms = ''.join(
		f'<atom id="r{index}" name="C"><point x="{index}cm" y="1cm"/></atom>'
		for index in range(1, 6)
	)
	root_leaf_bonds = ''.join(
		f'<bond id="rb{index}" start="root" end="r{index}" type="n1"/>'
		for index in range(1, 6)
	)
	child_atoms = ''.join(
		f'<atom id="c{index}" name="C"><point x="{index}cm" y="1cm"/></atom>'
		for index in range(1, 7)
	)
	child_bonds = ''.join(
		f'<bond id="cb{index}" start="parent" end="c{index}" type="n1"/>'
		for index in range(1, 7)
	)
	non_root_overflow = (
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">'
		'<atom id="root" name="C"><point x="0cm" y="0cm"/></atom>'
		'<atom id="ring1" name="C"><point x="1cm" y="1cm"/></atom>'
		'<atom id="ring2" name="C"><point x="-1cm" y="1cm"/></atom>'
		f'<atom id="parent" name="C"><point x="1cm" y="0cm"/></atom>{root_leaf_atoms}{child_atoms}'
		'<bond id="ring-b1" start="root" end="ring1" type="n1"/>'
		'<bond id="ring-b2" start="ring1" end="ring2" type="n1"/>'
		'<bond id="ring-b3" start="ring2" end="root" type="n1"/>'
		f'<bond id="rp" start="root" end="parent" type="n1"/>{root_leaf_bonds}{child_bonds}'
		'</molecule></cdml>'
	)
	for cdml_text in (root_overflow, non_root_overflow):
		session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
		before = session.snapshot()
		with pytest.raises(oasa.cdml_document.CDMLValidationError, match="no free 60-degree slot"):
			session.repair_geometry(_angle_request(before.revision))
		assert session.snapshot() == before


#============================================
def test_angle_repair_stale_request_and_restore_are_authoritative() -> None:
	"""Angle commits reject stale input and restore through retained backend history."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CLEAN_CDML)
	session.repair_geometry(_angle_request(session.revision))
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.repair_geometry(_angle_request(0))
	stale_preserved = session.snapshot() == before
	restored = session.restore(target_revision=0, expected_revision=before.revision)

	assert stale_preserved and restored.revision == before.revision + 1
	assert _fingerprint(restored.cdml) == _fingerprint(_CLEAN_CDML)


#============================================
def test_straighten_bonds_uses_durable_id_not_source_order_for_two_atom_component() -> None:
	"""A reversed two-atom source keeps the lexically first durable endpoint fixed."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="b" name="C"><point x="1.327cm" y="0.483cm"/></atom><atom id="a" name="C"><point x="0cm" y="0cm"/></atom>
<bond id="b1" start="a" end="b" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _direct_atom_coordinates_by_id(session.snapshot().cdml)
	after = _direct_atom_coordinates_by_id(
		session.repair_geometry(_straighten_request(session.revision)).snapshot.cdml,
	)

	assert after["a"] == pytest.approx(before["a"], abs=0.02)
	assert _bond_angle_degrees(after, "a", "b") == pytest.approx(30.0, abs=0.03)


#============================================
def test_straighten_bonds_advances_exact_half_slots_toward_increasing_angle() -> None:
	"""Terminal +15, -15, and 345-degree vectors use the documented tie rule."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="root" name="C"><point x="0cm" y="0cm"/></atom><atom id="plus" name="C"><point x="0.965925826289cm" y="0.258819045103cm"/></atom><atom id="minus" name="C"><point x="0.965925826289cm" y="-0.258819045103cm"/></atom><atom id="three45" name="C"><point x="1.931851652578cm" y="-0.517638090206cm"/></atom>
<bond id="b1" start="root" end="plus" type="n1"/><bond id="b2" start="root" end="minus" type="n1"/><bond id="b3" start="root" end="three45" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	coordinates = _direct_atom_coordinates_by_id(
		session.repair_geometry(_straighten_request(session.revision)).snapshot.cdml,
	)
	angles = tuple(
		_bond_angle_degrees(coordinates, "root", atom_id)
		for atom_id in ("plus", "minus", "three45")
	)

	assert angles == pytest.approx((30.0, 0.0, 0.0), abs=0.03)


#============================================
def test_straighten_bonds_resolves_half_slot_boundary_through_backend_request() -> None:
	"""Public repair keeps the lower side below 15 degrees and advances the tie."""
	delta = 1e-6
	coordinates = tuple(
		(math.cos(math.pi / 12.0 + offset), math.sin(math.pi / 12.0 + offset))
		for offset in (-delta, 0.0, delta)
	)
	atom_xml = ''.join(
		'<atom id="a%s" name="C"><point x="%.12fcm" y="%.12fcm"/></atom>' % (
			index, x_value, y_value,
		)
		for index, (x_value, y_value) in enumerate(coordinates, start=1)
	)
	bond_xml = ''.join(
		'<bond id="b%s" start="root" end="a%s" type="n1"/>' % (index, index)
		for index in range(1, 4)
	)
	cdml_text = (
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">'
		'<molecule id="m1"><atom id="root" name="C"><point x="0cm" y="0cm"/></atom>'
		+ atom_xml + bond_xml + '</molecule></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	after = _direct_atom_coordinates_by_id(
		session.repair_geometry(_straighten_request(session.revision)).snapshot.cdml,
	)
	angles = tuple(_bond_angle_degrees(after, "root", "a%s" % index) for index in range(1, 4))

	assert angles == pytest.approx((0.0, 30.0, 30.0), abs=0.03)


#============================================
def test_straighten_bonds_moves_branch_and_ring_terminal_without_moving_anchors() -> None:
	"""Only degree-one endpoints move; a branch center and ring stay fixed."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="r1" name="C"><point x="0cm" y="0cm"/></atom><atom id="r2" name="C"><point x="1cm" y="0cm"/></atom><atom id="r3" name="C"><point x="0.5cm" y="0.866cm"/></atom><atom id="terminal" name="C"><point x="-0.940cm" y="0.342cm"/></atom>
<bond id="b1" start="r1" end="r2" type="n1"/><bond id="b2" start="r2" end="r3" type="n1"/><bond id="b3" start="r3" end="r1" type="n1"/><bond id="b4" start="r1" end="terminal" type="n1"/></molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _direct_atom_coordinates_by_id(session.snapshot().cdml)
	after = _direct_atom_coordinates_by_id(
		session.repair_geometry(_straighten_request(session.revision)).snapshot.cdml,
	)

	assert all(after[atom_id] == pytest.approx(before[atom_id], abs=0.02) for atom_id in ("r1", "r2", "r3"))
	assert _bond_angle_degrees(after, "r1", "terminal") == pytest.approx(150.0, abs=0.03)


#============================================
def test_straighten_bonds_preserves_complete_cdml_outside_selected_point_xy() -> None:
	"""A committed repair retains root order, metadata, and an unselected molecule."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
<!--root-comment--><molecule id="m1" vendor-flag="keep"><atom id="a1" name="C" atom-flag="keep"><point x="1cm" y="1cm" z="7cm" point-flag="keep"/><v:note>keep</v:note></atom><atom id="a2" name="O"><point x="3.819cm" y="2.026cm"/></atom><bond id="b1" start="a1" end="a2" type="n1" bond-flag="keep"/></molecule>
<arrow id="arrow1" arrow-flag="keep"><point x="1cm" y="2cm"/></arrow><v:opaque id="foreign1" value="keep"/><molecule id="m2"><atom id="u1" name="C"><point x="10cm" y="0cm"/></atom><atom id="u2" name="O"><point x="11cm" y="0cm"/></atom><bond id="ub1" start="u1" end="u2" type="n1"/></molecule>
</cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	result = session.repair_geometry(_straighten_request(session.revision))

	assert result.changed
	assert _normalized_direct_sequences(result.snapshot.cdml, "m1") == _normalized_direct_sequences(cdml_text, "m1")


#============================================
def test_straighten_bonds_degenerate_and_repeated_requests_are_backend_noops() -> None:
	"""Degenerate terminals stay fixed, and canonical repeated repair has no history entry."""
	degenerate = _REPAIR_CDML.replace('x="4cm" y="1cm"', 'x="1cm" y="1cm"')
	first_session = oasa.cdml_document.CDMLDocumentSession.load(degenerate)
	first = first_session.repair_geometry(_straighten_request(first_session.revision))
	canonical = _REPAIR_CDML.replace('x="4cm" y="1cm"', 'x="3.598cm" y="2.500cm"')
	second_session = oasa.cdml_document.CDMLDocumentSession.load(canonical)
	second = second_session.repair_geometry(_straighten_request(second_session.revision))

	assert not first.changed and first.snapshot == first_session.snapshot()
	assert not second.changed and second.commit is None


#============================================
def test_straighten_bonds_rejects_stale_or_invalid_targets_and_restores_backend_history() -> None:
	"""Invalid and stale requests are atomic; an accepted repair restores through OASA history."""
	cdml_text = _REPAIR_CDML.replace('x="4cm" y="1cm"', 'x="3.819cm" y="2.026cm"')
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.repair_geometry(_straighten_request(before.revision, ("missing",)))
	invalid_preserved = session.snapshot() == before
	changed = session.repair_geometry(_straighten_request(session.revision))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.repair_geometry(_straighten_request(before.revision))
	stale_preserved = session.snapshot() == changed.snapshot
	restored = session.restore(target_revision=0, expected_revision=session.revision)

	assert invalid_preserved and stale_preserved
	assert _fingerprint(restored.cdml) == _fingerprint(cdml_text)


#============================================
def test_straighten_bonds_rejects_mixed_eligible_and_ineligible_targets_atomically() -> None:
	"""A bad second target leaves the otherwise eligible first target unchanged."""
	cdml_text = _MULTI_SNAP_CDML.replace(
		'x="4cm" y="1cm"', 'x="3.819cm" y="2.026cm"',
	).replace(
		'</cdml>', '<molecule id="m3"><atom id="bad" name="C"><point x="0cm" y="0cm"/></atom></molecule></cdml>',
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLValidationError, match="bonded direct-atom molecule"):
		session.repair_geometry(_straighten_request(before.revision, ("m1", "m3")))

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("identifiers", ((None, None), ("same", "same")))
def test_straighten_bonds_uses_authored_order_without_unambiguous_oasa_ids(
		identifiers: tuple[str | None, str | None],
		) -> None:
	"""Pure OASA keeps the first authored endpoint fixed without a unique ID order."""
	molecule = oasa.molecule_lib.Molecule()
	first = oasa.atom_lib.Atom(symbol="C", coords=(0.0, 0.0, 0.0))
	second = oasa.atom_lib.Atom(symbol="C", coords=(1.327, 0.483, 0.0))
	first.id, second.id = identifiers
	molecule.add_vertex(first)
	molecule.add_vertex(second)
	molecule.add_edge(first, second, oasa.bond_lib.Bond(order=1, type="n"))
	before = (first.x, first.y)
	oasa.repair_ops.straighten_bonds(molecule)

	assert (first.x, first.y) == before
	assert math.degrees(math.atan2(second.y - first.y, second.x - first.x)) == pytest.approx(30.0, abs=1e-9)


#============================================
def test_straighten_bonds_cdml_requires_a_durable_atom_id() -> None:
	"""A repair rejects a missing persistent atom identity without a mutation."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom name="C"><point x="0cm" y="0cm"/></atom><atom id="a2" name="C"><point x="1.327cm" y="0.483cm"/></atom><bond id="b1" start="" end="a2" type="n1"/>
</molecule></cdml>
"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLValidationError, match="unique durable atom IDs"):
		session.repair_geometry(_straighten_request(before.revision))

	assert session.snapshot() == before


#============================================
def test_straighten_bonds_cdml_rejects_ambiguous_durable_atom_ids_at_load() -> None:
	"""Strict CDML rejects ambiguous persistent IDs before a repair can be requested."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">
<atom id="same" name="C"><point x="0cm" y="0cm"/></atom><atom id="same" name="C"><point x="1.327cm" y="0.483cm"/></atom><bond id="b1" start="same" end="same" type="n1"/>
</molecule></cdml>
"""

	with pytest.raises(oasa.cdml_document.CDMLValidationError, match="duplicate CDML id"):
		oasa.cdml_document.CDMLDocumentSession.load(cdml_text)


#============================================
def test_normalize_rings_regularizes_one_ring_and_translates_its_substituent() -> None:
	"""One accepted repair preserves centroid, opaque XML, and anchor displacement."""
	cdml_text = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
<molecule id="m1"><atom id="a" name="C"><point x="0cm" y="0cm"/></atom><atom id="b" name="C"><point x="2cm" y="0cm"/></atom><atom id="c" name="C"><point x="1.5cm" y="1cm"/></atom><atom id="d" name="C"><point x="0cm" y="1cm"/></atom><atom id="side" name="O"><point x="-1cm" y="1cm"/></atom><bond id="ab" start="a" end="b" type="n1"/><bond id="bc" start="b" end="c" type="n1"/><bond id="cd" start="c" end="d" type="n1"/><bond id="da" start="d" end="a" type="n1"/><bond id="ds" start="d" end="side" type="n1"/><v:note>keep</v:note></molecule><v:opaque id="outside">keep</v:opaque>
</cdml>"""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _direct_atom_coordinates_by_id(session.snapshot().cdml)
	result = session.repair_geometry(_ring_request(session.revision))
	after = _direct_atom_coordinates_by_id(result.snapshot.cdml)
	before_centroid = tuple(sum(before[key][axis] for key in "abcd") / 4.0 for axis in (0, 1))
	after_centroid = tuple(sum(after[key][axis] for key in "abcd") / 4.0 for axis in (0, 1))

	geometry_preserved = (
		_point_distance(after, "a", "b") == pytest.approx(40.0, abs=0.02)
		and after_centroid == pytest.approx(before_centroid, abs=0.02)
		and (after["side"][0] - before["side"][0], after["side"][1] - before["side"][1])
		== pytest.approx((after["d"][0] - before["d"][0], after["d"][1] - before["d"][1]), abs=0.02)
	)
	opaque_preserved = '<v:note>keep</v:note>' in result.snapshot.cdml and '<v:opaque id="outside">keep</v:opaque>' in result.snapshot.cdml

	assert geometry_preserved
	assert opaque_preserved


#============================================
def test_normalize_rings_is_deterministic_across_authored_atom_and_bond_order() -> None:
	"""Durable IDs, rather than XML order, choose the normalized coordinate map."""
	atoms = '<atom id="a" name="C"><point x="0cm" y="0cm"/></atom><atom id="b" name="C"><point x="2cm" y="0cm"/></atom><atom id="c" name="C"><point x="1.5cm" y="1cm"/></atom><atom id="d" name="C"><point x="0cm" y="1cm"/></atom>'
	bonds = '<bond id="ab" start="a" end="b" type="n1"/><bond id="bc" start="b" end="c" type="n1"/><bond id="cd" start="c" end="d" type="n1"/><bond id="da" start="d" end="a" type="n1"/>'
	first = '<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">' + atoms + bonds + '</molecule></cdml>'
	second = '<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"><molecule id="m1">' + atoms + bonds + '</molecule></cdml>'
	second = second.replace(atoms, '<atom id="d" name="C"><point x="0cm" y="1cm"/></atom><atom id="c" name="C"><point x="1.5cm" y="1cm"/></atom><atom id="b" name="C"><point x="2cm" y="0cm"/></atom><atom id="a" name="C"><point x="0cm" y="0cm"/></atom>')
	second = second.replace(bonds, '<bond id="da" start="d" end="a" type="n1"/><bond id="cd" start="c" end="d" type="n1"/><bond id="bc" start="b" end="c" type="n1"/><bond id="ab" start="a" end="b" type="n1"/>')
	first_session = oasa.cdml_document.CDMLDocumentSession.load(first)
	second_session = oasa.cdml_document.CDMLDocumentSession.load(second)
	first_result = first_session.repair_geometry(_ring_request(first_session.revision))
	second_result = second_session.repair_geometry(_ring_request(second_session.revision))

	assert _direct_atom_coordinates_by_id(first_result.snapshot.cdml) == pytest.approx(_direct_atom_coordinates_by_id(second_result.snapshot.cdml), abs=0.02)


#============================================
def test_normalize_rings_repeated_stale_and_restore_requests_follow_backend_history() -> None:
	"""A ring commit is final, repeat is history-free, and stale input cannot overwrite it."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_SIMPLE_RING_CDML)
	first = session.repair_geometry(_ring_request(session.revision))
	second = session.repair_geometry(_ring_request(session.revision))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.repair_geometry(_ring_request(0))
	stale_preserved = session.snapshot() == second.snapshot
	restored = session.restore(target_revision=0, expected_revision=session.revision)

	assert not second.changed and second.commit is None and second.snapshot == first.snapshot and stale_preserved
	assert _fingerprint(restored.cdml) == _fingerprint(_SIMPLE_RING_CDML)


#============================================
def test_normalize_rings_no_ring_is_a_semantic_noop() -> None:
	"""A molecule without a cycle needs neither a revision nor a history entry."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_REPAIR_CDML)
	before = session.snapshot()
	result = session.repair_geometry(_ring_request(before.revision))

	assert not result.changed and result.commit is None
	assert result.snapshot == before


#============================================
@pytest.mark.parametrize("bonds", (
	('<bond id="b1" start="r1" end="r2" type="n1"/><bond id="b2" start="r2" end="r3" type="n1"/><bond id="b3" start="r3" end="r1" type="n1"/><bond id="b4" start="r2" end="r4" type="n1"/><bond id="b5" start="r4" end="r5" type="n1"/><bond id="b6" start="r5" end="r2" type="n1"/>'),
	('<bond id="b1" start="r1" end="r2" type="n1"/><bond id="b2" start="r2" end="r3" type="n1"/><bond id="b3" start="r3" end="r1" type="n1"/><bond id="b4" start="r1" end="r4" type="n1"/><bond id="b5" start="r4" end="r2" type="n1"/>'),
	('<bond id="b1" start="r1" end="r2" type="n1"/><bond id="b2" start="r2" end="r3" type="n1"/><bond id="b3" start="r3" end="r4" type="n1"/><bond id="b4" start="r4" end="r1" type="n1"/><bond id="b5" start="r1" end="r3" type="n1"/>'),
))
def test_normalize_rings_rejects_multi_cycle_topology_atomically(bonds: str) -> None:
	"""A bad second graph preserves an otherwise eligible first ring snapshot."""
	atoms = '<atom id="r1" name="C"><point x="0cm" y="0cm"/></atom><atom id="r2" name="C"><point x="1cm" y="0cm"/></atom><atom id="r3" name="C"><point x="0.5cm" y="1cm"/></atom><atom id="r4" name="C"><point x="2cm" y="0cm"/></atom><atom id="r5" name="C"><point x="2.5cm" y="1cm"/></atom>'
	bad_target = '<molecule id="m2">' + atoms + bonds + '</molecule>'
	cdml_text = _SIMPLE_RING_CDML.replace('</cdml>', bad_target + '</cdml>')
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLValidationError, match="exactly one independent cycle"):
		session.repair_geometry(_ring_request(before.revision, ("m1", "m2")))
	assert session.snapshot() == before
