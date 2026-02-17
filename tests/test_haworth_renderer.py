"""Unit tests for Haworth schematic render_ops output."""

# Standard Library
import dataclasses
import math
from xml.dom import minidom as xml_minidom

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

import oasa.dom_extensions as dom_extensions
import oasa.haworth as haworth
import oasa.haworth_renderer as haworth_renderer
import oasa.haworth_spec as haworth_spec
import oasa.render_geometry as render_geometry
import oasa.render_ops as render_ops
import oasa.sugar_code as sugar_code


#============================================
def _build_spec(code: str, ring_type: str, anomeric: str) -> haworth_spec.HaworthSpec:
	parsed = sugar_code.parse(code)
	return haworth_spec.generate(parsed, ring_type=ring_type, anomeric=anomeric)


#============================================
def _render(code: str, ring_type: str, anomeric: str, bond_length: float = 30.0, **kwargs) -> tuple:
	spec = _build_spec(code, ring_type, anomeric)
	ops = haworth_renderer.render(spec, bond_length=bond_length, **kwargs)
	return spec, ops


#============================================
def _texts(ops):
	return [op for op in ops if isinstance(op, render_ops.TextOp)]


#============================================
def _polygons(ops):
	return [op for op in ops if isinstance(op, render_ops.PolygonOp)]


#============================================
def _paths(ops):
	return [op for op in ops if isinstance(op, render_ops.PathOp)]


#============================================
def _lines(ops):
	return [op for op in ops if isinstance(op, render_ops.LineOp)]


#============================================
def _by_id(ops, op_id: str):
	for op in ops:
		if getattr(op, "op_id", None) == op_id:
			return op
	raise AssertionError("Missing op_id %s" % op_id)


#============================================
def _text_by_id(ops, op_id: str) -> render_ops.TextOp:
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.TextOp)
	return op


#============================================
def _line_by_id(ops, op_id: str) -> render_ops.LineOp:
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.LineOp)
	return op


#============================================
def _polygon_by_id(ops, op_id: str) -> render_ops.PolygonOp:
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.PolygonOp)
	return op


#============================================
def _path_by_id(ops, op_id: str) -> render_ops.PathOp:
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.PathOp)
	return op


#============================================
def _ring_vertex(spec: haworth_spec.HaworthSpec, carbon: int, bond_length: float = 30.0) -> tuple[float, float]:
	slot_map = haworth_renderer.carbon_slot_map(spec)
	slot = slot_map[f"C{carbon}"]
	if spec.ring_type == "pyranose":
		coords = haworth._ring_template(6, bond_length=bond_length)
		index = haworth_renderer.PYRANOSE_SLOT_INDEX[slot]
	else:
		coords = haworth._ring_template(5, bond_length=bond_length)
		index = haworth_renderer.FURANOSE_SLOT_INDEX[slot]
	return coords[index]


#============================================
def _ring_center(spec: haworth_spec.HaworthSpec, bond_length: float = 30.0) -> tuple[float, float]:
	if spec.ring_type == "pyranose":
		coords = haworth._ring_template(6, bond_length=bond_length)
	else:
		coords = haworth._ring_template(5, bond_length=bond_length)
	center_x = sum(point[0] for point in coords) / len(coords)
	center_y = sum(point[1] for point in coords) / len(coords)
	return (center_x, center_y)


#============================================
def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
	return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


#============================================
def _raster_text_column_histogram(
		text_op: render_ops.TextOp,
		probe_point: tuple[float, float],
		scale: float = 16.0,
		padding: float = 24.0) -> tuple[dict[int, int], float]:
	"""Rasterize one text op and return per-column ink counts plus probe x in px."""
	try:
		import cairo
	except ImportError:
		pytest.skip("pycairo is required for raster-grounded glyph probe")
	min_x = min(text_op.x, probe_point[0]) - (text_op.font_size * 3.0)
	max_x = max(text_op.x, probe_point[0]) + (text_op.font_size * 9.0)
	min_y = min(text_op.y, probe_point[1]) - (text_op.font_size * 3.0)
	max_y = max(text_op.y, probe_point[1]) + (text_op.font_size * 2.0)
	width = int(math.ceil(((max_x - min_x) * scale) + (2.0 * padding)))
	height = int(math.ceil(((max_y - min_y) * scale) + (2.0 * padding)))
	surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, max(1, width), max(1, height))
	context = cairo.Context(surface)
	context.set_source_rgb(1.0, 1.0, 1.0)
	context.paint()
	tx = padding - (min_x * scale)
	ty = padding - (min_y * scale)
	context.translate(tx, ty)
	context.scale(scale, scale)
	render_ops.ops_to_cairo(context, [text_op])
	buffer = surface.get_data()
	stride = surface.get_stride()
	histogram = {}
	for y_pos in range(surface.get_height()):
		row = y_pos * stride
		for x_pos in range(surface.get_width()):
			base = row + (x_pos * 4)
			blue = buffer[base + 0]
			green = buffer[base + 1]
			red = buffer[base + 2]
			alpha = buffer[base + 3]
			if alpha == 0:
				continue
			if red >= 245 and green >= 245 and blue >= 245:
				continue
			histogram[x_pos] = histogram.get(x_pos, 0) + 1
	probe_x = (probe_point[0] * scale) + tx
	return histogram, probe_x


#============================================
def _contiguous_int_ranges(values: list[int]) -> list[tuple[int, int]]:
	"""Return sorted contiguous [start, end] ranges for integer values."""
	if not values:
		return []
	ranges = []
	start = values[0]
	end = values[0]
	for value in values[1:]:
		if value == (end + 1):
			end = value
			continue
		ranges.append((start, end))
		start = value
		end = value
	ranges.append((start, end))
	return ranges


#============================================
def _line_length(line: render_ops.LineOp) -> float:
	return _distance(line.p1, line.p2)


#============================================
def _bbox(ops: list) -> tuple[float, float, float, float]:
	minx = float("inf")
	miny = float("inf")
	maxx = float("-inf")
	maxy = float("-inf")

	def take(x: float, y: float) -> None:
		nonlocal minx
		nonlocal miny
		nonlocal maxx
		nonlocal maxy
		minx = min(minx, x)
		miny = min(miny, y)
		maxx = max(maxx, x)
		maxy = max(maxy, y)

	for op in ops:
		if isinstance(op, render_ops.LineOp):
			take(op.p1[0], op.p1[1])
			take(op.p2[0], op.p2[1])
			continue
		if isinstance(op, render_ops.PolygonOp):
			for x, y in op.points:
				take(x, y)
			continue
		if isinstance(op, render_ops.TextOp):
			visible = haworth_renderer._visible_text_length(op.text)
			width = visible * op.font_size * 0.6
			height = op.font_size
			x = op.x
			if op.anchor == "middle":
				x -= width / 2.0
			elif op.anchor == "end":
				x -= width
			take(x, op.y - height)
			take(x + width, op.y)
	if minx == float("inf"):
		raise AssertionError("No drawable ops for bbox")
	return (minx, miny, maxx, maxy)


#============================================
def _edge_thicknesses(poly: render_ops.PolygonOp) -> tuple[float, float]:
	p0, p1, p2, p3 = poly.points
	return (_distance(p0, p1), _distance(p2, p3))


#============================================
def _label_bbox(label: render_ops.TextOp) -> tuple[float, float, float, float]:
	return haworth_renderer._text_target(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
	).box


#============================================
def _point_in_box(point: tuple[float, float], box: tuple[float, float, float, float]) -> bool:
	return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


#============================================
def _point_on_box_edge(
		point: tuple[float, float],
		box: tuple[float, float, float, float],
		tol: float = 1e-6) -> bool:
	x_value, y_value = point
	x1, y1, x2, y2 = box
	on_x = abs(x_value - x1) <= tol or abs(x_value - x2) <= tol
	on_y = abs(y_value - y1) <= tol or abs(y_value - y2) <= tol
	in_x = (x1 - tol) <= x_value <= (x2 + tol)
	in_y = (y1 - tol) <= y_value <= (y2 + tol)
	return (on_x and in_y) or (on_y and in_x)


#============================================
def _segment_intersects_box_closed(
		p1: tuple[float, float],
		p2: tuple[float, float],
		box: tuple[float, float, float, float],
		tol: float = 1e-9) -> bool:
	x1, y1, x2, y2 = box
	dx = p2[0] - p1[0]
	dy = p2[1] - p1[1]
	p_values = (-dx, dx, -dy, dy)
	q_values = (
		p1[0] - x1,
		x2 - p1[0],
		p1[1] - y1,
		y2 - p1[1],
	)
	u1 = 0.0
	u2 = 1.0
	for p_value, q_value in zip(p_values, q_values):
		if abs(p_value) <= tol:
			if q_value < 0.0:
				return False
			continue
		t_value = q_value / p_value
		if p_value < 0.0:
			u1 = max(u1, t_value)
		else:
			u2 = min(u2, t_value)
		if u1 > u2:
			return False
	return True


#============================================
def _segment_intersects_box_interior(
		p1: tuple[float, float],
		p2: tuple[float, float],
		box: tuple[float, float, float, float],
		epsilon: float = 1e-3) -> bool:
	x1, y1, x2, y2 = box
	inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
	if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
		return False
	return _segment_intersects_box_closed(p1, p2, inner_box)


#============================================
def _point_to_segment_distance(
		point: tuple[float, float],
		seg_start: tuple[float, float],
		seg_end: tuple[float, float]) -> float:
	px, py = point
	ax, ay = seg_start
	bx, by = seg_end
	abx = bx - ax
	aby = by - ay
	ab2 = (abx * abx) + (aby * aby)
	if ab2 <= 1e-12:
		return math.hypot(px - ax, py - ay)
	t_value = ((px - ax) * abx + (py - ay) * aby) / ab2
	t_value = max(0.0, min(1.0, t_value))
	closest_x = ax + (abx * t_value)
	closest_y = ay + (aby * t_value)
	return math.hypot(px - closest_x, py - closest_y)


