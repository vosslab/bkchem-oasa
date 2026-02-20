"""Unit tests for shared attachment target primitives and geometry helpers."""

# Third Party
import pytest

# local repo modules
from oasa.render_lib.data_types import AttachConstraints
from oasa.render_lib.data_types import AttachTarget
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.data_types import make_circle_target
from oasa.render_lib.data_types import make_composite_target
from oasa.render_lib.low_level_geometry import directional_attach_edge_intersection
from oasa.render_lib.label_geometry import label_attach_target
from oasa.render_lib.label_geometry import label_target
from oasa.render_lib.attach_resolution import resolve_attach_endpoint
from oasa.render_lib.attach_resolution import retreat_endpoint_until_legal
from oasa.render_lib.attach_resolution import validate_attachment_paint


#============================================
def _is_on_circle_boundary(point, center, radius, tol=1e-6):
	distance = ((point[0] - center[0]) ** 2 + (point[1] - center[1]) ** 2) ** 0.5
	return abs(distance - radius) <= tol


#============================================
def test_attach_target_centroid_box_circle_composite():
	box = make_box_target((0.0, 2.0, 10.0, 12.0))
	circle = make_circle_target((5.0, -4.0), 3.0)
	composite = make_composite_target((circle, box))
	assert box.centroid() == pytest.approx((5.0, 7.0))
	assert circle.centroid() == pytest.approx((5.0, -4.0))
	assert composite.centroid() == pytest.approx(circle.centroid())


#============================================
def test_attach_target_contains_box_and_circle():
	box = make_box_target((0.0, 0.0, 10.0, 10.0))
	circle = make_circle_target((0.0, 0.0), 5.0)
	assert box.contains((5.0, 5.0))
	assert not box.contains((0.0, 5.0))
	assert circle.contains((1.0, 1.0))
	assert not circle.contains((5.0, 0.0))


#============================================
def test_attach_target_boundary_intersection_circle():
	target = make_circle_target((0.0, 0.0), 5.0)
	endpoint = target.boundary_intersection(bond_start=(-20.0, 0.0))
	assert _is_on_circle_boundary(endpoint, (0.0, 0.0), 5.0, tol=1e-6)
	assert endpoint[0] < 0.0


#============================================
def test_resolve_attach_endpoint_box_vertical_lock():
	target = make_box_target((0.0, 0.0, 10.0, 10.0))
	constraints = AttachConstraints(vertical_lock=True)
	endpoint = resolve_attach_endpoint(
		bond_start=(5.0, -10.0),
		target=target,
		interior_hint=(5.0, 5.0),
		constraints=constraints,
	)
	assert endpoint == pytest.approx((5.0, 0.0))


#============================================
def test_validate_attachment_paint_circle_legality_boundary_then_penetration():
	target = make_circle_target((0.0, 0.0), 5.0)
	boundary_endpoint = resolve_attach_endpoint(
		bond_start=(-12.0, 0.0),
		target=target,
		interior_hint=target.centroid(),
		constraints=AttachConstraints(direction_policy="line"),
	)
	assert _is_on_circle_boundary(boundary_endpoint, (0.0, 0.0), 5.0, tol=1e-6)
	assert validate_attachment_paint(
		line_start=(-12.0, 0.0),
		line_end=boundary_endpoint,
		line_width=1.0,
		forbidden_regions=[target],
		allowed_regions=[],
		epsilon=0.5,
	)
	assert not validate_attachment_paint(
		line_start=(-12.0, 0.0),
		line_end=(boundary_endpoint[0] + 0.8, boundary_endpoint[1]),
		line_width=1.0,
		forbidden_regions=[target],
		allowed_regions=[],
		epsilon=0.5,
	)


#============================================
def test_validate_attachment_paint_long_segment_circle_false_negative_regression():
	forbidden = make_circle_target((0.5, 0.0), 0.2)
	assert not validate_attachment_paint(
		line_start=(0.0, 0.0),
		line_end=(1000.0, 0.0),
		line_width=1.0,
		forbidden_regions=[forbidden],
		allowed_regions=[],
		epsilon=0.0,
	)


#============================================
def test_validate_attachment_paint_allowed_box_carveout_false_negative_regression():
	forbidden = make_box_target(
		(-0.9948500452311335, -0.27878791276789094, -0.8635941180998662, 0.07419065418791237)
	)
	allowed = make_box_target(
		(-0.9783920601615839, -0.1707535151356337, -0.799410415671622, -0.14755815607373746)
	)
	assert not validate_attachment_paint(
		line_start=(-159.64778523717416, 100.43156381656104),
		line_end=(39.030962583316295, -24.427278788129684),
		line_width=1.5009103569593027,
		forbidden_regions=[forbidden],
		allowed_regions=[allowed],
		epsilon=0.0,
	)


#============================================
def test_resolve_attach_endpoint_composite_uses_fallback_children():
	invalid_primary = AttachTarget(kind="unknown")
	fallback_box = make_box_target((0.0, 0.0, 10.0, 10.0))
	composite = make_composite_target((invalid_primary, fallback_box))
	endpoint = resolve_attach_endpoint(
		bond_start=(-5.0, 5.0),
		target=composite,
		interior_hint=(5.0, 5.0),
		constraints=AttachConstraints(direction_policy="line"),
	)
	assert endpoint == pytest.approx((0.0, 5.0))


