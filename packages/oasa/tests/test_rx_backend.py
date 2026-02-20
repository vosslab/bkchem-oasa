#!/usr/bin/env python3
"""Unit tests for the RxBackend adapter.

Tests cover initialization, mirror operations, rebuild, lazy sync,
algorithm delegates, and invalidation.
"""

# Standard Library
import sys

# local repo modules
sys.path.insert(0, "packages/oasa")
from oasa.graph.rx_backend import RxBackend
from oasa.graph.graph_lib import Graph
from oasa.graph.vertex_lib import Vertex
from oasa.graph.edge_lib import Edge
import graph_test_fixtures


#============================================
class TestRxBackendInit:
	"""Test empty backend initialization."""

	#============================================
	def test_empty_backend_node_count(self):
		"""Empty backend should have 0 nodes."""
		backend = RxBackend()
		assert len(backend.rx) == 0

	#============================================
	def test_empty_backend_edge_count(self):
		"""Empty backend should have 0 edges."""
		backend = RxBackend()
		assert len(backend.rx.edge_list()) == 0

	#============================================
	def test_empty_backend_is_dirty(self):
		"""Empty backend should be marked dirty."""
		backend = RxBackend()
		assert backend._dirty is True

	#============================================
	def test_empty_backend_maps_empty(self):
		"""All identity maps should be empty on init."""
		backend = RxBackend()
		assert len(backend.v_to_i) == 0
		assert len(backend.i_to_v) == 0
		assert len(backend.e_to_i) == 0
		assert len(backend.i_to_e) == 0


#============================================
class TestRxBackendMirrorOps:
	"""Test individual mirror operations (add/remove node/edge)."""

	#============================================
	def test_add_node_creates_mapping(self):
		"""Adding a node should populate v_to_i and i_to_v maps."""
		backend = RxBackend()
		v = Vertex()
		idx = backend.add_node(v)
		assert backend.v_to_i[v] == idx
		assert backend.i_to_v[idx] is v
		assert len(backend.rx) == 1

	#============================================
	def test_add_multiple_nodes(self):
		"""Adding multiple nodes should produce unique indices."""
		backend = RxBackend()
		v1 = Vertex()
		v2 = Vertex()
		v3 = Vertex()
		i1 = backend.add_node(v1)
		i2 = backend.add_node(v2)
		i3 = backend.add_node(v3)
		# all indices should be unique
		assert len({i1, i2, i3}) == 3
		assert len(backend.rx) == 3

	#============================================
	def test_add_edge_creates_mapping(self):
		"""Adding an edge should populate e_to_i and i_to_e maps."""
		backend = RxBackend()
		v1 = Vertex()
		v2 = Vertex()
		backend.add_node(v1)
		backend.add_node(v2)
		e = Edge([v1, v2])
		ei = backend.add_edge(v1, v2, e)
		assert backend.e_to_i[e] == ei
		assert backend.i_to_e[ei] is e
		assert len(backend.rx.edge_list()) == 1

	#============================================
	def test_remove_node_cleans_maps(self):
		"""Removing a node should clean up both vertex maps."""
		backend = RxBackend()
		v1 = Vertex()
		v2 = Vertex()
		backend.add_node(v1)
		backend.add_node(v2)
		# remove v1
		backend.remove_node(v1)
		assert v1 not in backend.v_to_i
		# v2 should still be present
		assert v2 in backend.v_to_i
		# i_to_v should no longer contain the removed index
		assert all(v is not v1 for v in backend.i_to_v.values())

	#============================================
	def test_remove_node_cleans_edge_maps(self):
		"""Removing a node should also clean up edges connected to it."""
		backend = RxBackend()
		v1 = Vertex()
		v2 = Vertex()
		backend.add_node(v1)
		backend.add_node(v2)
		e = Edge([v1, v2])
		backend.add_edge(v1, v2, e)
		# remove v1 -- should also remove the edge
		backend.remove_node(v1)
		assert e not in backend.e_to_i
		assert len(backend.i_to_e) == 0

	#============================================
	def test_remove_edge_cleans_maps(self):
		"""Removing an edge should clean up both edge maps."""
		backend = RxBackend()
		v1 = Vertex()
		v2 = Vertex()
		backend.add_node(v1)
		backend.add_node(v2)
		e = Edge([v1, v2])
		ei = backend.add_edge(v1, v2, e)
		# remove edge
		backend.remove_edge(e)
		assert e not in backend.e_to_i
		assert ei not in backend.i_to_e
		# vertices should still be present
		assert v1 in backend.v_to_i
		assert v2 in backend.v_to_i

	#============================================
	def test_remove_nonexistent_node_is_safe(self):
		"""Removing a vertex not in the backend should be a no-op."""
		backend = RxBackend()
		v = Vertex()
		# should not raise
		backend.remove_node(v)

	#============================================
	def test_remove_nonexistent_edge_is_safe(self):
		"""Removing an edge not in the backend should be a no-op."""
		backend = RxBackend()
		e = Edge()
		# should not raise
		backend.remove_edge(e)