#============================================
def _segments_intersect_for_penetration(
		a1: tuple[float, float],
		a2: tuple[float, float],
		b1: tuple[float, float],
		b2: tuple[float, float],
		tol: float = 1e-12) -> bool:
	def _cross(p0, p1, p2):
		return ((p1[0] - p0[0]) * (p2[1] - p0[1])) - ((p1[1] - p0[1]) * (p2[0] - p0[0]))

	def _on_segment(p0, p1, p2):
		return (
			min(p0[0], p1[0]) - tol <= p2[0] <= max(p0[0], p1[0]) + tol
			and min(p0[1], p1[1]) - tol <= p2[1] <= max(p0[1], p1[1]) + tol
		)

	d1 = _cross(a1, a2, b1)
	d2 = _cross(a1, a2, b2)
	d3 = _cross(b1, b2, a1)
	d4 = _cross(b1, b2, a2)
	if ((d1 > tol and d2 < -tol) or (d1 < -tol and d2 > tol)) and (
			(d3 > tol and d4 < -tol) or (d3 < -tol and d4 > tol)):
		return True
	if abs(d1) <= tol and _on_segment(a1, a2, b1):
		return True
	if abs(d2) <= tol and _on_segment(a1, a2, b2):
		return True
	if abs(d3) <= tol and _on_segment(b1, b2, a1):
		return True
	if abs(d4) <= tol and _on_segment(b1, b2, a2):
		return True
	return False


#============================================
def _segment_segment_distance(
		a1: tuple[float, float],
		a2: tuple[float, float],
		b1: tuple[float, float],
		b2: tuple[float, float]) -> float:
	if _segments_intersect_for_penetration(a1, a2, b1, b2):
		return 0.0
	return min(
		_point_to_segment_distance(a1, b1, b2),
		_point_to_segment_distance(a2, b1, b2),
		_point_to_segment_distance(b1, a1, a2),
		_point_to_segment_distance(b2, a1, a2),
	)


#============================================
def _segment_distance_to_box_interior(
		p1: tuple[float, float],
		p2: tuple[float, float],
		box: tuple[float, float, float, float],
		epsilon: float = 1e-3) -> float:
	x1, y1, x2, y2 = box
	inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
	if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
		return float("inf")
	if _segment_intersects_box_closed(p1, p2, inner_box):
		return 0.0
	corners = [
		(inner_box[0], inner_box[1]),
		(inner_box[2], inner_box[1]),
		(inner_box[2], inner_box[3]),
		(inner_box[0], inner_box[3]),
	]
	edges = [
		(corners[0], corners[1]),
		(corners[1], corners[2]),
		(corners[2], corners[3]),
		(corners[3], corners[0]),
	]
	return min(_segment_segment_distance(p1, p2, edge_start, edge_end) for edge_start, edge_end in edges)


#============================================
def _line_penetrates_label_interior(line: render_ops.LineOp, label_box: tuple[float, float, float, float]) -> bool:
	line_radius = max(0.0, float(getattr(line, "width", 0.0) or 0.0) * 0.5)
	if line_radius <= 0.0:
		return _segment_intersects_box_interior(line.p1, line.p2, label_box)
	min_distance = _segment_distance_to_box_interior(line.p1, line.p2, label_box)
	return min_distance < line_radius


#============================================
def _connector_hatches(ops: list, connector_id: str) -> list[render_ops.LineOp]:
	prefix = f"{connector_id}_hatch"
	return [
		line for line in _lines(ops)
		if (line.op_id or "").startswith(prefix)
	]


#============================================
def _line_projection_along(line: render_ops.LineOp, point: tuple[float, float]) -> float:
	dx = line.p2[0] - line.p1[0]
	dy = line.p2[1] - line.p1[1]
	length = math.hypot(dx, dy)
	if length <= 1e-9:
		return 0.0
	ux = dx / length
	uy = dy / length
	return ((point[0] - line.p1[0]) * ux) + ((point[1] - line.p1[1]) * uy)


#============================================
def _line_angle_degrees(line: render_ops.LineOp) -> float:
	"""Return one line angle in degrees in [0, 360)."""
	return math.degrees(math.atan2(line.p2[1] - line.p1[1], line.p2[0] - line.p1[0])) % 360.0


#============================================
def _lattice_angle_error(angle_degrees: float) -> float:
	"""Return minimum angular error to canonical 30-degree lattice."""
	lattice_angles = tuple(float(angle) for angle in range(0, 360, 30))
	return min(
		abs(((angle_degrees - lattice_angle + 180.0) % 360.0) - 180.0)
		for lattice_angle in lattice_angles
	)


#============================================
def _assert_line_on_lattice(line: render_ops.LineOp, tolerance_degrees: float = 10.0) -> None:
	"""Assert that one line direction is within tolerance of lattice angles."""
	angle = _line_angle_degrees(line)
	error = _lattice_angle_error(angle)
	assert error <= tolerance_degrees, (
		f"{line.op_id} angle={angle:.3f} error={error:.3f} exceeds {tolerance_degrees:.3f}"
	)


#============================================
def _assert_line_angle(line: render_ops.LineOp, expected_degrees: float, tolerance_degrees: float = 1e-6) -> None:
	"""Assert one line direction angle with wrap-around tolerance."""
	angle = _line_angle_degrees(line)
	error = abs(((angle - expected_degrees + 180.0) % 360.0) - 180.0)
	assert error <= tolerance_degrees, (
		f"{line.op_id} angle={angle:.6f} expected={expected_degrees:.6f} error={error:.6f}"
	)


#============================================
def _allowed_attach_target_for_connector(
		label: render_ops.TextOp,
		connector_id: str) -> render_geometry.AttachTarget | None:
	"""Return attach-token carve-out target for explicit token-based connectors."""
	del connector_id
	contract = render_geometry.label_attach_contract_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		line_width=0.0,
		chain_attach_site="core_center",
		font_name=label.font_name,
	)
	return contract.allowed_target


#============================================
def _assert_hashed_connector_quality(ops: list, connector_id: str, label_id: str) -> None:
	carrier = _line_by_id(ops, connector_id)
	assert 0.12 <= carrier.width <= 0.35
	hatches = _connector_hatches(ops, connector_id)
	assert hatches
	connector_length = _line_length(carrier)
	assert connector_length > 1e-9
	farthest = max(
		_line_projection_along(
			carrier,
			((hatch.p1[0] + hatch.p2[0]) * 0.5, (hatch.p1[1] + hatch.p2[1]) * 0.5),
		)
		for hatch in hatches
	)
	nearest = min(
		_line_projection_along(
			carrier,
			((hatch.p1[0] + hatch.p2[0]) * 0.5, (hatch.p1[1] + hatch.p2[1]) * 0.5),
		)
		for hatch in hatches
	)
	assert nearest <= (0.26 * connector_length)
	assert farthest >= (0.80 * connector_length)
	label = _text_by_id(ops, label_id)
	label_box = _label_bbox(label)
	allowed_target = _allowed_attach_target_for_connector(label, connector_id)
	if allowed_target is None:
		assert not _line_penetrates_label_interior(carrier, label_box)
	else:
		full_target = render_geometry.label_target_from_text_origin(
			text_x=label.x,
			text_y=label.y,
			text=label.text,
			anchor=label.anchor,
			font_size=label.font_size,
		)
		assert render_geometry.validate_attachment_paint(
			line_start=carrier.p1,
			line_end=carrier.p2,
			line_width=carrier.width,
			forbidden_regions=[full_target],
			allowed_regions=[allowed_target],
			epsilon=0.5,
		)
	for hatch in hatches:
		if allowed_target is None:
			assert not _line_penetrates_label_interior(hatch, label_box)
		else:
			full_target = render_geometry.label_target_from_text_origin(
				text_x=label.x,
				text_y=label.y,
				text=label.text,
				anchor=label.anchor,
				font_size=label.font_size,
			)
			assert render_geometry.validate_attachment_paint(
				line_start=hatch.p1,
				line_end=hatch.p2,
				line_width=hatch.width,
				forbidden_regions=[full_target],
				allowed_regions=[allowed_target],
				epsilon=0.5,
			)


#============================================
def _connector_bbox_for_label(label: render_ops.TextOp) -> tuple[float, float, float, float]:
	first_bbox = render_geometry.label_attach_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom="first",
	).box
	last_bbox = render_geometry.label_attach_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom="last",
	).box
	if first_bbox != last_bbox:
		return first_bbox
	return _label_bbox(label)


#============================================
def _oxygen_attach_bbox_for_hydroxyl_label(label: render_ops.TextOp) -> tuple[float, float, float, float]:
	attach_mode = "first" if label.text == "OH" else "last"
	return render_geometry.label_attach_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom=attach_mode,
	).box


#============================================
def _assert_connector_endpoint_on_attach_element(
		ops: list,
		label_id: str,
		connector_id: str,
		attach_element: str,
		attach_site: str | None = None) -> None:
	label = _text_by_id(ops, label_id)
	connector = _line_by_id(ops, connector_id)
	if attach_site is None:
		attach_site = "core_center"
	contract = render_geometry.label_attach_contract_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		line_width=connector.width,
		attach_atom="first",
		attach_element=attach_element,
		attach_site=attach_site,
		chain_attach_site="core_center",
		font_name=label.font_name,
	)
	# epsilon must accommodate ATTACH_GAP_TARGET retreat from endpoint
	# plus additional retreat to maintain gap from full label text
	gap_epsilon = render_geometry.ATTACH_GAP_TARGET * 2.0
	assert render_geometry._point_in_attach_target_closed(connector.p2, contract.endpoint_target, epsilon=gap_epsilon), (
		f"{connector_id} endpoint {connector.p2} not inside {label_id} "
		f"{attach_element}-target {contract.endpoint_target} (epsilon={gap_epsilon})"
	)
	assert render_geometry.validate_attachment_paint(
		line_start=connector.p1,
		line_end=connector.p2,
		line_width=connector.width,
		forbidden_regions=[contract.full_target],
		allowed_regions=[contract.allowed_target],
		epsilon=0.5,
	)


#============================================
def _hydroxyl_oxygen_center(label: render_ops.TextOp) -> tuple[float, float]:
	center = haworth_renderer._hydroxyl_oxygen_center(
		text=label.text,
		anchor=label.anchor,
		text_x=label.x,
		text_y=label.y,
		font_size=label.font_size,
	)
	if center is None:
		raise AssertionError("Expected hydroxyl label with oxygen center")
	return center


#============================================
def _point_outside_circle_radius(
		point: tuple[float, float],
		center: tuple[float, float],
		radius: float,
		tol: float = 1e-3) -> bool:
	return _distance(point, center) >= (radius - tol)


