"""Rustworkx backend adapter for OASA graph operations.

Provides the RxBackend class that mediates all rustworkx usage for OASA,
maintaining identity maps between OASA Vertex/Edge objects and rustworkx
integer indices. Algorithm delegates return OASA objects, never raw indices.
"""

# PIP3 modules
import rustworkx


#============================================
class RxBackend:
	"""Adapter mediating all rustworkx usage for OASA graph operations.

	Maintains a parallel rustworkx.PyGraph that mirrors an OASA Graph.
	All algorithm results are translated back to OASA Vertex/Edge objects
	so callers never see rustworkx internals.

	Attributes:
		rx: The rustworkx PyGraph instance.
		v_to_i: Dict mapping OASA Vertex -> rustworkx node index.
		i_to_v: Dict mapping rustworkx node index -> OASA Vertex.
		e_to_i: Dict mapping OASA Edge -> rustworkx edge index.
		i_to_e: Dict mapping rustworkx edge index -> OASA Edge.
	"""

	#============================================
	def __init__(self):
		"""Create an empty backend with no nodes or edges."""
		self.rx = rustworkx.PyGraph(multigraph=False)
		self.v_to_i = {}
		self.i_to_v = {}
		self.e_to_i = {}
		self.i_to_e = {}
		self._dirty = True

	#============================================
	def add_node(self, vertex) -> int:
		"""Mirror an OASA vertex addition into the rustworkx graph.

		Args:
			vertex: The OASA Vertex object to add.

		Returns:
			The rustworkx node index assigned to this vertex.
		"""
		# add node with OASA vertex as payload
		idx = self.rx.add_node(vertex)
		self.v_to_i[vertex] = idx
		self.i_to_v[idx] = vertex
		self._dirty = True
		return idx

	#============================================
	def remove_node(self, vertex):
		"""Mirror an OASA vertex removal from the rustworkx graph.

		Removes the node and cleans up all identity maps, including
		any edges that were connected to this vertex.

		Args:
			vertex: The OASA Vertex object to remove.
		"""
		if vertex not in self.v_to_i:
			return
		idx = self.v_to_i[vertex]
		# find and clean up edges connected to this node
		edges_to_remove = []
		for e, ei in list(self.e_to_i.items()):
			# check if this edge connects to the vertex being removed
			verts = e.get_vertices()
			if vertex in verts:
				edges_to_remove.append(e)
		for e in edges_to_remove:
			ei = self.e_to_i.pop(e)
			self.i_to_e.pop(ei, None)
		# remove the node from rustworkx graph
		self.rx.remove_node(idx)
		# clean up vertex maps
		del self.v_to_i[vertex]
		del self.i_to_v[idx]
		self._dirty = True

	#============================================
	def add_edge(self, v1, v2, edge) -> int:
		"""Mirror an OASA edge addition into the rustworkx graph.

		Args:
			v1: First OASA Vertex endpoint.
			v2: Second OASA Vertex endpoint.
			edge: The OASA Edge object to add.

		Returns:
			The rustworkx edge index assigned to this edge.
		"""
		i1 = self.v_to_i[v1]
		i2 = self.v_to_i[v2]
		# add edge with OASA edge as payload
		ei = self.rx.add_edge(i1, i2, edge)
		self.e_to_i[edge] = ei
		self.i_to_e[ei] = edge
		self._dirty = True
		return ei

	#============================================
	def remove_edge(self, edge):
		"""Mirror an OASA edge removal from the rustworkx graph.

		Args:
			edge: The OASA Edge object to remove.
		"""
		if edge not in self.e_to_i:
			return
		ei = self.e_to_i[edge]
		# get endpoint indices for rustworkx removal
		verts = edge.get_vertices()
		i1 = self.v_to_i.get(verts[0])
		i2 = self.v_to_i.get(verts[1])
		if i1 is not None and i2 is not None:
			self.rx.remove_edge(i1, i2)
		# clean up edge maps
		del self.e_to_i[edge]
		self.i_to_e.pop(ei, None)
		self._dirty = True

	#============================================
	def mark_dirty(self):
		"""Mark the backend as needing a rebuild before next algorithm call."""
		self._dirty = True

	#============================================
	def invalidate(self):
		"""Clear all state and mark dirty for a full rebuild."""
		self.rx = rustworkx.PyGraph(multigraph=False)
		self.v_to_i.clear()
		self.i_to_v.clear()
		self.e_to_i.clear()
		self.i_to_e.clear()
		self._dirty = True

	#============================================
	def rebuild_from_graph(self, graph):
		"""Rebuild the entire rustworkx graph from an OASA Graph.

		Clears all existing state and repopulates maps from the graph's
		current vertices and edges lists. Sets dirty=False on completion.

		Args:
			graph: An OASA Graph (or Molecule) instance.
		"""
		# start fresh
		self.rx = rustworkx.PyGraph(multigraph=False)
		self.v_to_i = {}
		self.i_to_v = {}
		self.e_to_i = {}
		self.i_to_e = {}
		# add all vertices as nodes with OASA vertex as payload
		for v in graph.vertices:
			idx = self.rx.add_node(v)
			self.v_to_i[v] = idx
			self.i_to_v[idx] = v
		# add all active edges with OASA edge as payload
		for e in graph.edges:
			verts = e.get_vertices()
			v1, v2 = verts[0], verts[1]
			i1 = self.v_to_i[v1]
			i2 = self.v_to_i[v2]
			ei = self.rx.add_edge(i1, i2, e)
			self.e_to_i[e] = ei
			self.i_to_e[ei] = e
		self._dirty = False

	#============================================
	def ensure_synced(self, graph):
		"""Lazily rebuild the rustworkx graph if dirty.

		Called automatically before any algorithm delegate. If the
		backend is not dirty, this is a no-op.

		Args:
			graph: An OASA Graph (or Molecule) instance.
		"""
		if self._dirty:
			self.rebuild_from_graph(graph)

	# ------------------------------------------------------------------
	# Algorithm delegates
	# Each calls ensure_synced first and returns OASA objects.
	# ------------------------------------------------------------------

	#============================================
	def get_connected_components(self, graph) -> list:
		"""Return connected components as list of sets of OASA Vertex objects.

		Args:
			graph: An OASA Graph instance.

		Returns:
			List of sets, each containing the OASA Vertex objects
			in one connected component.
		"""
		self.ensure_synced(graph)
		# rustworkx returns list of sets of node indices
		rx_components = rustworkx.connected_components(self.rx)
		result = []
		for index_set in rx_components:
			vertex_set = set()
			for idx in index_set:
				vertex_set.add(self.i_to_v[idx])
			result.append(vertex_set)
		return result

	#============================================
	def is_connected(self, graph) -> bool:
		"""Test whether the graph is connected.

		Args:
			graph: An OASA Graph instance.

		Returns:
			True if the graph has exactly one connected component.
		"""
		self.ensure_synced(graph)
		# handle empty graph
		if len(self.rx) == 0:
			return True
		return rustworkx.is_connected(self.rx)

	#============================================
	def has_path(self, graph, v1, v2) -> bool:
		"""Test whether a path exists between two vertices.

		Args:
			graph: An OASA Graph instance.
			v1: Source OASA Vertex.
			v2: Target OASA Vertex.

		Returns:
			True if a path exists from v1 to v2.
		"""
		self.ensure_synced(graph)
		i1 = self.v_to_i[v1]
		i2 = self.v_to_i[v2]
		return rustworkx.has_path(self.rx, i1, i2)

	#============================================
	def get_diameter(self, graph) -> int:
		"""Compute graph diameter (longest shortest path).

		Args:
			graph: An OASA Graph instance.

		Returns:
			Integer diameter of the graph. Returns 0 for single-node
			or empty graphs.
		"""
		self.ensure_synced(graph)
		if len(self.rx) <= 1:
			return 0
		# compute distance matrix and find maximum finite entry
		dist_matrix = rustworkx.distance_matrix(self.rx)
		# dist_matrix is a numpy ndarray; inf means no path
		import numpy
		# replace inf with -1 to find max finite distance
		finite_mask = dist_matrix != numpy.inf
		if not numpy.any(finite_mask):
			return 0
		return int(numpy.max(dist_matrix[finite_mask]))

	#============================================
	def cycle_basis(self, graph) -> list:
		"""Return a set of independent cycles as sets of OASA Vertex objects.

		Args:
			graph: An OASA Graph instance.

		Returns:
			List of sets, each containing the OASA Vertex objects
			forming one independent cycle.
		"""
		self.ensure_synced(graph)
		# rustworkx returns list of lists of node indices
		rx_cycles = rustworkx.cycle_basis(self.rx)
		result = []
		for index_list in rx_cycles:
			vertex_set = set()
			for idx in index_list:
				vertex_set.add(self.i_to_v[idx])
			result.append(vertex_set)
		return result

	#============================================
	def bridges(self, graph) -> set:
		"""Return all bridge edges as a set of OASA Edge objects.

		A bridge is an edge whose removal disconnects the graph.
		Works around a rustworkx bug where bridges() misses edges
		connected to the DFS root node (node 0). We supplement with
		a degree-1 endpoint check for those missed edges.

		Args:
			graph: An OASA Graph instance.

		Returns:
			Set of OASA Edge objects that are bridges.
		"""
		self.ensure_synced(graph)
		# rustworkx.bridges returns set of (u, v) tuples
		rx_bridges = rustworkx.bridges(self.rx)
		result = set()
		for u, v in rx_bridges:
			# find the OASA edge connecting these two vertices
			oasa_v1 = self.i_to_v[u]
			oasa_v2 = self.i_to_v[v]
			edge = self._find_edge_between(oasa_v1, oasa_v2)
			if edge is not None:
				result.add(edge)
		# workaround: rustworkx.bridges() misses edges at degree-1
		# endpoints connected to the DFS root. Check all degree-1
		# nodes -- their single edge is always a bridge.
		for idx in self.rx.node_indices():
			if self.rx.degree(idx) == 1:
				oasa_v = self.i_to_v[idx]
				for e_key, neighbor in oasa_v._neighbors.items():
					if not e_key.disconnected:
						result.add(e_key)
		return result

	#============================================
	def _find_edge_between(self, v1, v2):
		"""Find the OASA Edge connecting two vertices.

		Args:
			v1: First OASA Vertex.
			v2: Second OASA Vertex.

		Returns:
			The OASA Edge object, or None if not found.
		"""
		for e, neighbor in v1._neighbors.items():
			if neighbor == v2 and not e.disconnected:
				return e
		return None

	#============================================
	def distance_from(self, graph, vertex) -> int:
		"""Compute BFS distances from a vertex, writing to properties_['d'].

		Matches the OASA side-effect contract: each reachable vertex gets
		its properties_['d'] set to the BFS distance from the source.
		Unreachable vertices do not get the 'd' key.

		Args:
			graph: An OASA Graph instance.
			vertex: Source OASA Vertex.

		Returns:
			Maximum distance (int) from vertex to any reachable vertex.
		"""
		self.ensure_synced(graph)
		# clean existing distance marks
		for v in graph.vertices:
			v.properties_.pop('d', None)
		src_idx = self.v_to_i[vertex]
		# use dijkstra with unit weights to get BFS distances
		lengths = rustworkx.dijkstra_shortest_path_lengths(
			self.rx, src_idx, lambda _: 1.0
		)
		# lengths is a dict: {node_index: distance}
		max_d = 0
		# set distance on the source vertex itself
		vertex.properties_['d'] = 0
		for idx, dist in lengths.items():
			d = int(dist)
			target_v = self.i_to_v[idx]
			target_v.properties_['d'] = d
			if d > max_d:
				max_d = d
		return max_d

	#============================================
	def find_path_between(self, graph, start, end,
							dont_go_through=None) -> list:
		"""Find a path between two vertices, optionally avoiding some.

		Args:
			graph: An OASA Graph instance.
			start: Source OASA Vertex.
			end: Target OASA Vertex.
			dont_go_through: Optional list of OASA Vertex/Edge objects
				to exclude from the path.

		Returns:
			List of OASA Vertex objects forming the path from end to
			start (matching OASA convention), or None if no path exists.
		"""
		self.ensure_synced(graph)
		# handle trivial case where start and end are the same vertex
		if start is end:
			return [start]
		if dont_go_through:
			# build a filtered subgraph excluding specified vertices/edges
			excluded_vertices = set()
			excluded_edges = set()
			for item in dont_go_through:
				if hasattr(item, '_neighbors'):
					# it's a vertex
					excluded_vertices.add(item)
				else:
					# it's an edge
					excluded_edges.add(item)
			# build a temporary rx graph without excluded items
			temp_rx = rustworkx.PyGraph(multigraph=False)
			temp_v_to_i = {}
			temp_i_to_v = {}
			for v in graph.vertices:
				# don't exclude start or end even if in dont_go_through
				if v in excluded_vertices and v is not start and v is not end:
					continue
				idx = temp_rx.add_node(v)
				temp_v_to_i[v] = idx
				temp_i_to_v[idx] = v
			for e in graph.edges:
				if e in excluded_edges:
					continue
				verts = e.get_vertices()
				v1, v2 = verts[0], verts[1]
				if v1 in temp_v_to_i and v2 in temp_v_to_i:
					temp_rx.add_edge(temp_v_to_i[v1], temp_v_to_i[v2], e)
			# find path in filtered graph
			if start not in temp_v_to_i or end not in temp_v_to_i:
				return None
			i_start = temp_v_to_i[start]
			i_end = temp_v_to_i[end]
			paths = rustworkx.dijkstra_shortest_paths(
				temp_rx, i_start, target=i_end, weight_fn=lambda _: 1.0
			)
			if i_end not in paths:
				return None
			# convert index path to OASA vertices, reversed to match OASA
			path_indices = paths[i_end]
			path_vertices = [temp_i_to_v[i] for i in path_indices]
			path_vertices.reverse()
			return path_vertices
		else:
			# simple path without exclusions
			i_start = self.v_to_i[start]
			i_end = self.v_to_i[end]
			paths = rustworkx.dijkstra_shortest_paths(
				self.rx, i_start, target=i_end, weight_fn=lambda _: 1.0
			)
			if i_end not in paths:
				return None
			path_indices = paths[i_end]
			path_vertices = [self.i_to_v[i] for i in path_indices]
			# reverse to match OASA convention: end -> start
			path_vertices.reverse()
			return path_vertices


	#============================================
	def max_matching(self, graph) -> tuple:
		"""Compute maximum cardinality matching using rustworkx.

		Returns the result in OASA's (mate, nrex) format where mate is a
		dict mapping each vertex to its matched partner (or 0 if exposed)
		and nrex is the count of exposed (unmatched) vertices.

		Args:
			graph: An OASA Graph instance.

		Returns:
			Tuple of (mate_dict, exposed_count).
		"""
		self.ensure_synced(graph)
		# rustworkx returns set of (u, v) index tuples
		rx_matching = rustworkx.max_weight_matching(
			self.rx, max_cardinality=True, default_weight=1
		)
		# convert to OASA mate dict: {vertex: partner_or_0}
		mate = {}.fromkeys(graph.vertices, 0)
		for i1, i2 in rx_matching:
			v1 = self.i_to_v[i1]
			v2 = self.i_to_v[i2]
			mate[v1] = v2
			mate[v2] = v1
		nrex = sum(1 for v in mate.values() if v == 0)
		return mate, nrex

	#============================================
	def cycle_basis_edges(self, graph) -> set:
		"""Return smallest independent cycles as frozensets of OASA Edge objects.

		Computes vertex-based cycle basis via rustworkx, then converts
		each vertex cycle to its corresponding edge subgraph.

		Args:
			graph: An OASA Graph instance.

		Returns:
			Set of frozensets, each containing OASA Edge objects
			forming one independent cycle.
		"""
		vertex_cycles = self.cycle_basis(graph)
		result = set()
		for v_cycle in vertex_cycles:
			edge_set = set()
			for v1 in v_cycle:
				for e, n in v1.get_neighbor_edge_pairs():
					if n in v_cycle:
						edge_set.add(e)
			result.add(frozenset(edge_set))
		return result

	#============================================
	def dijkstra_shortest_paths(self, graph, source, target=None) -> dict:
		"""Compute shortest paths from source to all (or one) target.

		Args:
			graph: An OASA Graph instance.
			source: Source OASA Vertex.
			target: Optional target OASA Vertex to limit search.

		Returns:
			Dict mapping OASA Vertex -> list of OASA Vertex path.
		"""
		self.ensure_synced(graph)
		i_src = self.v_to_i[source]
		if target is not None:
			i_tgt = self.v_to_i[target]
			rx_paths = rustworkx.dijkstra_shortest_paths(
				self.rx, i_src, target=i_tgt, weight_fn=lambda _: 1.0
			)
		else:
			rx_paths = rustworkx.dijkstra_shortest_paths(
				self.rx, i_src, weight_fn=lambda _: 1.0
			)
		# convert index paths to OASA vertex paths
		result = {}
		# include the source vertex with a trivial path to itself
		result[source] = [source]
		for idx, path_indices in rx_paths.items():
			vertex = self.i_to_v[idx]
			path = [self.i_to_v[i] for i in path_indices]
			result[vertex] = path
		return result

	# ------------------------------------------------------------------
	# Index conversion helpers
	# ------------------------------------------------------------------

	#============================================
	def vertex_to_index(self, v) -> int:
		"""Convert an OASA Vertex to its rustworkx node index.

		Args:
			v: An OASA Vertex object.

		Returns:
			The rustworkx integer node index.
		"""
		return self.v_to_i[v]

	#============================================
	def index_to_vertex(self, i):
		"""Convert a rustworkx node index to its OASA Vertex.

		Args:
			i: A rustworkx integer node index.

		Returns:
			The OASA Vertex object.
		"""
		return self.i_to_v[i]

	#============================================
	def edge_to_index(self, e) -> int:
		"""Convert an OASA Edge to its rustworkx edge index.

		Args:
			e: An OASA Edge object.

		Returns:
			The rustworkx integer edge index.
		"""
		return self.e_to_i[e]

	#============================================
	def index_to_edge(self, i):
		"""Convert a rustworkx edge index to its OASA Edge.

		Args:
			i: A rustworkx integer edge index.

		Returns:
			The OASA Edge object.
		"""
		return self.i_to_e[i]
