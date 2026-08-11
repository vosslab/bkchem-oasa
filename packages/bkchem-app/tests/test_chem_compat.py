"""Behavioral checks for classic frontend chemistry-role classification."""

# local repo modules
import bkchem.chem_compat
import bkchem.group_lib
import bkchem.textatom_lib


#============================================
def test_composed_vertex_projections_need_no_backend_class_registration() -> None:
	"""Every projected atom role is selectable as a vertex before app startup."""
	projected_vertices = (
		object.__new__(bkchem.group_lib.BkGroup),
		object.__new__(bkchem.textatom_lib.BkTextatom),
	)
	for vertex in projected_vertices:
		assert bkchem.chem_compat.is_chemistry_vertex(vertex)
		assert not bkchem.chem_compat.is_chemistry_edge(vertex)
		assert not bkchem.chem_compat.is_chemistry_graph(vertex)