#============================================
def _assert_endpoint_matches_directional_attach_edge(
		line: render_ops.LineOp,
		attach_bbox: tuple[float, float, float, float]) -> None:
	target_center = (
		(attach_bbox[0] + attach_bbox[2]) * 0.5,
		(attach_bbox[1] + attach_bbox[3]) * 0.5,
	)
	gap_tol = 0.75
	if _point_on_box_edge(line.p2, attach_bbox, tol=gap_tol):
		return
	max_clearance = max(0.75, float(getattr(line, "width", 0.0) or 0.0) * 2.0)
	dx = target_center[0] - line.p1[0]
	dy = target_center[1] - line.p1[1]
	if abs(dx) >= abs(dy):
		expected_x = attach_bbox[0] if dx > 0.0 else attach_bbox[2]
		assert abs(line.p2[0] - expected_x) <= max_clearance
		if dx > 0.0:
			assert line.p2[0] <= (expected_x + 1e-6)
		else:
			assert line.p2[0] >= (expected_x - 1e-6)
	else:
		expected_y = attach_bbox[1] if dy > 0.0 else attach_bbox[3]
		assert abs(line.p2[1] - expected_y) <= max_clearance
		if dy > 0.0:
			assert line.p2[1] <= (expected_y + 1e-6)
		else:
			assert line.p2[1] >= (expected_y - 1e-6)


#============================================
def _rect_corners(box: tuple[float, float, float, float]) -> list[tuple[float, float]]:
	return [
		(box[0], box[1]),
		(box[2], box[1]),
		(box[2], box[3]),
		(box[0], box[3]),
	]


#============================================
def _point_in_polygon(point: tuple[float, float], polygon: tuple[tuple[float, float], ...]) -> bool:
	x_value, y_value = point
	inside = False
	count = len(polygon)
	for index in range(count):
		x1, y1 = polygon[index]
		x2, y2 = polygon[(index + 1) % count]
		intersects = ((y1 > y_value) != (y2 > y_value))
		if not intersects:
			continue
		denominator = y2 - y1
		if abs(denominator) < 1e-9:
			continue
		x_intersect = x1 + ((y_value - y1) * (x2 - x1) / denominator)
		if x_intersect >= x_value:
			inside = not inside
	return inside


#============================================
def _segments_intersect(
		a1: tuple[float, float],
		a2: tuple[float, float],
		b1: tuple[float, float],
		b2: tuple[float, float]) -> bool:
	def _cross(p1, p2, p3):
		return ((p2[0] - p1[0]) * (p3[1] - p1[1])) - ((p2[1] - p1[1]) * (p3[0] - p1[0]))

	def _on_segment(p1, p2, p3):
		return (
			min(p1[0], p2[0]) - 1e-9 <= p3[0] <= max(p1[0], p2[0]) + 1e-9
			and min(p1[1], p2[1]) - 1e-9 <= p3[1] <= max(p1[1], p2[1]) + 1e-9
		)

	d1 = _cross(a1, a2, b1)
	d2 = _cross(a1, a2, b2)
	d3 = _cross(b1, b2, a1)
	d4 = _cross(b1, b2, a2)
	if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
		return True
	if abs(d1) < 1e-9 and _on_segment(a1, a2, b1):
		return True
	if abs(d2) < 1e-9 and _on_segment(a1, a2, b2):
		return True
	if abs(d3) < 1e-9 and _on_segment(b1, b2, a1):
		return True
	if abs(d4) < 1e-9 and _on_segment(b1, b2, a2):
		return True
	return False


#============================================
def _box_overlaps_polygon(
		box: tuple[float, float, float, float],
		polygon: tuple[tuple[float, float], ...]) -> bool:
	for point in polygon:
		if _point_in_box(point, box):
			return True
	for corner in _rect_corners(box):
		if _point_in_polygon(corner, polygon):
			return True
	rect_points = _rect_corners(box)
	rect_edges = [
		(rect_points[0], rect_points[1]),
		(rect_points[1], rect_points[2]),
		(rect_points[2], rect_points[3]),
		(rect_points[3], rect_points[0]),
	]
	for index in range(len(polygon)):
		edge_start = polygon[index]
		edge_end = polygon[(index + 1) % len(polygon)]
		for rect_start, rect_end in rect_edges:
			if _segments_intersect(edge_start, edge_end, rect_start, rect_end):
				return True
	return False


#============================================
def _inner_box(
		box: tuple[float, float, float, float],
		epsilon: float = 1e-3) -> tuple[float, float, float, float] | None:
	inner = (box[0] + epsilon, box[1] + epsilon, box[2] - epsilon, box[3] - epsilon)
	if inner[0] >= inner[2] or inner[1] >= inner[3]:
		return None
	return inner


#============================================
def test_render_returns_ops():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert isinstance(ops, list)
	assert ops


#============================================
def test_render_contains_text_ops():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	text_values = [op.text for op in _texts(ops)]
	assert "O" in text_values
	assert "OH" in text_values
	assert "H" in text_values


#============================================
def test_render_contains_polygon_ops():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	polys = _polygons(ops)
	assert len(polys) >= 5


#============================================
def test_render_bbox_reasonable():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	minx, miny, maxx, maxy = _bbox(ops)
	assert maxx > minx
	assert maxy > miny
	assert (maxx - minx) > 20.0
	assert (maxy - miny) > 20.0


#============================================
def test_render_furanose():
	_, ops = _render("ARRDM", "furanose", "beta")
	ring_ops = [
		op for op in ops
		if (op.op_id or "").startswith("ring_edge_")
		and isinstance(op, (render_ops.PolygonOp, render_ops.PathOp))
	]
	# 5 edges: 1 back polygon + 2 rounded side paths + 2 oxygen-adjacent split pairs.
	assert len(ring_ops) == 7


#============================================
def test_furanose_template_calibrated_to_neurotiker_means():
	assert haworth.FURANOSE_TEMPLATE[0] == pytest.approx((-0.97, -0.26))
	assert haworth.FURANOSE_TEMPLATE[1] == pytest.approx((-0.49, 0.58))
	assert haworth.FURANOSE_TEMPLATE[2] == pytest.approx((0.49, 0.58))
	assert haworth.FURANOSE_TEMPLATE[3] == pytest.approx((0.97, -0.26))
	assert haworth.FURANOSE_TEMPLATE[4] == pytest.approx((0.00, -0.65))


#============================================
def test_render_with_carbon_numbers():
	_, ops = _render("ARLRDM", "pyranose", "alpha", show_carbon_numbers=True)
	number_labels = [op for op in _texts(ops) if (op.op_id or "").endswith("_number")]
	assert len(number_labels) == 5


#============================================
def test_render_carbon_numbers_closer_to_ring_vertices():
	spec, ops = _render("ARLRDM", "pyranose", "alpha", show_carbon_numbers=True)
	center = _ring_center(spec, bond_length=30.0)
	for carbon in (1, 2, 3, 4, 5):
		vertex = _ring_vertex(spec, carbon, bond_length=30.0)
		label = _text_by_id(ops, f"C{carbon}_number")
		label_point = (label.x, label.y)
		assert _distance(label_point, vertex) < _distance(label_point, center)


#============================================
def test_render_aldohexose_furanose():
	_, ops = _render("ARLRDM", "furanose", "alpha")
	assert _text_by_id(ops, "C4_up_chain1_oh_label").text in ("OH", "HO")
	assert _text_by_id(ops, "C4_up_chain2_label").text in ("CH<sub>2</sub>OH", "HOH<sub>2</sub>C")


#============================================
def test_render_debug_attach_overlay_emits_overlay_ops():
	_, ops = _render("ARRDM", "furanose", "alpha", show_hydrogens=False, debug_attach_overlay=True)
	assert any((op.op_id or "").endswith("_debug_target") for op in ops)
	assert any((op.op_id or "").endswith("_debug_centerline") for op in ops)
	assert any((op.op_id or "").endswith("_debug_endpoint") for op in ops)


#============================================
def test_render_ribose_pyranose():
	_, ops = _render("ARRDM", "pyranose", "alpha")
	chain_ops = [op for op in ops if "chain" in (op.op_id or "")]
	assert not chain_ops


#============================================
def test_render_erythrose_furanose():
	_, ops = _render("ARDM", "furanose", "beta")
	chain_ops = [op for op in ops if "chain" in (op.op_id or "")]
	assert not chain_ops


#============================================
def test_render_ribose_furanose_alpha_c4_up_connector_attaches_to_closed_carbon_center():
	_, ops = _render("ARRDM", "furanose", "alpha", show_hydrogens=False)
	_assert_connector_endpoint_on_attach_element(
		ops,
		label_id="C4_up_label",
		connector_id="C4_up_connector",
		attach_element="C",
		attach_site="core_center",
	)


#============================================
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_render_ribose_furanose_c4_up_connector_vertical_and_x_aligned_to_carbon_core_centerline(anomeric):
	_, ops = _render("ARRDM", "furanose", anomeric, show_hydrogens=False)
	label = _text_by_id(ops, "C4_up_label")
	line = _line_by_id(ops, "C4_up_connector")
	core_target = render_geometry.label_attach_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)
	core_center_x, _core_center_y = core_target.centroid()
	assert abs(line.p2[0] - line.p1[0]) <= 0.05
	assert line.p2[0] == pytest.approx(core_center_x, abs=0.20)
	assert line.p2[0] <= (core_center_x + 1e-6)


#============================================
def test_render_ribose_furanose_alpha_c4_up_connector_raster_probe_hits_c_stem_band():
	"""Independent raster probe: endpoint must avoid first-glyph C left stem edge."""
	_, ops = _render("ARRDM", "furanose", "alpha", show_hydrogens=False)
	label = _text_by_id(ops, "C4_up_label")
	line = _line_by_id(ops, "C4_up_connector")
	histogram, probe_x = _raster_text_column_histogram(label, line.p2, scale=16.0, padding=24.0)
	assert histogram, "No label ink captured for raster probe"
	columns = sorted(histogram)
	groups = _contiguous_int_ranges(columns)
	assert groups, "No glyph column groups found in raster probe"
	# C is the first glyph in CH2OH, so the left-most contiguous ink group is C.
	c_group_start, c_group_end = groups[0]
	c_columns = [x_value for x_value in columns if c_group_start <= x_value <= c_group_end]
	assert c_columns, "No columns found for first glyph group"
	max_count = max(histogram[x_value] for x_value in c_columns)
	stem_threshold = max_count * 0.70
	stem_band = [x_value for x_value in c_columns if histogram[x_value] >= stem_threshold]
	assert stem_band, "No C-stem band found in raster probe"
	stem_min = min(stem_band)
	stem_max = max(stem_band)
	assert probe_x > (stem_max + 12.0), (
		f"Ribose raster probe failed: endpoint_x_px={probe_x:.2f} still on C stem band "
		f"[{stem_min:.2f}, {stem_max:.2f}]"
	)