#============================================
def test_render_geometry_shim_removed():
	"""Verify the backward-compat shim module no longer exists."""
	import importlib
	with pytest.raises(ImportError):
		# the shim was deleted after the render_lib sub-package split
		importlib.import_module("oasa.render_geometry")


#============================================
def test_directional_attach_line_policy_matches_legacy_clip():
	box = (0.0, 0.0, 10.0, 10.0)
	start = (-10.0, 2.0)
	target = (5.0, 5.0)
	line_policy = directional_attach_edge_intersection(
		bond_start=start,
		attach_bbox=box,
		attach_target=target,
		direction_policy="line",
	)
	resolved = resolve_attach_endpoint(
		bond_start=start,
		target=make_box_target(box),
		interior_hint=target,
		constraints=AttachConstraints(direction_policy="line"),
	)
	assert line_policy == pytest.approx(resolved)


#============================================
def test_directional_attach_auto_policy_snaps_to_canonical_lattice_for_box():
	box = (0.0, 0.0, 10.0, 10.0)
	start = (-10.0, 1.0)
	target = (5.0, 5.0)
	endpoint = directional_attach_edge_intersection(
		bond_start=start,
		attach_bbox=box,
		attach_target=target,
		direction_policy="auto",
	)
	assert endpoint == pytest.approx((0.0, 1.0))


#============================================
def test_resolve_attach_endpoint_circle_auto_policy_snaps_to_canonical_lattice():
	target = make_circle_target((0.0, 0.0), 5.0)
	endpoint = resolve_attach_endpoint(
		bond_start=(-10.0, 2.0),
		target=target,
		interior_hint=(0.0, 0.0),
		constraints=AttachConstraints(direction_policy="auto"),
	)
	assert endpoint[1] == pytest.approx(2.0)
	assert endpoint[0] == pytest.approx(-(21.0 ** 0.5))


#============================================
@pytest.mark.parametrize(
	("text", "anchor", "x", "y", "font_size", "expected"),
	(
		("O", "middle", 10.0, 20.0, 16.0, (3.77734375, 14.272, 16.22265625, 26.128)),
		("OH", "start", 10.0, 8.0, 12.0, (6.25, 3.7040000000000006, 24.25, 12.596)),
		("NH3+", "end", -5.0, 4.0, 16.0, (-46.3515625, -1.7279999999999998, -5.0, 10.128)),
	),
)
def test_label_target_legacy_geometry_values(text, anchor, x, y, font_size, expected):
	target = label_target(x, y, text, anchor, font_size)
	assert target.kind == "box"
	assert target.box == pytest.approx(expected)


#============================================
def test_label_attach_target_legacy_geometry_values():
	target = label_attach_target(
		0.0,
		0.0,
		"CH2OH",
		"start",
		16.0,
		attach_atom="last",
	)
	full = label_target(0.0, 0.0, "CH2OH", "start", 16.0)
	assert target.kind == "box"
	assert target.box[0] > full.box[0]
	assert target.box[2] <= full.box[2]
	assert target.box[0] > ((full.box[0] + full.box[2]) * 0.5)
	assert (target.box[2] - target.box[0]) > 0.0


#============================================
def test_label_attach_selector_precedence_uses_element_before_attach_atom():
	with_element = label_attach_target(
		0.0,
		0.0,
		"COOH",
		"start",
		16.0,
		attach_atom="first",
		attach_element="O",
	).box
	default_first = label_attach_target(
		0.0,
		0.0,
		"COOH",
		"start",
		16.0,
		attach_atom="first",
	).box
	assert with_element[0] > default_first[0]


#============================================
@pytest.mark.parametrize("text", ("CH2OH", "HOH2C"))
def test_label_attach_element_targets_core_span_not_decorated_span(text):
	core_target = label_attach_target(
		0.0,
		0.0,
		text,
		"start",
		16.0,
		attach_atom="first",
		attach_element="C",
	).box
	decorated_target = label_attach_target(
		0.0,
		0.0,
		text,
		"start",
		16.0,
		attach_atom="first",
	).box
	core_width = core_target[2] - core_target[0]
	decorated_width = decorated_target[2] - decorated_target[0]
	if text == "CH2OH":
		assert core_width < decorated_width
		assert core_target[0] >= decorated_target[0]
		assert core_target[2] <= decorated_target[2]
		assert core_target[2] < decorated_target[2]
	else:
		assert core_width > 0.0
		assert core_target[0] > decorated_target[2]


