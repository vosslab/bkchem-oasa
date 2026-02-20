#!/usr/bin/env python3
"""Parity tests: run graph algorithms through OASA and rustworkx, assert matching results.

Each test class exercises one graph algorithm across all fixture molecules,
comparing OASA output against the equivalent rustworkx operation.
"""

# Standard Library
import sys
import os

# PIP3 modules
import numpy
import pytest
import rustworkx

# ensure oasa is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# local repo modules
import graph_test_fixtures


# build fixtures once, parametrize by name
ALL_FIXTURES = graph_test_fixtures.get_all_fixtures()
FIXTURE_IDS = [f["name"] for f in ALL_FIXTURES]
CONNECTED_FIXTURES = [f for f in ALL_FIXTURES if f["expected"]["is_connected"]]
CONNECTED_IDS = [f["name"] for f in CONNECTED_FIXTURES]


#============================================
class TestConnectedComponents:
	"""Compare connected component counts and sizes between OASA and rustworkx."""

	@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=FIXTURE_IDS)
	def test_component_count(self, fixture):
		"""Assert same number of connected components."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		# OASA returns a generator of sets of vertices
		oasa_comps = list(mol.get_connected_components())
		# rustworkx returns a list of sets of node indices
		rx_comps = rustworkx.connected_components(rx_g)
		assert len(oasa_comps) == len(rx_comps)

	@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=FIXTURE_IDS)
	def test_component_sizes(self, fixture):
		"""Assert same component sizes (sorted) between OASA and rustworkx."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		oasa_sizes = sorted(len(c) for c in mol.get_connected_components())
		rx_sizes = sorted(len(c) for c in rustworkx.connected_components(rx_g))
		assert oasa_sizes == rx_sizes


#============================================
class TestIsConnected:
	"""Compare connectivity check between OASA and rustworkx."""

	@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=FIXTURE_IDS)
	def test_is_connected(self, fixture):
		"""Assert identical boolean result for is_connected."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		oasa_result = mol.is_connected()
		rx_result = rustworkx.is_connected(rx_g)
		assert bool(oasa_result) == bool(rx_result)


#============================================
class TestPathExists:
	"""Compare path existence checks between OASA and rustworkx."""

	@pytest.mark.parametrize("fixture", CONNECTED_FIXTURES, ids=CONNECTED_IDS)
	def test_path_exists_connected(self, fixture):
		"""For connected graphs, path should exist between first and last vertex."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		v_to_i = fixture["v_to_i"]
		verts = mol.vertices
		if len(verts) < 2:
			pytest.skip("Need at least 2 vertices for path test")
		v0, v1 = verts[0], verts[-1]
		i0, i1 = v_to_i[v0], v_to_i[v1]
		oasa_result = mol.path_exists(v0, v1)
		rx_result = rustworkx.has_path(rx_g, i0, i1)
		assert bool(oasa_result) == bool(rx_result)

	def test_path_not_exists_disconnected(self):
		"""For disconnected graph, vertices in different components have no path."""
		fixture = graph_test_fixtures.make_disconnected()
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		v_to_i = fixture["v_to_i"]
		# get components to find vertices in different components
		comps = list(mol.get_connected_components())
		assert len(comps) == 2
		v0 = next(iter(comps[0]))
		v1 = next(iter(comps[1]))
		i0, i1 = v_to_i[v0], v_to_i[v1]
		oasa_result = mol.path_exists(v0, v1)
		rx_result = rustworkx.has_path(rx_g, i0, i1)
		assert bool(oasa_result) is False
		assert bool(rx_result) is False


#============================================
class TestDiameter:
	"""Compare graph diameter between OASA and rustworkx."""

	@pytest.mark.parametrize("fixture", CONNECTED_FIXTURES, ids=CONNECTED_IDS)
	def test_diameter(self, fixture):
		"""Assert identical diameter values."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		# flush OASA cache to avoid stale values
		mol._flush_cache()
		oasa_diameter = mol.get_diameter()
		# rustworkx: max entry in distance matrix
		dist_matrix = rustworkx.distance_matrix(rx_g)
		rx_diameter = int(numpy.max(dist_matrix))
		assert oasa_diameter == rx_diameter


#============================================
class TestCycleBasis:
	"""Compare independent cycle counts between OASA and rustworkx."""

	@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=FIXTURE_IDS)
	def test_cycle_count(self, fixture):
		"""Assert same number of independent cycles."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		oasa_cycles = mol.get_smallest_independent_cycles()
		rx_cycles = rustworkx.cycle_basis(rx_g)
		assert len(oasa_cycles) == len(rx_cycles)

	def test_benzene_single_cycle_of_six(self):
		"""Benzene should have exactly 1 cycle of size 6."""
		fixture = graph_test_fixtures.make_benzene()
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		oasa_cycles = mol.get_smallest_independent_cycles()
		rx_cycles = rustworkx.cycle_basis(rx_g)
		assert len(oasa_cycles) == 1
		assert len(rx_cycles) == 1
		# OASA cycles are lists of vertices; check length is 6
		assert len(oasa_cycles[0]) == 6
		# rustworkx cycles are lists of node indices
		assert len(rx_cycles[0]) == 6

	def test_cholesterol_four_cycles(self):
		"""Cholesterol should have exactly 4 independent cycles."""
		fixture = graph_test_fixtures.make_cholesterol()
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		oasa_cycles = mol.get_smallest_independent_cycles()
		rx_cycles = rustworkx.cycle_basis(rx_g)
		assert len(oasa_cycles) == 4
		assert len(rx_cycles) == 4


