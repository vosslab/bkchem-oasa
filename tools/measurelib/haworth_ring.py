"""Haworth ring detection for glyph-bond alignment measurement."""

# Standard Library
import math

from measurelib.constants import HAWORTH_RING_MIN_PRIMITIVES, HAWORTH_RING_SEARCH_RADIUS
from measurelib.util import length_stats, line_endpoints, line_length
from measurelib.geometry import points_close


#============================================
def canonical_cycle_key(node_indexes: list[int]) -> tuple[int, ...]:
	"""Return rotation- and direction-invariant tuple for one cycle."""
	sequence = tuple(node_indexes)
	reverse_sequence = tuple(reversed(node_indexes))
	candidates = []
	for sequence_variant in (sequence, reverse_sequence):
		for start in range(len(sequence_variant)):
			candidate = sequence_variant[start:] + sequence_variant[:start]
			candidates.append(candidate)
	return min(candidates)


#============================================
def cycle_node_pairs(node_cycle: tuple[int, ...]) -> list[tuple[int, int]]:
	"""Return normalized node-pairs for one closed cycle."""
	pairs = []
	for index, node_value in enumerate(node_cycle):
		next_node = node_cycle[(index + 1) % len(node_cycle)]
		pairs.append((min(node_value, next_node), max(node_value, next_node)))
	return pairs


#============================================
def clustered_endpoint_graph(
		lines: list[dict],
		line_indexes: list[int],
		merge_tol: float = 1.5) -> tuple[
			list[tuple[float, float]], dict[int, tuple[int, int]],
			dict[int, set[int]], dict[tuple[int, int], list[int]]]:
	"""Build clustered endpoint graph for a subset of line indexes."""
	nodes: list[tuple[float, float]] = []
	line_to_nodes: dict[int, tuple[int, int]] = {}
	adjacency: dict[int, set[int]] = {}
	edge_to_lines: dict[tuple[int, int], list[int]] = {}
	for line_index in line_indexes:
		line = lines[line_index]
		p1, p2 = line_endpoints(line)
		node_indexes = []
		for point in (p1, p2):
			matched_node = None
			for node_index, node_point in enumerate(nodes):
				if points_close(point, node_point, tol=merge_tol):
					matched_node = node_index
					break
			if matched_node is None:
				nodes.append(point)
				matched_node = len(nodes) - 1
			node_indexes.append(matched_node)
		n1, n2 = node_indexes
		if n1 == n2:
			continue
		line_to_nodes[line_index] = (n1, n2)
		adjacency.setdefault(n1, set()).add(n2)
		adjacency.setdefault(n2, set()).add(n1)
		key = (min(n1, n2), max(n1, n2))
		edge_to_lines.setdefault(key, []).append(line_index)
	return nodes, line_to_nodes, adjacency, edge_to_lines


#============================================
def find_candidate_cycles(adjacency: dict[int, set[int]], min_size: int = 5, max_size: int = 6) -> list[tuple[int, ...]]:
	"""Find simple cycles of allowed sizes in one undirected adjacency graph."""
	cycles: set[tuple[int, ...]] = set()
	for start in sorted(adjacency.keys()):
		stack = [(start, [start])]
		while stack:
			node_value, path = stack.pop()
			if len(path) > max_size:
				continue
			for neighbor in adjacency.get(node_value, set()):
				if neighbor == start and min_size <= len(path) <= max_size:
					cycle = canonical_cycle_key(path[:])
					cycles.add(cycle)
					continue
				if neighbor in path:
					continue
				if len(path) >= max_size:
					continue
				stack.append((neighbor, path + [neighbor]))
	return sorted(cycles)


#============================================
def empty_haworth_ring_detection() -> dict:
	"""Return default no-detection payload for Haworth base ring analysis."""
	return {
		"detected": False,
		"line_indexes": [],
		"primitive_indexes": [],
		"node_count": 0,
		"centroid": None,
		"radius": 0.0,
		"score": None,
		"source": None,
	}