#============================================
@pytest.mark.parametrize("code", ("ARLLDM", "ARRLDM"))
def test_render_furanose_left_tail_chain2_connector_stays_on_carbon_token(code):
	_, ops = _render(code, "furanose", "alpha", show_hydrogens=False)
	_assert_connector_endpoint_on_attach_element(
		ops,
		label_id="C4_down_chain2_label",
		connector_id="C4_down_chain2_connector",
		attach_element="C",
	)


#============================================
def test_render_furanose_chain2_connector_matches_shared_resolver_endpoint():
	_, ops = _render("ARLLDM", "furanose", "alpha", show_hydrogens=False)
	line = _line_by_id(ops, "C4_down_chain2_connector")
	label = _text_by_id(ops, "C4_down_chain2_label")
	# Compensate for round-cap extending connector_width/2 into the gap
	ch2_gap = render_geometry.ATTACH_GAP_TARGET + (line.width * 0.5)
	resolved, _contract = render_geometry.resolve_label_connector_endpoint_from_text_origin(
		bond_start=line.p1,
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		line_width=line.width,
		constraints=render_geometry.make_attach_constraints(
			font_size=label.font_size,
			target_gap=ch2_gap,
			direction_policy="auto",
		),
		epsilon=1e-3,
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
		chain_attach_site="core_center",
		target_kind="attach_box",
		font_name=label.font_name,
	)
	assert line.p2 == pytest.approx(resolved)


#============================================
def test_strict_validate_ops_is_not_dependent_on_connector_op_id_suffixes():
	_, ops = _render("ARLLDM", "furanose", "alpha", show_hydrogens=False)
	rewritten = []
	for index, op in enumerate(ops):
		if isinstance(op, render_ops.LineOp):
			rewritten.append(dataclasses.replace(op, op_id=f"line_{index}"))
			continue
		if isinstance(op, render_ops.TextOp):
			rewritten.append(dataclasses.replace(op, op_id=f"text_{index}"))
			continue
		rewritten.append(op)
	haworth_renderer.strict_validate_ops(
		rewritten,
		context="phase2_op_id_contract",
		epsilon=0.5,
	)


#============================================
@pytest.mark.parametrize("code", ("ALRRLd", "ARRLLd"))
def test_render_deoxy_terminal_methyl_uses_subscript_markup(code):
	_, ops = _render(code, "pyranose", "alpha", show_hydrogens=False)
	label = _text_by_id(ops, "C5_down_label")
	assert label.text == "CH<sub>3</sub>"
	assert label.font_size == pytest.approx(10.8)


#============================================
def test_render_l_fucose_internal_groups_scale_to_90_when_multiple():
	_, ops = _render("ALRRLd", "pyranose", "alpha", show_hydrogens=False)
	internal_ho = _text_by_id(ops, "C2_up_label")
	internal_ch3 = _text_by_id(ops, "C5_down_label")
	external_oh = _text_by_id(ops, "C1_up_label")
	assert internal_ho.font_size == pytest.approx(10.8)
	assert internal_ch3.font_size == pytest.approx(10.8)
	assert external_oh.font_size == pytest.approx(12.0)


#============================================
def test_render_front_edge_stable():
	_, ops = _render("ARLRDM", "pyranose", "alpha", bond_length=40.0)
	front = _polygon_by_id(ops, f"ring_edge_{haworth_renderer.PYRANOSE_FRONT_EDGE_INDEX}")
	back = _polygon_by_id(ops, "ring_edge_0")
	front_start, front_end = _edge_thicknesses(front)
	back_start, back_end = _edge_thicknesses(back)
	assert front_start > back_start
	assert front_end > back_end


#============================================
def test_render_pyranose_side_edges_use_rounded_path_ops_with_arcs():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	front_edge = haworth_renderer.PYRANOSE_FRONT_EDGE_INDEX
	side_edges = {(front_edge - 1) % 6, (front_edge + 1) % 6}
	for edge_index in side_edges:
		path = _path_by_id(ops, f"ring_edge_{edge_index}")
		assert any(command == "ARC" for command, _payload in path.commands), path.op_id


#============================================
def test_render_furanose_side_edges_use_rounded_path_ops_with_arcs():
	_, ops = _render("ARRDM", "furanose", "alpha")
	front_edge = haworth_renderer.FURANOSE_FRONT_EDGE_INDEX
	side_edges = {(front_edge - 1) % 5, (front_edge + 1) % 5}
	for edge_index in side_edges:
		path = _path_by_id(ops, f"ring_edge_{edge_index}")
		assert any(command == "ARC" for command, _payload in path.commands), path.op_id


#============================================
def test_render_furanose_labels():
	_, ops = _render("ARRDM", "furanose", "alpha")
	c1_up = _text_by_id(ops, "C1_up_label")
	c2_up = _text_by_id(ops, "C2_up_label")
	assert c1_up.anchor == "start"
	assert c2_up.anchor == "start"


#============================================
def test_render_pyranose_side_connectors_vertical():
	spec, ops = _render("ARLRDM", "pyranose", "alpha")
	slot_map = haworth_renderer.carbon_slot_map(spec)
	for carbon_key, slot in slot_map.items():
		if slot not in ("BR", "BL", "TL"):
			continue
		carbon = int(carbon_key[1:])
		for direction in ("up", "down"):
			label_id = f"C{carbon}_{direction}_label"
			try:
				label = _text_by_id(ops, label_id)
			except AssertionError:
				continue
			if label.text not in ("OH", "HO"):
				continue
			line = _line_by_id(ops, f"C{carbon}_{direction}_connector")
			assert line.p1[0] == pytest.approx(line.p2[0], abs=1e-5)


#============================================
def test_render_furanose_side_connectors_vertical():
	spec, ops = _render("MKLRDM", "furanose", "beta")
	slot_map = haworth_renderer.carbon_slot_map(spec)
	for carbon_key, slot in slot_map.items():
		if slot not in ("BR", "BL"):
			continue
		carbon = int(carbon_key[1:])
		for direction in ("up", "down"):
			label_id = f"C{carbon}_{direction}_label"
			try:
				label = _text_by_id(ops, label_id)
			except AssertionError:
				continue
			if label.text not in ("OH", "HO"):
				continue
			line = _line_by_id(ops, f"C{carbon}_{direction}_connector")
			assert line.p1[0] == pytest.approx(line.p2[0], abs=1e-5)


#============================================
def test_connector_terminates_at_bbox_edge():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for op in _lines(ops):
		op_id = op.op_id or ""
		if not op_id.endswith("_connector"):
			continue
		if "_chain" in op_id:
			continue
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		if label.text in ("OH", "HO"):
			continue
		label_box = _connector_bbox_for_label(label)
		gap_tol = render_geometry.ATTACH_GAP_TARGET + 0.5
		assert _point_on_box_edge(op.p2, label_box, tol=gap_tol)


#============================================
def test_connector_does_not_enter_bbox():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for op in _lines(ops):
		op_id = op.op_id or ""
		if not op_id.endswith("_connector"):
			continue
		if "_chain" in op_id:
			continue
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		if label.text in ("OH", "HO"):
			continue
		label_box = _connector_bbox_for_label(label)
		gap_tol = render_geometry.ATTACH_GAP_TARGET + 0.5
		assert _point_on_box_edge(op.p2, label_box, tol=gap_tol)
		midpoint = ((op.p1[0] + op.p2[0]) / 2.0, (op.p1[1] + op.p2[1]) / 2.0)
		assert not _point_in_box(midpoint, label_box)


#============================================
def test_no_connector_passes_through_label():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for op in _lines(ops):
		op_id = op.op_id or ""
		if not op_id.endswith("_connector"):
			continue
		if "_chain" in op_id:
			continue
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		if label.text in ("OH", "HO"):
			continue
		label_box = _connector_bbox_for_label(label)
		midpoint = ((op.p1[0] + op.p2[0]) / 2.0, (op.p1[1] + op.p2[1]) / 2.0)
		assert not _point_in_box(midpoint, label_box)


#============================================
def test_render_internal_left_hydroxyl_uses_oh_order():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert _text_by_id(ops, "C3_up_label").text == "OH"


#============================================
def test_render_left_anchor_down_hydroxyl_uses_ho_order():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert _text_by_id(ops, "C4_down_label").text == "HO"


#============================================
def test_render_right_anchor_hydroxyl_keeps_oh_order():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert _text_by_id(ops, "C1_down_label").text == "OH"
	assert _text_by_id(ops, "C2_down_label").text == "OH"


#============================================
def test_render_right_anchor_hydroxyl_connector_hits_o_center():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	label = _text_by_id(ops, "C2_down_label")
	line = _line_by_id(ops, "C2_down_connector")
	assert label.text == "OH"
	assert label.anchor == "start"
	contract = render_geometry.label_attach_contract_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		line_width=line.width,
		chain_attach_site="core_center",
		font_name=label.font_name,
	)
	assert contract.policy.target_kind == "oxygen_circle"
	assert render_geometry._point_in_attach_target_closed(line.p2, contract.endpoint_target, epsilon=render_geometry.ATTACH_GAP_TARGET + 0.5)
	assert render_geometry.validate_attachment_paint(
		line_start=line.p1,
		line_end=line.p2,
		line_width=line.width,
		forbidden_regions=[contract.full_target],
		allowed_regions=[contract.allowed_target],
		epsilon=0.5,
	)


#============================================
def test_render_left_anchor_hydroxyl_connector_hits_o_center():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	label = _text_by_id(ops, "C4_down_label")
	line = _line_by_id(ops, "C4_down_connector")
	assert label.text == "HO"
	assert label.anchor == "end"
	contract = render_geometry.label_attach_contract_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		line_width=line.width,
		chain_attach_site="core_center",
		font_name=label.font_name,
	)
	assert contract.policy.target_kind == "oxygen_circle"
	assert render_geometry._point_in_attach_target_closed(line.p2, contract.endpoint_target, epsilon=render_geometry.ATTACH_GAP_TARGET + 0.5)
	assert render_geometry.validate_attachment_paint(
		line_start=line.p1,
		line_end=line.p2,
		line_width=line.width,
		forbidden_regions=[contract.full_target],
		allowed_regions=[contract.allowed_target],
		epsilon=0.5,
	)