#============================================
@pytest.mark.parametrize("text", ("CH2OH", "HOH2C"))
def test_label_attach_element_stem_site_is_left_of_core_site(text):
	core_target = label_attach_target(
		0.0,
		0.0,
		text,
		"start",
		16.0,
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	).box
	stem_target = label_attach_target(
		0.0,
		0.0,
		text,
		"start",
		16.0,
		attach_atom="first",
		attach_element="C",
		attach_site="stem_centerline",
	).box
	core_center = (core_target[0] + core_target[2]) * 0.5
	stem_center = (stem_target[0] + stem_target[2]) * 0.5
	assert stem_center < core_center
	assert (stem_target[2] - stem_target[0]) < (core_target[2] - core_target[0])


#============================================
@pytest.mark.parametrize("text", ("CH2OH", "HOH2C"))
def test_label_attach_element_core_center_is_right_of_stem_center(text):
	core_target = label_attach_target(
		0.0,
		0.0,
		text,
		"start",
		16.0,
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	).box
	stem_target = label_attach_target(
		0.0,
		0.0,
		text,
		"start",
		16.0,
		attach_atom="first",
		attach_element="C",
		attach_site="stem_centerline",
	).box
	closed_target = label_attach_target(
		0.0,
		0.0,
		text,
		"start",
		16.0,
		attach_atom="first",
		attach_element="C",
		attach_site="closed_center",
	).box
	core_center = (core_target[0] + core_target[2]) * 0.5
	stem_center = (stem_target[0] + stem_target[2]) * 0.5
	closed_center = (closed_target[0] + closed_target[2]) * 0.5
	assert closed_center >= core_center
	assert closed_center > stem_center


#============================================
def test_label_attach_element_works_for_single_decorated_token_hydroxyl():
	core_target = label_attach_target(
		0.0,
		0.0,
		"OH",
		"start",
		16.0,
		attach_atom="first",
		attach_element="O",
	).box
	decorated_target = label_attach_target(
		0.0,
		0.0,
		"OH",
		"start",
		16.0,
		attach_atom="first",
	).box
	assert core_target[2] < decorated_target[2]
	assert core_target[0] >= decorated_target[0]


#============================================
def test_label_attach_invalid_attach_atom_raises_even_with_attach_element():
	with pytest.raises(ValueError, match=r"Invalid attach_atom value: 'frist'"):
		label_attach_target(
			0.0,
			0.0,
			"COOH",
			"start",
			16.0,
			attach_atom="frist",
			attach_element="O",
		).box


#============================================
def test_label_attach_invalid_attach_site_raises():
	with pytest.raises(ValueError, match=r"Invalid attach_site value: 'bad_site'"):
		label_attach_target(
			0.0,
			0.0,
			"CH2OH",
			"start",
			16.0,
			attach_atom="first",
			attach_element="C",
			attach_site="bad_site",
		).box


#============================================
def test_retreat_endpoint_until_legal_returns_original_when_legal():
	forbidden = make_box_target((10.0, -2.0, 20.0, 2.0))
	start = (0.0, 0.0)
	end = (8.0, 0.0)
	retreated = retreat_endpoint_until_legal(
		line_start=start,
		line_end=end,
		line_width=1.0,
		forbidden_regions=[forbidden],
		epsilon=0.5,
	)
	assert retreated == pytest.approx(end)


#============================================
def test_retreat_endpoint_until_legal_box_penetration_retreats_and_is_legal():
	forbidden = make_box_target((0.0, -2.0, 10.0, 2.0))
	start = (-12.0, 0.0)
	end = (5.0, 0.0)
	retreated = retreat_endpoint_until_legal(
		line_start=start,
		line_end=end,
		line_width=2.0,
		forbidden_regions=[forbidden],
		epsilon=0.5,
	)
	assert retreated[0] > start[0]
	assert retreated[0] < end[0]
	assert validate_attachment_paint(
		line_start=start,
		line_end=retreated,
		line_width=2.0,
		forbidden_regions=[forbidden],
		epsilon=0.5,
	)
	assert not validate_attachment_paint(
		line_start=start,
		line_end=((retreated[0] + end[0]) * 0.5, (retreated[1] + end[1]) * 0.5),
		line_width=2.0,
		forbidden_regions=[forbidden],
		epsilon=0.5,
	)


#============================================
def test_retreat_endpoint_until_legal_circle_penetration_retreats_and_is_legal():
	forbidden = make_circle_target((0.0, 0.0), 5.0)
	start = (-12.0, 0.0)
	end = (0.0, 0.0)
	retreated = retreat_endpoint_until_legal(
		line_start=start,
		line_end=end,
		line_width=1.0,
		forbidden_regions=[forbidden],
		epsilon=0.5,
	)
	assert retreated[0] < end[0]
	assert validate_attachment_paint(
		line_start=start,
		line_end=retreated,
		line_width=1.0,
		forbidden_regions=[forbidden],
		epsilon=0.5,
	)


#============================================
def test_retreat_endpoint_until_legal_returns_start_when_no_legal_prefix():
	forbidden = make_box_target((-1.0, -1.0, 1.0, 1.0))
	start = (0.0, 0.0)
	end = (10.0, 0.0)
	retreated = retreat_endpoint_until_legal(
		line_start=start,
		line_end=end,
		line_width=2.0,
		forbidden_regions=[forbidden],
		epsilon=0.5,
	)
	assert retreated == pytest.approx(start)
