"""ABC registration for BKChem classes as virtual subclasses of OASA classes.

After the composition refactor, BKChem classes no longer inherit from OASA
classes directly. This module provides ABC interfaces that both OASA and
BKChem classes are registered with, so isinstance checks continue to work
across the codebase.

OASA classes use plain 'type' as their metaclass (not ABCMeta), so we
create thin ABC wrappers and register both OASA originals and BKChem
classes as virtual subclasses.
"""

# Standard Library
import abc

# PIP3 modules
import oasa
import oasa.graph


#============================================
class ChemistryVertex(abc.ABC):
	"""ABC for any chemistry vertex (OASA or BKChem atom/queryatom)."""
	pass


#============================================
class ChemistryEdge(abc.ABC):
	"""ABC for any chemistry edge (OASA or BKChem bond)."""
	pass


#============================================
class ChemistryGraph(abc.ABC):
	"""ABC for any chemistry graph (OASA or BKChem molecule)."""
	pass


#============================================
def register_bkchem_classes() -> None:
	"""Register BKChem and OASA classes as virtual subclasses of the ABCs.

	This must be called once at startup (e.g. from bkchem.__init__) so that
	isinstance(obj, ChemistryVertex) returns True for both OASA and BKChem
	vertex-like objects, even after BKChem classes stop inheriting from OASA.

	Registration mapping:
		ChemistryVertex:
			oasa.graph.Vertex, oasa.ChemVertex, oasa.Atom, oasa.QueryAtom
			bkchem.atom_lib.BkAtom, bkchem.queryatom_lib.BkQueryatom
		ChemistryEdge:
			oasa.graph.Edge, oasa.Bond
			bkchem.bond_lib.BkBond
		ChemistryGraph:
			oasa.graph.Graph, oasa.Molecule
			bkchem.molecule_lib.BkMolecule
	"""
	# late imports to avoid circular dependencies at module level
	import bkchem.atom_lib
	import bkchem.bond_lib
	import bkchem.molecule_lib
	import bkchem.queryatom_lib

	# -- register OASA classes with the ABCs --
	# vertex hierarchy
	ChemistryVertex.register(oasa.graph.Vertex)
	ChemistryVertex.register(oasa.ChemVertex)
	ChemistryVertex.register(oasa.Atom)
	ChemistryVertex.register(oasa.QueryAtom)
	# edge hierarchy
	ChemistryEdge.register(oasa.graph.Edge)
	ChemistryEdge.register(oasa.Bond)
	# graph hierarchy
	ChemistryGraph.register(oasa.graph.Graph)
	ChemistryGraph.register(oasa.Molecule)

	# -- register BKChem classes with the ABCs --
	ChemistryVertex.register(bkchem.atom_lib.BkAtom)
	ChemistryVertex.register(bkchem.queryatom_lib.BkQueryatom)
	ChemistryEdge.register(bkchem.bond_lib.BkBond)
	ChemistryGraph.register(bkchem.molecule_lib.BkMolecule)


#============================================
def is_chemistry_vertex(obj: object) -> bool:
	"""Check if obj is a chemistry vertex (OASA or BKChem).

	Args:
		obj: The object to check.

	Returns:
		True if obj is registered as a ChemistryVertex.
	"""
	return isinstance(obj, ChemistryVertex)


#============================================
def is_chemistry_edge(obj: object) -> bool:
	"""Check if obj is a chemistry edge (OASA or BKChem).

	Args:
		obj: The object to check.

	Returns:
		True if obj is registered as a ChemistryEdge.
	"""
	return isinstance(obj, ChemistryEdge)


#============================================
def is_chemistry_graph(obj: object) -> bool:
	"""Check if obj is a chemistry graph (OASA or BKChem).

	Args:
		obj: The object to check.

	Returns:
		True if obj is registered as a ChemistryGraph.
	"""
	return isinstance(obj, ChemistryGraph)
