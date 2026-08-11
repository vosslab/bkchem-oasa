"""Classify chemistry objects through the classic frontend's public roles.

BKChem scene projections expose ``object_type`` so heterogeneous paper items
can be classified without inspecting OASA implementation classes.  Keeping the
role check here gives the legacy callers one stable interface while preserving
composition at the backend/frontend boundary.
"""


_VERTEX_ROLE = "atom"
_EDGE_ROLE = "bond"
_GRAPH_ROLE = "molecule"


#============================================
def is_chemistry_vertex(obj: object) -> bool:
	"""Return whether a projected frontend object has the vertex role."""
	return getattr(obj, "object_type", None) == _VERTEX_ROLE


#============================================
def is_chemistry_edge(obj: object) -> bool:
	"""Return whether a projected frontend object has the edge role."""
	return getattr(obj, "object_type", None) == _EDGE_ROLE


#============================================
def is_chemistry_graph(obj: object) -> bool:
	"""Return whether a projected frontend object has the graph role."""
	return getattr(obj, "object_type", None) == _GRAPH_ROLE