#============================================
class TestRxBackendRebuild:
	"""Test rebuild_from_graph using an OASA Graph."""

	#============================================
	def _build_chain4(self) -> tuple:
		"""Build a chain of 4 vertices with 3 edges.

		Returns:
			Tuple of (graph, vertices_list, edges_list).
		"""
		g = Graph()
		verts = [Vertex() for _ in range(4)]
		for v in verts:
			g.add_vertex(v)
		edges = []
		for i in range(3):
			e = g.add_edge(verts[i], verts[i + 1])
			edges.append(e)
		return g, verts, edges

	#============================================
	def test_rebuild_node_count(self):
		"""After rebuild, rx graph should have same node count as OASA."""
		g, verts, edges = self._build_chain4()
		backend = RxBackend()
		backend.rebuild_from_graph(g)
		assert len(backend.rx) == 4

	#============================================
	def test_rebuild_edge_count(self):
		"""After rebuild, rx graph should have same edge count as OASA."""
		g, verts, edges = self._build_chain4()
		backend = RxBackend()
		backend.rebuild_from_graph(g)
		assert len(backend.rx.edge_list()) == 3

	#============================================
	def test_rebuild_vertex_maps_match(self):
		"""After rebuild, all OASA vertices should be in the maps."""
		g, verts, edges = self._build_chain4()
		backend = RxBackend()
		backend.rebuild_from_graph(g)
		for v in verts:
			assert v in backend.v_to_i
			idx = backend.v_to_i[v]
			assert backend.i_to_v[idx] is v

	#============================================
	def test_rebuild_edge_maps_match(self):
		"""After rebuild, all OASA edges should be in the maps."""
		g, verts, edges = self._build_chain4()
		backend = RxBackend()
		backend.rebuild_from_graph(g)
		for e in edges:
			assert e in backend.e_to_i
			ei = backend.e_to_i[e]
			assert backend.i_to_e[ei] is e

	#============================================
	def test_rebuild_clears_dirty(self):
		"""After rebuild, dirty flag should be False."""
		g, verts, edges = self._build_chain4()
		backend = RxBackend()
		assert backend._dirty is True
		backend.rebuild_from_graph(g)
		assert backend._dirty is False