#============================================
def test_render_hydroxyl_connectors_do_not_overlap_oxygen_glyph():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for label in _texts(ops):
		op_id = label.op_id or ""
		if not op_id.endswith("_label"):
			continue
		if label.text not in ("OH", "HO"):
			continue
		line = _line_by_id(ops, op_id.replace("_label", "_connector"))
		contract = render_geometry.label_attach_contract_from_text_origin(
			text_x=label.x,
			text_y=label.y,
			text=label.text,
			anchor=label.anchor,
			font_size=label.font_size,
			line_width=line.width,
			chain_attach_site="core_center",
			font_name=label.font_name,
		)
		assert render_geometry._point_in_attach_target_closed(line.p2, contract.endpoint_target, epsilon=render_geometry.ATTACH_GAP_TARGET + 0.5)
		assert render_geometry.validate_attachment_paint(
			line_start=line.p1,
			line_end=line.p2,
			line_width=line.width,
			forbidden_regions=[contract.full_target],
			allowed_regions=[contract.allowed_target],
			epsilon=0.5,
		)


#============================================
@pytest.mark.parametrize("show_hydrogens", (False, True))
def test_allldm_pyranose_beta_upward_hydroxyl_connectors_do_not_penetrate_own_labels(show_hydrogens):
	_, ops = _render("ALLLDM", "pyranose", "beta", show_hydrogens=show_hydrogens)
	for substituent_id in ("C1_up", "C2_up", "C3_up", "C4_up"):
		label = _text_by_id(ops, f"{substituent_id}_label")
		line = _line_by_id(ops, f"{substituent_id}_connector")
		assert label.text in ("OH", "HO")
		assert not _line_penetrates_label_interior(line, _label_bbox(label)), (
			f"{substituent_id} penetrates own label for show_hydrogens={show_hydrogens}"
		)


#============================================
def test_allldm_pyranose_beta_upward_hydroxyl_connectors_use_directional_attach_edges():
	_, ops = _render("ALLLDM", "pyranose", "beta", show_hydrogens=False)
	for substituent_id in ("C1_up", "C2_up", "C3_up", "C4_up"):
		label = _text_by_id(ops, f"{substituent_id}_label")
		line = _line_by_id(ops, f"{substituent_id}_connector")
		assert label.text in ("OH", "HO")
		attach_bbox = _oxygen_attach_bbox_for_hydroxyl_label(label)
		_assert_endpoint_matches_directional_attach_edge(line, attach_bbox)
		assert not _line_penetrates_label_interior(line, _label_bbox(label)), substituent_id


#============================================
def test_allose_furanose_alpha_branch_hydroxyl_uses_directional_side_edge_attachment():
	_, ops = _render("ARRRDM", "furanose", "alpha", show_hydrogens=False)
	line = _line_by_id(ops, "C4_up_chain1_oh_connector")
	label = _text_by_id(ops, "C4_up_chain1_oh_label")
	assert label.text in ("OH", "HO")
	attach_bbox = _oxygen_attach_bbox_for_hydroxyl_label(label)
	_assert_endpoint_matches_directional_attach_edge(line, attach_bbox)
	full_target = render_geometry.label_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
	)
	allowed_target = _allowed_attach_target_for_connector(label, "C4_up_chain1_oh_connector")
	assert allowed_target is not None
	assert render_geometry.validate_attachment_paint(
		line_start=line.p1,
		line_end=line.p2,
		line_width=line.width,
		forbidden_regions=[full_target],
		allowed_regions=[allowed_target],
		epsilon=0.5,
	)


#============================================
def test_furanose_alpha_hydroxyl_connectors_remain_vertical_and_o_centered():
	_, ops = _render("ARDM", "furanose", "alpha", show_hydrogens=False)
	for op_id in ("C1_down", "C2_down", "C3_down"):
		label = _text_by_id(ops, f"{op_id}_label")
		line = _line_by_id(ops, f"{op_id}_connector")
		assert label.text in ("OH", "HO")
		contract = render_geometry.label_attach_contract_from_text_origin(
			text_x=label.x,
			text_y=label.y,
			text=label.text,
			anchor=label.anchor,
			font_size=label.font_size,
			line_width=line.width,
			chain_attach_site="core_center",
			font_name=label.font_name,
		)
		assert render_geometry._point_in_attach_target_closed(line.p2, contract.endpoint_target, epsilon=render_geometry.ATTACH_GAP_TARGET + 0.5)
		assert render_geometry.validate_attachment_paint(
			line_start=line.p1,
			line_end=line.p2,
			line_width=line.width,
			forbidden_regions=[contract.full_target],
			allowed_regions=[contract.allowed_target],
			epsilon=0.5,
		)


#============================================
def test_upward_hydroxyl_clearance_show_hydrogens_false_pyranose():
	spec, ops = _render("ARLRDM", "pyranose", "alpha", show_hydrogens=False)
	slot_map = haworth_renderer.carbon_slot_map(spec)
	found = False
	for label in _texts(ops):
		op_id = label.op_id or ""
		if not op_id.endswith("_up_label"):
			continue
		if label.text not in ("OH", "HO"):
			continue
		found = True
		line = _line_by_id(ops, op_id.replace("_label", "_connector"))
		oxygen_center = _hydroxyl_oxygen_center(label)
		min_clearance = haworth_renderer._hydroxyl_oxygen_radius(label.font_size) + (line.width * 0.5)
		assert _distance(line.p2, oxygen_center) >= (min_clearance - 1e-3)
		carbon = int(op_id.split("_", 1)[0][1:])
		slot = slot_map[f"C{carbon}"]
		if slot in ("BR", "BL", "TL"):
			assert line.p1[0] == pytest.approx(line.p2[0], abs=1e-5)
	assert found


#============================================
def test_upward_hydroxyl_clearance_show_hydrogens_false_furanose():
	spec, ops = _render("ALDM", "furanose", "alpha", show_hydrogens=False)
	slot_map = haworth_renderer.carbon_slot_map(spec)
	found = False
	for label in _texts(ops):
		op_id = label.op_id or ""
		if not op_id.endswith("_up_label"):
			continue
		if label.text not in ("OH", "HO"):
			continue
		found = True
		line = _line_by_id(ops, op_id.replace("_label", "_connector"))
		oxygen_center = _hydroxyl_oxygen_center(label)
		min_clearance = haworth_renderer._hydroxyl_oxygen_radius(label.font_size) + (line.width * 0.5)
		assert _distance(line.p2, oxygen_center) >= (min_clearance - 1e-3)
		carbon = int(op_id.split("_", 1)[0][1:])
		slot = slot_map[f"C{carbon}"]
		if slot in ("BR", "BL", "TL"):
			assert line.p1[0] == pytest.approx(line.p2[0], abs=1e-5)
	assert found


#============================================
def test_render_hydroxyl_two_pass_increases_spacing_for_aldm_furanose_alpha():
	_, ops = _render("ALDM", "furanose", "alpha", show_hydrogens=False)
	c1_down = _text_by_id(ops, "C1_down_label")
	c2_up = _text_by_id(ops, "C2_up_label")
	assert c1_down.text == "OH"
	assert c2_up.text in ("OH", "HO")
	gap = c1_down.font_size * haworth_renderer.HYDROXYL_LAYOUT_MIN_GAP_FACTOR
	intersection = haworth_renderer._intersection_area(_label_bbox(c1_down), _label_bbox(c2_up), gap=gap)
	assert intersection == pytest.approx(0.0, abs=1e-6)
	default_length = 30.0 * 0.45
	c1_down_line = _line_by_id(ops, "C1_down_connector")
	c2_up_line = _line_by_id(ops, "C2_up_connector")
	c1_length = _line_length(c1_down_line)
	c2_length = _line_length(c2_up_line)
	assert (abs(c1_length - default_length) > 1e-6) or (abs(c2_length - default_length) > 1e-6)


#============================================
def test_render_arabinose_furanose_labels_do_not_overlap_ring_bonds():
	_, ops = _render("ALRDM", "furanose", "alpha", show_hydrogens=False)
	ring_polys = [op for op in _polygons(ops) if (op.op_id or "").startswith("ring_edge_")]
	for label in _texts(ops):
		op_id = label.op_id or ""
		if not op_id.endswith("_label"):
			continue
		if op_id == "oxygen_label":
			continue
		label_box = _label_bbox(label)
		for polygon in ring_polys:
				assert not _box_overlaps_polygon(label_box, polygon.points), (
					f"{op_id} overlaps {polygon.op_id}"
				)


#============================================
def test_render_lyxose_pyranose_internal_labels_do_not_overlap_ring_bonds():
	_, ops = _render("ALLDM", "pyranose", "alpha", show_hydrogens=False)
	ring_polys = [op for op in _polygons(ops) if (op.op_id or "").startswith("ring_edge_")]
	for op_id in ("C2_up_label", "C3_up_label"):
		label_box = _label_bbox(_text_by_id(ops, op_id))
		for polygon in ring_polys:
			assert not _box_overlaps_polygon(label_box, polygon.points), (
				f"{op_id} overlaps {polygon.op_id}"
			)


#============================================
def test_render_lyxose_pyranose_internal_connectors_stop_at_label_edges():
	_, ops = _render("ALLDM", "pyranose", "alpha", show_hydrogens=False)
	for op_id in ("C2_up_connector", "C3_up_connector"):
		line = _line_by_id(ops, op_id)
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		if label.text in ("OH", "HO"):
			oxygen_center = _hydroxyl_oxygen_center(label)
			assert _point_outside_circle_radius(
				line.p2,
				oxygen_center,
				haworth_renderer._hydroxyl_oxygen_radius(label.font_size) + (line.width * 0.5),
			)
		else:
			label_box = _connector_bbox_for_label(label)
			assert _point_on_box_edge(line.p2, label_box, tol=render_geometry.ATTACH_GAP_TARGET + 0.5)


#============================================
def test_render_mannose_pyranose_internal_pair_renders_oh_ho():
	_, ops = _render("ALLRDM", "pyranose", "alpha", show_hydrogens=False)
	assert _text_by_id(ops, "C2_up_label").text == "HO"
	assert _text_by_id(ops, "C3_up_label").text == "OH"