#============================================
def detect_haworth_ring_from_line_cycles(lines: list[dict], labels: list[dict]) -> dict:
	"""Detect Haworth-like base ring cycle from line geometry."""
	line_indexes = list(range(len(lines)))
	if len(line_indexes) < HAWORTH_RING_MIN_PRIMITIVES:
		return empty_haworth_ring_detection()
	nodes, _, adjacency, edge_to_lines = clustered_endpoint_graph(lines, line_indexes, merge_tol=1.5)
	cycles = find_candidate_cycles(adjacency, min_size=5, max_size=6)
	best = None
	for cycle in cycles:
		node_pairs = cycle_node_pairs(cycle)
		cycle_line_indexes = []
		for pair in node_pairs:
			line_options = edge_to_lines.get(pair, [])
			if not line_options:
				cycle_line_indexes = []
				break
			cycle_line_indexes.append(line_options[0])
		if len(cycle_line_indexes) < HAWORTH_RING_MIN_PRIMITIVES:
			continue
		node_points = [nodes[node_index] for node_index in cycle]
		centroid_x = sum(point[0] for point in node_points) / float(len(node_points))
		centroid_y = sum(point[1] for point in node_points) / float(len(node_points))
		radii = [math.hypot(point[0] - centroid_x, point[1] - centroid_y) for point in node_points]
		radius_stats = length_stats(radii)
		if radius_stats["mean"] <= 4.0 or radius_stats["mean"] > HAWORTH_RING_SEARCH_RADIUS:
			continue
		if radius_stats["coefficient_of_variation"] > 0.55:
			continue
		cycle_lengths = [line_length(lines[line_index]) for line_index in cycle_line_indexes]
		cycle_length_stats = length_stats(cycle_lengths)
		if cycle_length_stats["mean"] <= 2.0 or cycle_length_stats["coefficient_of_variation"] > 0.7:
			continue
		has_oxygen = False
		for label in labels:
			if str(label["text"]).upper() != "O":
				continue
			distance = math.hypot(label["x"] - centroid_x, label["y"] - centroid_y)
			if distance <= (radius_stats["mean"] * 1.8):
				has_oxygen = True
				break
		score = (
			radius_stats["coefficient_of_variation"]
			+ cycle_length_stats["coefficient_of_variation"]
			+ abs(len(cycle) - 6) * 0.15
		)
		if has_oxygen:
			score -= 0.15
		candidate = {
			"detected": True,
			"line_indexes": sorted(set(cycle_line_indexes)),
			"primitive_indexes": [],
			"node_count": len(cycle),
			"centroid": [centroid_x, centroid_y],
			"radius": radius_stats["mean"],
			"score": score,
			"source": "line_cycle",
		}
		if best is None or candidate["score"] < best["score"]:
			best = candidate
	if best is not None:
		return best
	return empty_haworth_ring_detection()


#============================================
def detect_haworth_ring_from_primitives(primitives: list[dict], labels: list[dict]) -> dict:
	"""Detect Haworth-like base ring from filled polygon/path primitive clusters."""
	if len(primitives) < HAWORTH_RING_MIN_PRIMITIVES:
		return empty_haworth_ring_detection()
	best_candidate = None
	for index, primitive in enumerate(primitives):
		center_x, center_y = primitive["centroid"]
		members = []
		for other_index, other in enumerate(primitives):
			ox, oy = other["centroid"]
			if math.hypot(ox - center_x, oy - center_y) <= HAWORTH_RING_SEARCH_RADIUS:
				members.append(other_index)
		if len(members) < HAWORTH_RING_MIN_PRIMITIVES:
			continue
		member_centers = [primitives[member]["centroid"] for member in members]
		candidate_center_x = sum(point[0] for point in member_centers) / float(len(member_centers))
		candidate_center_y = sum(point[1] for point in member_centers) / float(len(member_centers))
		radii = [
			math.hypot(point[0] - candidate_center_x, point[1] - candidate_center_y)
			for point in member_centers
		]
		radius_stats = length_stats(radii)
		if radius_stats["mean"] <= 2.0 or radius_stats["mean"] > HAWORTH_RING_SEARCH_RADIUS:
			continue
		if radius_stats["coefficient_of_variation"] > 0.8:
			continue
		oxygen_bonus = 0.0
		for label in labels:
			if str(label["text"]).upper() != "O":
				continue
			distance = math.hypot(label["x"] - candidate_center_x, label["y"] - candidate_center_y)
			if distance <= (radius_stats["mean"] * 2.2):
				oxygen_bonus = 0.15
				break
		score = radius_stats["coefficient_of_variation"] - oxygen_bonus - (0.02 * len(members))
		candidate = {
			"detected": True,
			"line_indexes": [],
			"primitive_indexes": sorted(set(members)),
			"node_count": len(members),
			"centroid": [candidate_center_x, candidate_center_y],
			"radius": radius_stats["mean"],
			"score": score,
			"source": "filled_primitive_cluster",
		}
		if best_candidate is None or candidate["score"] < best_candidate["score"]:
			best_candidate = candidate
	if best_candidate is not None:
		return best_candidate
	return empty_haworth_ring_detection()