#============================================
class TestRxBackendLazySync:
	"""Test lazy ensure_synced behavior."""

	#============================================
	def test_ensure_synced_rebuilds_when_dirty(self):
		"""ensure_synced should rebuild when dirty=True."""
		g = Graph()
		v = Vertex()
		g.add_vertex(v)
		backend = RxBackend()
		assert backend._dirty is True
		backend.ensure_synced(g)
		assert backend._dirty is False
		assert len(backend.rx) == 1

	#============================================
	def test_ensure_synced_noop_when_clean(self):
		"""ensure_synced should not rebuild when dirty=False."""
		g = Graph()
		v = Vertex()
		g.add_vertex(v)
		backend = RxBackend()
		backend.rebuild_from_graph(g)
		assert backend._dirty is False
		# add another vertex to OASA graph but not backend
		v2 = Vertex()
		g.add_vertex(v2)
		# ensure_synced should NOT see v2 because not dirty
		backend.ensure_synced(g)
		assert len(backend.rx) == 1

	#============================================
	def test_mark_dirty_triggers_rebuild(self):
		"""mark_dirty followed by ensure_synced should rebuild."""
		g = Graph()
		v1 = Vertex()
		g.add_vertex(v1)
		backend = RxBackend()
		backend.rebuild_from_graph(g)
		# add vertex to OASA graph
		v2 = Vertex()
		g.add_vertex(v2)
		# mark dirty so ensure_synced triggers rebuild
		backend.mark_dirty()
		assert backend._dirty is True
		backend.ensure_synced(g)
		assert backend._dirty is False
		# now v2 should appear in the rx graph
		assert len(backend.rx) == 2


