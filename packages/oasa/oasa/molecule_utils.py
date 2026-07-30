#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Helpers for molecule graph manipulation."""


#============================================
def merge_molecules(molecules: object) -> object:
	"""Merge molecules into one disconnected graph."""
	if not molecules:
		return None
	if len(molecules) == 1:
		return molecules[0]
	first = molecules[0]
	merged = first.create_graph() if hasattr(first, "create_graph") else type(first)()
	for part in molecules:
		vertex_map = {}
		for original_vertex in part.vertices:
			copied_vertex = original_vertex.copy()
			merged.add_vertex(copied_vertex)
			vertex_map[original_vertex] = copied_vertex
		for original_edge in part.edges:
			copied_edge = original_edge.copy()
			vertex_1, vertex_2 = original_edge.vertices
			merged.add_edge(vertex_map[vertex_1], vertex_map[vertex_2], copied_edge)
	return merged