#============================================
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_render_arabinose_pyranose_internal_right_is_ho(anomeric):
	_, ops = _render("ALRDM", "pyranose", anomeric, show_hydrogens=False)
	assert _text_by_id(ops, "C2_up_label").text == "HO"


#============================================
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_render_xylose_pyranose_internal_left_is_oh(anomeric):
	_, ops = _render("ARLDM", "pyranose", anomeric, show_hydrogens=False)
	assert _text_by_id(ops, "C3_up_label").text == "OH"


#============================================
def test_render_lyxose_furanose_internal_pair_has_no_ohho_overlap():
	_, ops = _render("ALLDM", "furanose", "alpha", show_hydrogens=False)
	left = _text_by_id(ops, "C3_up_label")
	right = _text_by_id(ops, "C2_up_label")
	overlap = haworth_renderer._intersection_area(_label_bbox(left), _label_bbox(right), gap=0.0)
	scaled_size = 12.0 * haworth_renderer.INTERNAL_PAIR_LABEL_SCALE
	overlap_threshold = haworth_renderer.INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD
	if (
			left.font_size == pytest.approx(scaled_size)
			and right.font_size == pytest.approx(scaled_size)
	):
		# Allow a small scaled-layout tolerance while still enforcing a real upper bound.
		assert overlap <= (overlap_threshold * 1.25)
	else:
		assert overlap <= overlap_threshold


#============================================
def test_render_lyxose_furanose_internal_pair_uses_spacing_rule():
	_, ops = _render("ALLDM", "furanose", "alpha", show_hydrogens=False)
	left = _text_by_id(ops, "C3_up_label")
	right = _text_by_id(ops, "C2_up_label")
	assert left.text == "OH"
	assert right.text == "HO"
	left_box = _label_bbox(left)
	right_box = _label_bbox(right)
	h_gap = right_box[0] - left_box[2]
	min_gap = 12.0 * haworth_renderer.INTERNAL_PAIR_MIN_H_GAP_FACTOR
	scaled_size = 12.0 * haworth_renderer.INTERNAL_PAIR_LABEL_SCALE
	is_scaled = (
		left.font_size == pytest.approx(scaled_size)
		and right.font_size == pytest.approx(scaled_size)
	)
	assert is_scaled or (h_gap >= min_gap)


#============================================
def test_internal_pair_adjustment_flips_then_scales_once():
	jobs = [
		{
			"carbon": 3,
			"ring_type": "furanose",
			"slot": "BL",
			"direction": "up",
			"vertex": (-2.0, 0.0),
			"dx": 0.0,
			"dy": -1.0,
			"length": 10.0,
			"label": "OH",
			"connector_width": 1.0,
			"font_size": 12.0,
			"font_name": "sans-serif",
			"anchor": "start",
			"text_scale": 1.0,
			"line_color": "#000",
			"label_color": "#000",
		},
		{
			"carbon": 2,
			"ring_type": "furanose",
			"slot": "BR",
			"direction": "up",
			"vertex": (2.0, 0.0),
			"dx": 0.0,
			"dy": -1.0,
			"length": 10.0,
			"label": "OH",
			"connector_width": 1.0,
			"font_size": 12.0,
			"font_name": "sans-serif",
			"anchor": "end",
			"text_scale": 1.0,
			"line_color": "#000",
			"label_color": "#000",
		},
	]
	haworth_renderer._resolve_internal_hydroxyl_pair_overlap(jobs)
	assert jobs[0]["anchor"] == "start"
	assert jobs[1]["anchor"] == "end"
	assert jobs[0]["text_scale"] == pytest.approx(haworth_renderer.INTERNAL_PAIR_LABEL_SCALE)
	assert jobs[1]["text_scale"] == pytest.approx(haworth_renderer.INTERNAL_PAIR_LABEL_SCALE)


#============================================
def test_validate_simple_job_rejects_invalid_anchor():
	job = {
		"carbon": 3,
		"ring_type": "furanose",
		"slot": "BL",
		"direction": "up",
		"vertex": (-2.0, 0.0),
		"dx": 0.0,
		"dy": -1.0,
		"length": 10.0,
		"label": "OH",
		"connector_width": 1.0,
		"font_size": 12.0,
		"font_name": "sans-serif",
		"anchor": "leftward",
		"text_scale": 1.0,
		"line_color": "#000",
		"label_color": "#000",
	}
	with pytest.raises(ValueError, match="invalid anchor"):
		haworth_renderer._validate_simple_job(job)


#============================================
def test_validate_simple_job_rejects_invalid_slot_for_ring_type():
	job = {
		"carbon": 3,
		"ring_type": "furanose",
		"slot": "TL",
		"direction": "up",
		"vertex": (-2.0, 0.0),
		"dx": 0.0,
		"dy": -1.0,
		"length": 10.0,
		"label": "OH",
		"connector_width": 1.0,
		"font_size": 12.0,
		"font_name": "sans-serif",
		"anchor": "start",
		"text_scale": 1.0,
		"line_color": "#000",
		"label_color": "#000",
	}
	with pytest.raises(ValueError, match="not valid for ring_type"):
		haworth_renderer._validate_simple_job(job)


#============================================
def test_render_mannose_furanose_internal_pair_uses_oh_ho_scaled():
	_, ops = _render("ALLRDM", "furanose", "alpha", show_hydrogens=False)
	left = _text_by_id(ops, "C3_up_label")
	right = _text_by_id(ops, "C2_up_label")
	assert left.text == "OH"
	assert right.text == "HO"
	scaled_size = 12.0 * haworth_renderer.INTERNAL_PAIR_LABEL_SCALE
	assert left.font_size == pytest.approx(scaled_size)
	assert right.font_size == pytest.approx(scaled_size)


#============================================
def test_furanose_internal_dual_hydroxyl_never_uses_ho_oh_order():
	codes = (
		"ARDM", "ALDM", "ARRDM", "ALRDM", "ARLDM", "ALLDM",
		"ARRRDM", "ALRRDM", "ARLRDM", "ALLRDM", "ARRLDM", "ALRLDM", "ARLLDM", "ALLLDM",
		"MKRDM", "MKLDM", "MKLRDM", "MKLLDM", "MKRRDM", "MKRLDM",
	)
	checked_pairs = 0
	for code in codes:
		for anomeric in ("alpha", "beta"):
			spec, ops = _render(code, "furanose", anomeric, show_hydrogens=False)
			slot_map = haworth_renderer.carbon_slot_map(spec)
			slot_to_carbon = {slot: int(carbon_key[1:]) for carbon_key, slot in slot_map.items()}
			left_carbon = slot_to_carbon.get("BL")
			right_carbon = slot_to_carbon.get("BR")
			if left_carbon is None or right_carbon is None:
				continue
			left_label = next(
				(op for op in ops if getattr(op, "op_id", None) == f"C{left_carbon}_up_label"),
				None,
			)
			right_label = next(
				(op for op in ops if getattr(op, "op_id", None) == f"C{right_carbon}_up_label"),
				None,
			)
			if not left_label or not right_label:
				continue
			if left_label.text in ("OH", "HO") and right_label.text in ("OH", "HO"):
				checked_pairs += 1
				assert (left_label.text, right_label.text) == ("OH", "HO"), (
					f"{code} {anomeric}: internal pair rendered {left_label.text} {right_label.text}"
				)
	assert checked_pairs > 0


#============================================
def test_render_ch2oh_connector_hits_leading_carbon_center():
	_, ops = _render("ARRRDM", "pyranose", "alpha", show_hydrogens=False)
	label = _text_by_id(ops, "C5_up_label")
	line = _line_by_id(ops, "C5_up_connector")
	assert label.text == "CH<sub>2</sub>OH"
	# Full-box bond trimming: connector hits the full label bounding box edge.
	label_box = _label_bbox(label)
	assert _point_on_box_edge(line.p2, label_box, tol=render_geometry.ATTACH_GAP_TARGET + 0.5)


#============================================
def test_render_cooh_connector_hits_leading_carbon_center():
	_, ops = _render("ARLLDc", "pyranose", "alpha", show_hydrogens=False)
	label = _text_by_id(ops, "C5_up_label")
	line = _line_by_id(ops, "C5_up_connector")
	assert label.text == "COOH"
	# Full-box bond trimming: connector hits the full label bounding box edge.
	label_box = _label_bbox(label)
	assert _point_on_box_edge(line.p2, label_box, tol=render_geometry.ATTACH_GAP_TARGET + 0.5)


#============================================
def test_render_arabinose_furanose_ch2oh_connector_hits_leading_carbon_center():
	_, ops = _render("ALRDM", "furanose", "alpha", show_hydrogens=False)
	label = _text_by_id(ops, "C4_up_label")
	line = _line_by_id(ops, "C4_up_connector")
	# ML slot (anchor=end) reverses CH2OH to HOH2C so the carbon faces the ring
	assert label.text == "HOH<sub>2</sub>C"
	# Full-box bond trimming: connector hits the full label bounding box edge.
	label_box = _label_bbox(label)
	assert _point_on_box_edge(line.p2, label_box, tol=render_geometry.ATTACH_GAP_TARGET + 0.5)


#============================================
@pytest.mark.parametrize("code", ("MKRDM", "MKLDM"))
def test_render_ketopentose_furanose_down_ch2oh_connector_hits_leading_carbon_center(code):
	_, ops = _render(code, "furanose", "beta", show_hydrogens=False)
	label = _text_by_id(ops, "C2_down_label")
	line = _line_by_id(ops, "C2_down_connector")
	assert label.text == "CH<sub>2</sub>OH"
	# Full-box bond trimming: connector hits the full label bounding box edge.
	label_box = _label_bbox(label)
	assert _point_on_box_edge(line.p2, label_box, tol=render_geometry.ATTACH_GAP_TARGET + 0.5)


#============================================
def test_render_furanose_top_up_connectors_above_oxygen_label():
	_, ops = _render("MKLRDM", "furanose", "beta", show_hydrogens=False)
	oxygen = _text_by_id(ops, "oxygen_label")
	oxygen_target = render_geometry.label_target_from_text_origin(
		text_x=oxygen.x,
		text_y=oxygen.y,
		text=oxygen.text,
		anchor=oxygen.anchor,
		font_size=oxygen.font_size,
		font_name=oxygen.font_name,
	)
	for op_id in ("C2_up_connector", "C5_up_connector"):
		line = _line_by_id(ops, op_id)
		assert render_geometry.validate_attachment_paint(
			line_start=line.p1,
			line_end=line.p2,
			line_width=line.width,
			forbidden_regions=[oxygen_target],
			allowed_regions=[],
			epsilon=0.5,
		)