#============================================
class TestRxBackendAlgorithms:
	"""Test algorithm delegates using molecule fixtures."""

	#============================================
	def test_connected_components_benzene(self):
		"""Benzene should have exactly 1 connected component."""
		fixture = graph_test_fixtures.make_benzene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		components = backend.get_connected_components(mol)
		assert len(components) == 1
		# the single component should contain all vertices
		assert len(components[0]) == fixture["expected"]["atom_count"]

	#============================================
	def test_connected_components_disconnected(self):
		"""Disconnected graph should have 2 components."""
		fixture = graph_test_fixtures.make_disconnected()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		components = backend.get_connected_components(mol)
		assert len(components) == fixture["expected"]["component_count"]

	#============================================
	def test_is_connected_benzene(self):
		"""Benzene should be connected."""
		fixture = graph_test_fixtures.make_benzene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		assert backend.is_connected(mol) is True

	#============================================
	def test_is_connected_disconnected(self):
		"""Disconnected graph should not be connected."""
		fixture = graph_test_fixtures.make_disconnected()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		assert backend.is_connected(mol) is False

	#============================================
	def test_has_path_hexane_endpoints(self):
		"""Path should exist between first and last vertex of hexane."""
		fixture = graph_test_fixtures.make_hexane()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		v_first = mol.vertices[0]
		v_last = mol.vertices[-1]
		assert backend.has_path(mol, v_first, v_last) is True

	#============================================
	def test_has_path_disconnected_across_components(self):
		"""No path should exist between vertices in different components."""
		fixture = graph_test_fixtures.make_disconnected()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		# vertices 0 and 2 are in different components
		v1 = mol.vertices[0]
		v3 = mol.vertices[2]
		assert backend.has_path(mol, v1, v3) is False

	#============================================
	def test_diameter_benzene(self):
		"""Benzene diameter should be 3."""
		fixture = graph_test_fixtures.make_benzene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		assert backend.get_diameter(mol) == fixture["expected"]["diameter"]

	#============================================
	def test_diameter_hexane(self):
		"""Hexane diameter should be 5."""
		fixture = graph_test_fixtures.make_hexane()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		assert backend.get_diameter(mol) == fixture["expected"]["diameter"]

	#============================================
	def test_diameter_single_atom(self):
		"""Single atom diameter should be 0."""
		fixture = graph_test_fixtures.make_single_atom()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		assert backend.get_diameter(mol) == 0

	#============================================
	def test_cycle_basis_benzene(self):
		"""Benzene should have exactly 1 independent cycle."""
		fixture = graph_test_fixtures.make_benzene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		cycles = backend.cycle_basis(mol)
		assert len(cycles) == fixture["expected"]["cycle_count"]

	#============================================
	def test_cycle_basis_hexane(self):
		"""Hexane (acyclic) should have 0 independent cycles."""
		fixture = graph_test_fixtures.make_hexane()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		cycles = backend.cycle_basis(mol)
		assert len(cycles) == 0

	#============================================
	def test_cycle_basis_naphthalene(self):
		"""Naphthalene should have 2 independent cycles."""
		fixture = graph_test_fixtures.make_naphthalene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		cycles = backend.cycle_basis(mol)
		assert len(cycles) == fixture["expected"]["cycle_count"]

	#============================================
	def test_cycle_basis_returns_oasa_vertices(self):
		"""Cycle basis results should contain OASA Vertex objects."""
		fixture = graph_test_fixtures.make_benzene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		cycles = backend.cycle_basis(mol)
		for cycle in cycles:
			for v in cycle:
				assert v in mol.vertices

	#============================================
	def test_bridges_hexane(self):
		"""All edges in hexane (linear chain) should be bridges."""
		fixture = graph_test_fixtures.make_hexane()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		bridge_set = backend.bridges(mol)
		assert len(bridge_set) == fixture["expected"]["bond_count"]

	#============================================
	def test_bridges_benzene(self):
		"""Benzene (single ring) should have no bridges."""
		fixture = graph_test_fixtures.make_benzene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		bridge_set = backend.bridges(mol)
		assert len(bridge_set) == 0

	#============================================
	def test_bridges_returns_oasa_edges(self):
		"""Bridge results should contain OASA Edge objects."""
		fixture = graph_test_fixtures.make_hexane()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		bridge_set = backend.bridges(mol)
		for e in bridge_set:
			assert e in mol.edges

	#============================================
	def test_distance_from_writes_properties(self):
		"""distance_from should write properties_['d'] on reachable vertices."""
		fixture = graph_test_fixtures.make_hexane()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		start = mol.vertices[0]
		max_d = backend.distance_from(mol, start)
		# max distance in hexane from one end should be 5
		assert max_d == 5
		# check that start vertex has d=0
		assert start.properties_['d'] == 0
		# check that all vertices got a 'd' property
		for v in mol.vertices:
			assert 'd' in v.properties_

	#============================================
	def test_distance_from_single_atom(self):
		"""distance_from on a single atom should return 0."""
		fixture = graph_test_fixtures.make_single_atom()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		start = mol.vertices[0]
		max_d = backend.distance_from(mol, start)
		assert max_d == 0
		assert start.properties_['d'] == 0

	#============================================
	def test_find_path_between_hexane(self):
		"""find_path_between should return a valid path in hexane."""
		fixture = graph_test_fixtures.make_hexane()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		start = mol.vertices[0]
		end = mol.vertices[-1]
		path = backend.find_path_between(mol, start, end)
		assert path is not None
		# path goes from end to start (OASA convention)
		assert path[0] is end
		assert path[-1] is start
		# path should include all 6 vertices for a linear chain
		assert len(path) == len(mol.vertices)

	#============================================
	def test_find_path_between_no_path(self):
		"""find_path_between should return None for disconnected vertices."""
		fixture = graph_test_fixtures.make_disconnected()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		v1 = mol.vertices[0]
		v3 = mol.vertices[2]
		path = backend.find_path_between(mol, v1, v3)
		assert path is None

	#============================================
	def test_find_path_with_dont_go_through(self):
		"""find_path_between with dont_go_through should avoid vertices."""
		fixture = graph_test_fixtures.make_benzene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		# pick start and end that are neighbors
		start = mol.vertices[0]
		end = mol.vertices[3]
		# block one neighbor so path must go the other way around
		blocked = [mol.vertices[1]]
		path = backend.find_path_between(mol, start, end,
										 dont_go_through=blocked)
		assert path is not None
		# blocked vertex should not appear in path
		for v in path:
			assert v is not blocked[0]

	#============================================
	def test_dijkstra_shortest_paths(self):
		"""dijkstra_shortest_paths should return dict of vertex -> path."""
		fixture = graph_test_fixtures.make_hexane()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		source = mol.vertices[0]
		paths = backend.dijkstra_shortest_paths(mol, source)
		# should have a path to every vertex
		for v in mol.vertices:
			assert v in paths
		# path to self should be just [self]
		assert paths[source] == [source]

	#============================================
	def test_algorithms_return_oasa_objects(self):
		"""All algorithm results should contain only OASA objects."""
		fixture = graph_test_fixtures.make_naphthalene()
		mol = fixture["oasa_mol"]
		backend = RxBackend()
		backend.rebuild_from_graph(mol)
		# connected components
		for comp in backend.get_connected_components(mol):
			for v in comp:
				assert isinstance(v, Vertex.__mro__[0]) or v in mol.vertices
		# cycle basis
		for cycle in backend.cycle_basis(mol):
			for v in cycle:
				assert v in mol.vertices


