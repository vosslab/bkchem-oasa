"""Semantic geometry tests for portable molecule primitive painting."""

import dataclasses

import pytest

import bkchem_qt.canvas.items.primitive_ops_painter
import bkchem_qt.io.cdml_document_io
import oasa.cdml_document


#============================================
def _bond_batch() -> object:
	"""Return one real portable single-bond batch from the OASA boundary."""
	document = oasa.cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='1cm' y='0cm'/></atom>"
		"<bond id='e' start='a' end='b' type='n1'/></molecule></cdml>", validation="compat",
	)
	return next(batch for batch in document.molecule_render_observation(0).batches if batch.kind == "bond")


#============================================
def test_portable_line_bounds_include_its_stroked_endpoints(qapp: object) -> None:
	"""Qt bounds include the visible stroke rather than only its center line."""
	batch = _bond_batch()
	bounds = bkchem_qt.canvas.items.primitive_ops_painter.bounds(batch.operations, 0.0)
	line = batch.operations[0]
	assert bounds.contains(*line.points[0]) and bounds.contains(*line.points[1])
	assert bounds.top() < line.points[0][1] < bounds.bottom()


#============================================
def test_bond_drag_preview_follows_current_endpoints_without_mutating_batch(qapp: object) -> None:
	"""A preview transforms immutable accepted facts into the live endpoint axis."""
	batch = _bond_batch()
	original = batch.operations
	line = dataclasses.replace(batch.operations[0], points=((0.0, 0.0), (10.0, 0.0)))
	preview = bkchem_qt.canvas.items.primitive_ops_painter.transformed_operations(
		(line,), ((0.0, 0.0), (10.0, 0.0)), ((5.0, 5.0), (5.0, 25.0)),
	)
	assert preview[0].points == ((5.0, 5.0), (5.0, 25.0))
	assert batch.operations == original


#============================================
def test_portable_subscript_text_expands_the_local_label_bound(qapp: object) -> None:
	"""Qt-local text measurement retains portable subscript label geometry."""
	del qapp
	base = oasa.cdml_document.CDMLRenderPrimitive(
		"text", ((0.0, 0.0),), (), (("N", "base"),), None,
		None, "foreground", None, None, None, "Arial", 12.0, "start",
		"normal", None, None, 0,
	)
	subscript = dataclasses.replace(base, text_runs=(("N", "base"), ("2", "sub")))
	base_left, base_right = bkchem_qt.canvas.items.primitive_ops_painter.text_horizontal_bounds((base,))
	subscript_left, subscript_right = bkchem_qt.canvas.items.primitive_ops_painter.text_horizontal_bounds((subscript,))

	assert subscript_left == base_left and subscript_right > base_right


#============================================
def test_direct_hydration_rejects_mixed_observation_revisions(qapp: object) -> None:
	"""Every public hydration entry point rejects cross-revision backend facts."""
	document = oasa.cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='1cm' y='0cm'/></atom><bond id='e' start='a' end='b' type='n1'/></molecule></cdml>", validation="compat",
	)
	with pytest.raises(ValueError):
		oasa.cdml_document.CDMLProjectionSnapshot(
			oasa.cdml_document.CDMLSnapshot(0, document.serialize(), False),
			document.presentation_description(0), document.paper_layout(0),
			document.fragment_metadata(0), document.atom_mark_observation(0),
			document.group_observation(0), document.molecule_core_observation(0),
			dataclasses.replace(document.molecule_render_observation(0), revision=1),
		)