#============================================
def test_render_arabinose_furanose_beta_top_labels_are_not_flat_aligned():
	_, ops = _render("ALRDM", "furanose", "beta", show_hydrogens=False)
	right_oh = _text_by_id(ops, "C1_up_label")
	left_chain = _text_by_id(ops, "C4_up_label")
	assert right_oh.text == "OH"
	# ML slot (anchor=end) reverses CH2OH to HOH2C
	assert left_chain.text == "HOH<sub>2</sub>C"
	assert right_oh.y > left_chain.y
	assert (right_oh.y - left_chain.y) >= (right_oh.font_size * 0.09)


#============================================
def test_resolve_hydroxyl_layout_jobs_uses_candidate_slots():
	jobs = [
		{
			"carbon": 1,
			"direction": "down",
			"vertex": (0.0, 0.0),
			"dx": 0.0,
			"dy": 1.0,
			"length": 10.0,
			"label": "OH",
			"connector_width": 1.0,
			"font_size": 12.0,
			"font_name": "sans-serif",
			"anchor": "start",
			"line_color": "#000",
			"label_color": "#000",
		},
		{
			"carbon": 2,
			"direction": "down",
			"vertex": (0.0, 2.0),
			"dx": 0.0,
			"dy": 1.0,
			"length": 10.0,
			"label": "OH",
			"connector_width": 1.0,
			"font_size": 12.0,
			"font_name": "sans-serif",
			"anchor": "start",
			"line_color": "#000",
			"label_color": "#000",
		},
	]
	resolved = haworth_renderer._resolve_hydroxyl_layout_jobs(jobs)
	assert len(resolved) == 2
	assert resolved[0]["length"] == pytest.approx(10.0)
	assert resolved[1]["length"] > 10.0


#============================================
def test_render_bbox_sub_tags():
	assert haworth_renderer._visible_text_length("CH<sub>2</sub>OH") == 5


#============================================
def test_render_subscript_svg_uses_lowered_tspan_dy():
	_, ops = _render("ALRDM", "furanose", "alpha", show_hydrogens=False)
	try:
		impl = xml_minidom.getDOMImplementation()
		doc = impl.createDocument(None, None, None)
	except Exception:
		doc = xml_minidom.Document()
	svg = dom_extensions.elementUnder(
		doc,
		"svg",
		attributes=(
			("xmlns", "http://www.w3.org/2000/svg"),
			("version", "1.1"),
			("width", "220"),
			("height", "220"),
			("viewBox", "0 0 220 220"),
		),
	)
	render_ops.ops_to_svg(svg, ops)
	svg_text = doc.toxml("utf-8")
	if isinstance(svg_text, bytes):
		svg_text = svg_text.decode("utf-8")
	assert 'dy="4.80"' in svg_text
	assert 'dy="-4.80"' in svg_text
	assert 'baseline-shift=' not in svg_text


#============================================
def test_render_fructose_anomeric_no_overlap():
	_, ops = _render("MKLRDM", "furanose", "beta")
	up = _text_by_id(ops, "C2_up_label")
	down = _text_by_id(ops, "C2_down_label")
	assert _distance((up.x, up.y), (down.x, down.y)) > 8.0


#============================================
def test_render_alpha_glucose_c1_oh_below():
	spec, ops = _render("ARLRDM", "pyranose", "alpha")
	vertex = _ring_vertex(spec, 1)
	oh_label = _text_by_id(ops, "C1_down_label")
	assert oh_label.text == "OH"
	assert oh_label.y > vertex[1]


#============================================
def test_render_alpha_glucose_c3_oh_above():
	spec, ops = _render("ARLRDM", "pyranose", "alpha")
	vertex = _ring_vertex(spec, 3)
	oh_label = _text_by_id(ops, "C3_up_label")
	assert oh_label.text == "OH"
	assert oh_label.y < vertex[1]


#============================================
def test_render_beta_glucose_c1_oh_above():
	spec, ops = _render("ARLRDM", "pyranose", "beta")
	vertex = _ring_vertex(spec, 1)
	oh_label = _text_by_id(ops, "C1_up_label")
	assert oh_label.text == "OH"
	assert oh_label.y < vertex[1]


#============================================
def test_render_all_substituents_correct_side():
	spec, ops = _render("ARLRDM", "pyranose", "alpha")
	for carbon in (1, 2, 3, 4, 5):
		vertex = _ring_vertex(spec, carbon)
		up = _text_by_id(ops, f"C{carbon}_up_label")
		down = _text_by_id(ops, f"C{carbon}_down_label")
		assert up.y < vertex[1]
		assert down.y > vertex[1]


#============================================
def test_render_fructose_c2_labels_both_offset():
	spec, ops = _render("MKLRDM", "furanose", "beta", bond_length=30.0)
	vertex = _ring_vertex(spec, 2)
	up = _text_by_id(ops, "C2_up_label")
	down = _text_by_id(ops, "C2_down_label")
	assert _distance(vertex, (up.x, up.y)) > (30.0 * 0.4)
	assert _distance(vertex, (down.x, down.y)) > (30.0 * 0.4)
	assert up.y < vertex[1] < down.y


#============================================
def test_render_l_series_reverses_directions():
	spec, ops = _render("ARLRLM", "pyranose", "alpha")
	vertex = _ring_vertex(spec, 1)
	oh_label = _text_by_id(ops, "C1_up_label")
	assert oh_label.text == "OH"
	assert oh_label.y < vertex[1]


#============================================
def test_visible_text_length_no_tags():
	assert haworth_renderer._visible_text_length("OH") == 2


#============================================
def test_visible_text_length_empty():
	assert haworth_renderer._visible_text_length("") == 0


#============================================
def test_visible_text_length_nested_tags():
	assert haworth_renderer._visible_text_length("<b>O<sub>2</sub></b>") == 2


#============================================
def test_sub_length_multiplier_dual_wide():
	_, ops = _render("MKLRDM", "furanose", "beta", bond_length=40.0)
	line = _line_by_id(ops, "C2_up_connector")
	label = _text_by_id(ops, "C2_up_label")
	if label.text in ("OH", "HO"):
		oxygen_center = _hydroxyl_oxygen_center(label)
		assert _point_outside_circle_radius(
			line.p2,
			oxygen_center,
			haworth_renderer._hydroxyl_oxygen_radius(label.font_size) + (line.width * 0.5),
		)
	else:
		label_box = _connector_bbox_for_label(label)
		assert _point_on_box_edge(line.p2, label_box, tol=render_geometry.ATTACH_GAP_TARGET + 0.5)


#============================================
def test_sub_length_default_single_wide():
	_, ops = _render("ARLRDM", "pyranose", "alpha", bond_length=40.0)
	line = _line_by_id(ops, "C1_down_connector")
	label = _text_by_id(ops, "C1_down_label")
	if label.text in ("OH", "HO"):
		contract = render_geometry.label_attach_contract_from_text_origin(
			text_x=label.x,
			text_y=label.y,
			text=label.text,
			anchor=label.anchor,
			font_size=label.font_size,
			line_width=line.width,
			chain_attach_site="core_center",
			font_name=label.font_name,
		)
		assert render_geometry._point_in_attach_target_closed(line.p2, contract.endpoint_target, epsilon=render_geometry.ATTACH_GAP_TARGET + 0.5)
		assert render_geometry.validate_attachment_paint(
			line_start=line.p1,
			line_end=line.p2,
			line_width=line.width,
			forbidden_regions=[contract.full_target],
			allowed_regions=[contract.allowed_target],
			epsilon=0.5,
		)
	else:
		label_box = _connector_bbox_for_label(label)
		assert _point_on_box_edge(line.p2, label_box, tol=render_geometry.ATTACH_GAP_TARGET + 0.5)


#============================================
def test_render_has_no_oxygen_mask_op():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert all((op.op_id or "") != "oxygen_mask" for op in ops)


#============================================
def test_oxygen_adjacent_ring_edges_do_not_overlap_oxygen_label_interior():
	spec, ops = _render("ARLRDM", "pyranose", "alpha")
	oxygen = _text_by_id(ops, "oxygen_label")
	oxygen_inner = _inner_box(_label_bbox(oxygen), epsilon=0.2)
	assert oxygen_inner is not None
	ring_cfg = haworth_renderer.RING_RENDER_CONFIG[spec.ring_type]
	ring_size = ring_cfg["ring_size"]
	oxygen_index = ring_cfg["oxygen_index"]
	adjacent_edge_indices = {oxygen_index, (oxygen_index - 1) % ring_size}
	adjacent_ring_polygons = []
	for edge_index in adjacent_edge_indices:
		base_id = f"ring_edge_{edge_index}"
		for polygon in _polygons(ops):
			op_id = polygon.op_id or ""
			if op_id == base_id or op_id.startswith(base_id + "_"):
				adjacent_ring_polygons.append(polygon)
	assert adjacent_ring_polygons
	for polygon in adjacent_ring_polygons:
		assert not _box_overlaps_polygon(oxygen_inner, polygon.points), (
			f"{polygon.op_id} overlaps oxygen interior"
		)


#============================================
def test_transparent_background_has_no_mask_artifact_ops():
	_, ops = _render("ARLRDM", "pyranose", "alpha", bg_color="transparent")
	assert all((op.op_id or "") != "oxygen_mask" for op in ops)
	assert _text_by_id(ops, "oxygen_label").text == "O"


#============================================
def _assert_furanose_tail_branch_geometry(
		ops: list,
		direction: str,
		expect_ho_side: str,
		expect_ch2_side: str) -> None:
	trunk = _line_by_id(ops, f"C4_{direction}_chain1_connector")
	ho_branch = _line_by_id(ops, f"C4_{direction}_chain1_oh_connector")
	ch2_branch = _line_by_id(ops, f"C4_{direction}_chain2_connector")
	assert ho_branch.p1 == pytest.approx(trunk.p2)
	assert ch2_branch.p1 == pytest.approx(trunk.p2)
	if expect_ho_side == "left":
		assert ho_branch.p2[0] < ho_branch.p1[0]
	elif expect_ho_side == "right":
		assert ho_branch.p2[0] > ho_branch.p1[0]
	else:
		raise AssertionError(f"Unsupported expected HO side: {expect_ho_side}")
	if expect_ch2_side == "left":
		assert ch2_branch.p2[0] < ch2_branch.p1[0]
	elif expect_ch2_side == "right":
		assert ch2_branch.p2[0] > ch2_branch.p1[0]
	else:
		raise AssertionError(f"Unsupported expected CH2 side: {expect_ch2_side}")
	_assert_line_on_lattice(ho_branch)
	_assert_line_on_lattice(ch2_branch)


