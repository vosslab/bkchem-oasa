"""GraphVertexMixin - replicate oasa.graph.vertex interface as a BKChem mixin.

This mixin provides the graph connectivity interface that BKChem vertex
classes need after removing oasa.graph.vertex from their MRO. It replicates
the exact API of oasa.graph.vertex so that graph algorithms continue to work.
"""

# Standard Library
import copy


#============================================
class GraphVertexMixin:
	"""Mixin providing oasa.graph.vertex interface for BKChem vertices.

	Replicates: _neighbors dict, properties_ dict, value attribute,
	neighbors property, degree property, neighbor_edges property,
	add_neighbor(), remove_neighbor(), remove_edge_and_neighbor(),
	get_edge_leading_to(), get_neighbor_edge_pairs(),
	get_neighbor_connected_via(), get_neighbors_with_distance(),
	copy(), _clean_cache().
	"""

	attrs_to_copy: tuple[str, ...] = ("value",)

	#============================================
	def __init__(self):
		"""Initialize vertex state: properties, value, neighbors, and cache."""
		self.properties_ = {}
		self.value = None
		self._neighbors = {}
		self._clean_cache()

	#============================================
	def __str__(self) -> str:
		"""Return string representation showing value, degree, and properties."""
		return ("vertex, value=%s, degree=%d, " % (str(self.value), self.degree)) + str(self.properties_)

	#============================================
	def _clean_cache(self) -> None:
		"""Reset the internal cache dict."""
		self._cache = {}

	#============================================
	def copy(self):
		"""Create a shallow copy of this vertex, copying attrs_to_copy fields.

		Returns:
			A new instance of the same class with copied attributes.
		"""
		other = self.__class__()
		for attr in self.attrs_to_copy:
			setattr(other, attr, copy.copy(getattr(self, attr)))
		return other

	#============================================
	def add_neighbor(self, v, e) -> None:
		"""Add a neighbor connected via edge e.

		Args:
			v: The neighboring vertex to add.
			e: The edge connecting this vertex to v.
		"""
		self._clean_cache()
		self._neighbors[e] = v

	#============================================
	def remove_neighbor(self, v) -> None:
		"""Remove neighbor v and the edge connecting to it.

		Args:
			v: The neighboring vertex to remove.

		Raises:
			Exception: If v is not a current neighbor.
		"""
		self._clean_cache()
		to_del = None
		for k, vv in list(self._neighbors.items()):
			if v == vv:
				to_del = k
				break
		if to_del:
			del self._neighbors[to_del]
		else:
			raise Exception("Cannot remove non-existing neighbor")

	#============================================
	def remove_edge_and_neighbor(self, e) -> None:
		"""Remove edge e and its associated neighbor.

		Args:
			e: The edge to remove.

		Raises:
			Exception: If e is not a current edge.
		"""
		self._clean_cache()
		if e in list(self._neighbors.keys()):
			del self._neighbors[e]
		else:
			raise Exception("Cannot remove non-existing edge", e)

	#============================================
	@property
	def neighbors(self) -> list:
		"""Return list of neighboring vertices excluding disconnected edges."""
		return [v for (e, v) in list(self._neighbors.items())
				if not e.disconnected]

	#============================================
	def get_neighbor_connected_via(self, e):
		"""Return the neighbor connected via edge e.

		Args:
			e: The edge to look up.

		Returns:
			The vertex connected via edge e.
		"""
		return self._neighbors[e]

	#============================================
	def get_edge_leading_to(self, a):
		"""Return the edge leading to vertex a, or None.

		Args:
			a: The target vertex.

		Returns:
			The edge connecting to vertex a, or None if not found.
		"""
		for b, at in list(self._neighbors.items()):
			if a == at:
				return b
		return None

	#============================================
	@property
	def degree(self) -> int:
		"""Return the degree of this vertex (number of active neighbors)."""
		return len(self.neighbors)

	#============================================
	def get_neighbors_with_distance(self, d) -> list:
		"""Return neighbors whose properties_ dict has 'd' equal to d.

		Args:
			d: The distance value to filter by.

		Returns:
			List of neighboring vertices with matching distance property.
		"""
		ret = []
		for v in self.neighbors:
			if 'd' in v.properties_ and v.properties_['d'] == d:
				ret.append(v)
		return ret

	#============================================
	def get_neighbor_edge_pairs(self):
		"""Yield (edge, vertex) pairs for all active connections."""
		for e, v in list(self._neighbors.items()):
			if not e.disconnected:
				yield e, v

	#============================================
	@property
	def neighbor_edges(self) -> list:
		"""Return list of active neighboring edges."""
		return [e for e in list(self._neighbors.keys())
				if not e.disconnected]