#============================================
def detect_haworth_base_ring(lines: list[dict], labels: list[dict], ring_primitives: list[dict]) -> dict:
	"""Detect Haworth base ring using line-cycle and filled-primitive heuristics."""
	line_detection = detect_haworth_ring_from_line_cycles(lines, labels)
	primitive_detection = detect_haworth_ring_from_primitives(ring_primitives, labels)
	if not line_detection["detected"] and not primitive_detection["detected"]:
		return empty_haworth_ring_detection()
	if line_detection["detected"] and not primitive_detection["detected"]:
		return line_detection
	if primitive_detection["detected"] and not line_detection["detected"]:
		return primitive_detection
	if primitive_detection["score"] <= line_detection["score"]:
		return primitive_detection
	return line_detection


#============================================
def oxygen_virtual_connector_lines(
		haworth_ring: dict,
		labels: list[dict],
		ring_primitives: list[dict]) -> list[dict]:
	"""Synthesize virtual line dicts from oxygen-adjacent ring polygon edges.

	When the Haworth ring is detected via filled polygon primitives, the ring
	oxygen label has no nearby <line> endpoint for gap measurement.  This
	function finds the two ring polygon edges adjacent to the O label and
	returns virtual line dicts (center-axis of each trapezoid) so the
	measurement pipeline can treat them like normal connector lines.

	Args:
		haworth_ring: Detection result from detect_haworth_base_ring().
		labels: Parsed SVG text labels.
		ring_primitives: Filled polygon/path primitives from collect_svg_ring_primitives().

	Returns:
		List of virtual line dicts with keys x1, y1, x2, y2, width, virtual_ring_edge.
	"""
	if not haworth_ring.get("detected"):
		return []
	if haworth_ring.get("source") != "filled_primitive_cluster":
		return []
	centroid = haworth_ring.get("centroid")
	radius = float(haworth_ring.get("radius", 0.0))
	if centroid is None or radius <= 0.0:
		return []
	# find the O label nearest the ring centroid
	cx, cy = float(centroid[0]), float(centroid[1])
	o_label = None
	o_dist = float("inf")
	for label in labels:
		if str(label.get("text", "")).upper() != "O":
			continue
		dist = math.hypot(float(label["x"]) - cx, float(label["y"]) - cy)
		if dist <= radius * 2.0 and dist < o_dist:
			o_label = label
			o_dist = dist
	if o_label is None:
		return []
	o_x = float(o_label["x"])
	o_y = float(o_label["y"])
	# collect primitive indexes belonging to the detected ring
	primitive_indexes = haworth_ring.get("primitive_indexes", [])
	if not primitive_indexes:
		return []
	# rank primitives by distance from O label, pick closest 2
	scored = []
	for prim_idx in primitive_indexes:
		if prim_idx < 0 or prim_idx >= len(ring_primitives):
			continue
		prim = ring_primitives[prim_idx]
		prim_cx, prim_cy = prim["centroid"]
		dist = math.hypot(prim_cx - o_x, prim_cy - o_y)
		scored.append((dist, prim_idx))
	scored.sort()
	# take the two closest primitives (one on each side of O)
	top_primitives = scored[:2]
	virtual_lines = []
	for _, prim_idx in top_primitives:
		prim = ring_primitives[prim_idx]
		points = prim.get("points", ())
		if len(points) < 4:
			continue
		# compute center axis: midpoint of edge 0-1 and midpoint of edge 2-3
		mid_a_x = (points[0][0] + points[1][0]) * 0.5
		mid_a_y = (points[0][1] + points[1][1]) * 0.5
		mid_b_x = (points[2][0] + points[3][0]) * 0.5
		mid_b_y = (points[2][1] + points[3][1]) * 0.5
		# orient so the end closer to the O label is x2,y2
		dist_a = math.hypot(mid_a_x - o_x, mid_a_y - o_y)
		dist_b = math.hypot(mid_b_x - o_x, mid_b_y - o_y)
		if dist_a <= dist_b:
			# end A is closer to O
			line_x1, line_y1 = mid_b_x, mid_b_y
			line_x2, line_y2 = mid_a_x, mid_a_y
		else:
			# end B is closer to O
			line_x1, line_y1 = mid_a_x, mid_a_y
			line_x2, line_y2 = mid_b_x, mid_b_y
		virtual_lines.append({
			"x1": line_x1,
			"y1": line_y1,
			"x2": line_x2,
			"y2": line_y2,
			"width": 0.0,
			"virtual_ring_edge": True,
		})
	return virtual_lines