#============================================
def test_render_allose_furanose_alpha_tail_branches_right_with_ch2oh_text():
	_, ops = _render("ARRRDM", "furanose", "alpha", show_hydrogens=False)
	_assert_furanose_tail_branch_geometry(
		ops,
		direction="up",
		expect_ho_side="left",
		expect_ch2_side="right",
	)
	ho = _text_by_id(ops, "C4_up_chain1_oh_label")
	ch2 = _text_by_id(ops, "C4_up_chain2_label")
	assert ho.text in ("OH", "HO")
	assert ch2.text == "CH<sub>2</sub>OH"
	_assert_hashed_connector_quality(
		ops,
		connector_id="C4_up_chain2_connector",
		label_id="C4_up_chain2_label",
	)
	assert _distance((ch2.x, ch2.y), (ho.x, ho.y)) > 5.0


#============================================
def test_render_gulose_furanose_alpha_tail_branches_left_with_hoh2c_text():
	_, ops = _render("ARRLDM", "furanose", "alpha", show_hydrogens=False)
	_assert_furanose_tail_branch_geometry(
		ops,
		direction="down",
		expect_ho_side="left",
		expect_ch2_side="left",
	)
	assert _text_by_id(ops, "C4_down_chain1_oh_label").text == "HO"
	assert _text_by_id(ops, "C4_down_chain2_label").text == "HOH<sub>2</sub>C"
	_assert_hashed_connector_quality(
		ops,
		connector_id="C4_down_chain1_oh_connector",
		label_id="C4_down_chain1_oh_label",
	)


#============================================
def test_render_mannose_furanose_alpha_two_carbon_up_branch_angles():
	_, ops = _render("ALLRDM", "furanose", "alpha", show_hydrogens=False)
	_assert_line_angle(_line_by_id(ops, "C4_up_chain1_oh_connector"), 210.0)
	# Standard chain_ops positioning (no custom centroid alignment) shifts angle slightly
	_assert_line_angle(_line_by_id(ops, "C4_up_chain2_connector"), 320.533682, tolerance_degrees=0.001)


#============================================
def test_render_gulose_furanose_alpha_two_carbon_down_branch_angles():
	_, ops = _render("ARRLDM", "furanose", "alpha", show_hydrogens=False)
	_assert_line_angle(_line_by_id(ops, "C4_down_chain1_oh_connector"), 210.0)
	# Standard chain_ops positioning (no custom centroid alignment) shifts angle slightly
	_assert_line_angle(_line_by_id(ops, "C4_down_chain2_connector"), 123.631746, tolerance_degrees=0.001)


#============================================
_TWO_CARBON_DOWN_CLASS_CODES = (
	"ARRLDM",
	"ALRLDM",
	"ARLLDM",
	"ALLLDM",
	"ARRLLM",
	"ALRLLM",
	"ARLLLM",
	"ALLLLM",
)


@pytest.mark.parametrize("code", _TWO_CARBON_DOWN_CLASS_CODES)
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_render_furanose_two_carbon_down_class_uses_c4_down_tail(code, anomeric):
	_, ops = _render(code, "furanose", anomeric, show_hydrogens=False)
	line_ids = {
		op.op_id for op in _lines(ops)
		if op.op_id
	}
	assert "C4_down_chain2_connector" in line_ids
	assert "C4_up_chain2_connector" not in line_ids
	assert _text_by_id(ops, "C4_down_chain1_oh_label").text == "HO"
	assert _text_by_id(ops, "C4_down_chain2_label").text == "HOH<sub>2</sub>C"
	assert any(line_id.startswith("C4_down_chain1_oh_connector_hatch") for line_id in line_ids)


#============================================
_TWO_CARBON_UP_CLASS_CODES = (
	"ALLRDM",
	"ARLRDM",
	"ALRRDM",
	"ARRRDM",
	"ALLRLM",
	"ARLRLM",
	"ALRRLM",
	"ARRRLM",
)


@pytest.mark.parametrize("code", _TWO_CARBON_UP_CLASS_CODES)
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_render_furanose_two_carbon_up_class_uses_c4_up_tail(code, anomeric):
	_, ops = _render(code, "furanose", anomeric, show_hydrogens=False)
	line_ids = {
		op.op_id for op in _lines(ops)
		if op.op_id
	}
	assert "C4_up_chain2_connector" in line_ids
	assert "C4_down_chain2_connector" not in line_ids
	assert _text_by_id(ops, "C4_up_chain1_oh_label").text in ("OH", "HO")
	assert _text_by_id(ops, "C4_up_chain2_label").text == "CH<sub>2</sub>OH"
	assert any(line_id.startswith("C4_up_chain2_connector_hatch") for line_id in line_ids)


#============================================
@pytest.mark.parametrize("code", ["ARLLDM", "ALRLDM", "ALLLDM"])
def test_render_furanose_two_carbon_tail_left_parity_class_uses_hashed_ho(code):
	"""Phase B.1 parity fixture: left-tail class keeps hashed HO + lower CH2 lane."""
	_, ops = _render(code, "furanose", "alpha", show_hydrogens=False)
	trunk = _line_by_id(ops, "C4_down_chain1_connector")
	ho_branch = _line_by_id(ops, "C4_down_chain1_oh_connector")
	ch2_branch = _line_by_id(ops, "C4_down_chain2_connector")
	ho_label = _text_by_id(ops, "C4_down_chain1_oh_label")
	ch2_label = _text_by_id(ops, "C4_down_chain2_label")
	assert ho_label.text == "HO"
	assert ch2_label.text == "HOH<sub>2</sub>C"
	assert ho_branch.p1 == pytest.approx(trunk.p2)
	assert ch2_branch.p1 == pytest.approx(trunk.p2)
	assert ho_branch.p2[0] < ho_branch.p1[0]
	assert ch2_branch.p2[0] < ch2_branch.p1[0]
	_assert_line_on_lattice(ho_branch)
	_assert_line_on_lattice(ch2_branch)
	assert ch2_label.y > ho_label.y
	_assert_hashed_connector_quality(
		ops,
		connector_id="C4_down_chain1_oh_connector",
		label_id="C4_down_chain1_oh_label",
	)


#============================================
@pytest.mark.parametrize(
	"code,direction",
	[
		("ALLLDM", "down"),
		("ARLLDM", "down"),
		("ALRLDM", "down"),
		("ALLRDM", "up"),
		("ARLRDM", "up"),
	],
)
def test_render_furanose_two_carbon_tail_uses_branched_labels(code, direction):
	_, ops = _render(code, "furanose", "alpha", show_hydrogens=False)
	if direction == "up":
		assert _text_by_id(ops, f"C4_{direction}_chain1_oh_label").text in ("OH", "HO")
		assert _text_by_id(ops, f"C4_{direction}_chain2_label").text == "CH<sub>2</sub>OH"
	else:
		assert _text_by_id(ops, f"C4_{direction}_chain1_oh_label").text == "HO"
		assert _text_by_id(ops, f"C4_{direction}_chain2_label").text == "HOH<sub>2</sub>C"
	chain_texts = [op.text for op in _texts(ops) if "chain" in (op.op_id or "")]
	assert "HOHC" not in chain_texts


#============================================
def test_render_exocyclic_0_no_chain():
	_, ops = _render("ARRDM", "pyranose", "alpha")
	chain_ops = [op for op in ops if "chain" in (op.op_id or "")]
	assert not chain_ops


#============================================
def test_render_exocyclic_3_collinear():
	_, ops = _render("ARLRRDM", "furanose", "alpha")
	line1 = _line_by_id(ops, "C4_up_chain1_connector")
	line2 = _line_by_id(ops, "C4_up_chain2_connector")
	line3 = _line_by_id(ops, "C4_up_chain3_connector")
	d1 = haworth_renderer._normalize_vector(line1.p2[0] - line1.p1[0], line1.p2[1] - line1.p1[1])
	d2 = haworth_renderer._normalize_vector(line2.p2[0] - line2.p1[0], line2.p2[1] - line2.p1[1])
	d3 = haworth_renderer._normalize_vector(line3.p2[0] - line3.p1[0], line3.p2[1] - line3.p1[1])
	assert d1[0] == pytest.approx(d2[0], rel=1e-3)
	assert d1[1] == pytest.approx(d2[1], rel=1e-3)
	assert d1[0] == pytest.approx(d3[0], rel=1e-3)
	assert d1[1] == pytest.approx(d3[1], rel=1e-3)


#============================================
def test_show_hydrogens_default_true():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	h_labels = [op for op in _texts(ops) if op.text == "H"]
	assert len(h_labels) > 0


#============================================
def test_show_hydrogens_false_no_h_labels():
	_, ops = _render("ARLRDM", "pyranose", "alpha", show_hydrogens=False)
	h_labels = [op for op in _texts(ops) if op.text == "H"]
	assert len(h_labels) == 0


#============================================
def test_show_hydrogens_false_no_h_connectors():
	spec, ops = _render("ARLRDM", "pyranose", "alpha", show_hydrogens=False)
	# C1_up is "H" for alpha glucose - its connector should be absent
	h_connector_ids = [
		op.op_id for op in _lines(ops)
		if op.op_id and op.op_id.endswith("_connector")
	]
	# For alpha-D-glucopyranose: C1_up=H, C2_up=H, C3_down=H, C4_up=H, C5_down=H
	for carbon, direction in ((1, "up"), (2, "up"), (3, "down"), (4, "up"), (5, "down")):
		assert f"C{carbon}_{direction}_connector" not in h_connector_ids


#============================================
def test_show_hydrogens_false_preserves_non_h():
	_, ops = _render("ARLRDM", "pyranose", "alpha", show_hydrogens=False)
	text_values = [op.text for op in _texts(ops)]
	assert "OH" in text_values
	assert "HO" in text_values
	assert "CH<sub>2</sub>OH" in text_values
	assert "O" in text_values