#============================================
class TestRxBackendInvalidation:
	"""Test invalidation and re-sync behavior."""

	#============================================
	def test_invalidate_clears_state(self):
		"""invalidate should clear all maps and set dirty."""
		g = Graph()
		v = Vertex()
		g.add_vertex(v)
		backend = RxBackend()
		backend.rebuild_from_graph(g)
		assert len(backend.rx) == 1
		backend.invalidate()
		assert len(backend.rx) == 0
		assert len(backend.v_to_i) == 0
		assert len(backend.i_to_v) == 0
		assert backend._dirty is True

	#============================================
	def test_invalidate_then_ensure_synced(self):
		"""After invalidation, ensure_synced should rebuild from graph."""
		g = Graph()
		v1 = Vertex()
		g.add_vertex(v1)
		backend = RxBackend()
		backend.rebuild_from_graph(g)
		# add new vertex to OASA graph only
		v2 = Vertex()
		g.add_vertex(v2)
		# invalidate and resync
		backend.invalidate()
		backend.ensure_synced(g)
		# both vertices should now be in rx graph
		assert len(backend.rx) == 2
		assert v1 in backend.v_to_i
		assert v2 in backend.v_to_i
		assert backend._dirty is False

	#============================================
	def test_rebuild_replaces_stale_data(self):
		"""Rebuild should completely replace previous state."""
		# build first graph
		g1 = Graph()
		v1 = Vertex()
		v2 = Vertex()
		g1.add_vertex(v1)
		g1.add_vertex(v2)
		g1.add_edge(v1, v2)
		backend = RxBackend()
		backend.rebuild_from_graph(g1)
		assert len(backend.rx) == 2
		# build second graph
		g2 = Graph()
		v3 = Vertex()
		g2.add_vertex(v3)
		# rebuild with second graph
		backend.rebuild_from_graph(g2)
		assert len(backend.rx) == 1
		assert v3 in backend.v_to_i
		# old vertices should be gone
		assert v1 not in backend.v_to_i
		assert v2 not in backend.v_to_i


#============================================
class TestRxBackendIndexConversion:
	"""Test index conversion helper methods."""

	#============================================
	def test_vertex_to_index_roundtrip(self):
		"""vertex_to_index and index_to_vertex should roundtrip."""
		backend = RxBackend()
		v = Vertex()
		idx = backend.add_node(v)
		assert backend.vertex_to_index(v) == idx
		assert backend.index_to_vertex(idx) is v

	#============================================
	def test_edge_to_index_roundtrip(self):
		"""edge_to_index and index_to_edge should roundtrip."""
		backend = RxBackend()
		v1 = Vertex()
		v2 = Vertex()
		backend.add_node(v1)
		backend.add_node(v2)
		e = Edge([v1, v2])
		ei = backend.add_edge(v1, v2, e)
		assert backend.edge_to_index(e) == ei
		assert backend.index_to_edge(ei) is e