#============================================
class TestDistanceFrom:
	"""Compare BFS distance results between OASA and rustworkx."""

	@pytest.mark.parametrize("fixture", CONNECTED_FIXTURES, ids=CONNECTED_IDS)
	def test_max_distance(self, fixture):
		"""Assert max distance from first vertex matches between backends."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		v_to_i = fixture["v_to_i"]
		verts = mol.vertices
		v0 = verts[0]
		i0 = v_to_i[v0]
		# OASA: mark_vertices_with_distance_from returns max distance
		oasa_max = mol.mark_vertices_with_distance_from(v0)
		# rustworkx: row in distance matrix for source node
		dist_matrix = rustworkx.distance_matrix(rx_g)
		rx_max = int(numpy.max(dist_matrix[i0]))
		assert oasa_max == rx_max

	@pytest.mark.parametrize("fixture", CONNECTED_FIXTURES, ids=CONNECTED_IDS)
	def test_per_vertex_distances(self, fixture):
		"""Assert per-vertex BFS distances match between OASA and rustworkx."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		v_to_i = fixture["v_to_i"]
		verts = mol.vertices
		v0 = verts[0]
		i0 = v_to_i[v0]
		# run OASA BFS
		mol.mark_vertices_with_distance_from(v0)
		# get rustworkx distance matrix row
		dist_matrix = rustworkx.distance_matrix(rx_g)
		# compare each vertex distance
		for v in verts:
			oasa_dist = v.properties_.get("d", 0)
			rx_dist = int(dist_matrix[i0][v_to_i[v]])
			assert oasa_dist == rx_dist, (
				f"Distance mismatch for vertex in {fixture['name']}: "
				f"OASA={oasa_dist}, rx={rx_dist}"
			)


#============================================
class TestBridges:
	"""Compare bridge edge detection between OASA and rustworkx.

	Known issue: rustworkx.bridges() misses the bridge incident to the
	DFS root node (node index 0), causing an off-by-one undercount when
	the root has a bridge edge. We tolerate a difference of at most 1
	(OASA >= rustworkx) for connected graphs with bridges.
	"""

	@pytest.mark.parametrize("fixture", CONNECTED_FIXTURES, ids=CONNECTED_IDS)
	def test_bridge_count(self, fixture):
		"""Compare bridge counts between OASA and rustworkx."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		# OASA: check each edge individually
		oasa_bridge_count = sum(
			1 for e in mol.edges if mol.is_edge_a_bridge(e)
		)
		# rustworkx: bridges returns set of (u, v) tuples
		rx_bridge_count = len(rustworkx.bridges(rx_g))
		# both should agree on zero vs nonzero
		if oasa_bridge_count == 0:
			assert rx_bridge_count == 0, (
				f"{fixture['name']}: OASA=0 bridges but rx={rx_bridge_count}"
			)
		else:
			# rustworkx may undercount by 1 due to root-edge bug
			assert oasa_bridge_count >= rx_bridge_count, (
				f"{fixture['name']}: OASA={oasa_bridge_count} < rx={rx_bridge_count}"
			)
			assert oasa_bridge_count - rx_bridge_count <= 1, (
				f"{fixture['name']}: bridge gap too large: "
				f"OASA={oasa_bridge_count}, rx={rx_bridge_count}"
			)


#============================================
class TestFindPathBetween:
	"""Compare path finding between OASA and rustworkx."""

	@pytest.mark.parametrize("fixture", CONNECTED_FIXTURES, ids=CONNECTED_IDS)
	def test_path_validity(self, fixture):
		"""Both backends find valid paths; rustworkx path <= OASA path length."""
		mol = fixture["oasa_mol"]
		rx_g = fixture["rx_graph"]
		v_to_i = fixture["v_to_i"]
		verts = mol.vertices
		if len(verts) < 2:
			pytest.skip("Need at least 2 vertices for path test")
		v0, v1 = verts[0], verts[-1]
		i0, i1 = v_to_i[v0], v_to_i[v1]
		# OASA path: list of vertices from end to start
		oasa_path = mol.find_path_between(v0, v1)
		assert oasa_path is not None, f"OASA found no path in {fixture['name']}"
		# OASA path length is number of edges = len(vertices) - 1
		oasa_path_len = len(oasa_path) - 1
		# rustworkx: dijkstra returns dict {target: [path_nodes]}
		rx_paths = rustworkx.dijkstra_shortest_paths(rx_g, i0, target=i1)
		assert i1 in rx_paths, f"rustworkx found no path in {fixture['name']}"
		rx_path = rx_paths[i1]
		rx_path_len = len(rx_path) - 1
		# rustworkx guarantees shortest path
		assert rx_path_len <= oasa_path_len, (
			f"{fixture['name']}: rx shortest={rx_path_len} > oasa={oasa_path_len}"
		)
		# verify both paths start and end correctly
		# OASA path goes end->start, so last element is start
		assert oasa_path[-1] == v0, "OASA path does not start at v0"
		assert oasa_path[0] == v1, "OASA path does not end at v1"
		# rustworkx path goes start->end
		assert rx_path[0] == i0, "rustworkx path does not start at i0"
		assert rx_path[-1] == i1, "rustworkx path does not end at i1"
