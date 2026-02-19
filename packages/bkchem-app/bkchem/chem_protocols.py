"""Protocol classes defining the chemistry interface contract.

These Protocol classes define the exact interface that composition wrappers
must satisfy when delegating to OASA chemistry backend objects. They mirror
the public API of oasa.graph.vertex, oasa.graph.edge, oasa.graph.graph,
oasa.chem_vertex, oasa.atom, oasa.bond, and oasa.molecule.
"""

# Standard Library
import typing


#============================================
@typing.runtime_checkable
class ChemVertexProtocol(typing.Protocol):
	"""Protocol for chemistry vertex objects.

	Covers the interface from oasa.graph.vertex, oasa.chem_vertex,
	and oasa.atom. Any object satisfying this protocol can serve as
	a vertex in the chemistry graph.
	"""

	# --- graph.vertex attributes ---
	properties_: dict
	value: typing.Any
	_neighbors: dict

	# --- chem_vertex attributes ---
	charge: int
	x: typing.Optional[float]
	y: typing.Optional[float]
	z: typing.Optional[float]
	multiplicity: int
	valency: int
	free_sites: int

	# --- atom attributes ---
	symbol: str
	symbol_number: int
	isotope: typing.Optional[int]
	explicit_hydrogens: int

	# --- graph.vertex computed properties ---

	@property
	def neighbors(self) -> list:
		"""Return list of neighboring vertices (excluding disconnected edges)."""
		...

	@property
	def degree(self) -> int:
		"""Return the degree of the vertex."""
		...

	@property
	def neighbor_edges(self) -> list:
		"""Return list of active neighboring edges."""
		...

	# --- graph.vertex methods ---

	def add_neighbor(self, v: "ChemVertexProtocol", e: "ChemEdgeProtocol") -> None:
		"""Add a neighbor connected via edge e."""
		...

	def remove_neighbor(self, v: "ChemVertexProtocol") -> None:
		"""Remove a neighbor vertex."""
		...

	def remove_edge_and_neighbor(self, e: "ChemEdgeProtocol") -> None:
		"""Remove an edge and its associated neighbor."""
		...

	def get_neighbor_connected_via(self, e: "ChemEdgeProtocol") -> "ChemVertexProtocol":
		"""Return the neighbor connected via edge e."""
		...

	def get_edge_leading_to(
		self, a: "ChemVertexProtocol"
	) -> typing.Optional["ChemEdgeProtocol"]:
		"""Return the edge connecting self to vertex a, or None."""
		...

	def get_neighbor_edge_pairs(self) -> typing.Iterator:
		"""Yield (edge, vertex) pairs for active neighbors."""
		...

	def get_neighbors_with_distance(self, d: int) -> list:
		"""Return neighbors whose distance property equals d."""
		...

	def copy(self) -> "ChemVertexProtocol":
		"""Return a shallow copy of this vertex."""
		...

	# --- chem_vertex computed properties ---

	@property
	def coords(self) -> tuple:
		"""Return (x, y, z) coordinate tuple."""
		...

	@coords.setter
	def coords(self, coords: tuple) -> None:
		...

	@property
	def occupied_valency(self) -> int:
		"""Return the occupied valency from bond orders."""
		...

	@property
	def free_valency(self) -> int:
		"""Return valency minus occupied valency."""
		...

	@property
	def weight(self) -> float:
		"""Return atomic weight from periodic table."""
		...

	# --- chem_vertex methods ---

	def has_aromatic_bonds(self) -> int:
		"""Return 1 if any neighboring bond is aromatic, else 0."""
		...

	def bond_order_changed(self) -> None:
		"""Called by a bond when its order changes."""
		...

	def get_hydrogen_count(self) -> int:
		"""Return implicit + explicit hydrogen count."""
		...

	def matches(self, other: "ChemVertexProtocol") -> bool:
		"""Return True if this vertex matches other for substructure search."""
		...

	# --- atom methods ---

	def get_formula_dict(self) -> dict:
		"""Return formula as a dictionary."""
		...

	def raise_valency_to_senseful_value(self) -> None:
		"""Set valency to the lowest value giving non-negative free_valency."""
		...

	def raise_valency(self) -> bool:
		"""Try to raise valency to the next higher value. Return success."""
		...

	def get_x(self) -> float:
		"""Return x coordinate, defaulting to 0."""
		...

	def get_y(self) -> float:
		"""Return y coordinate, defaulting to 0."""
		...

	def get_z(self) -> float:
		"""Return z coordinate, defaulting to 0."""
		...


#============================================
@typing.runtime_checkable
class ChemEdgeProtocol(typing.Protocol):
	"""Protocol for chemistry edge (bond) objects.

	Covers the interface from oasa.graph.edge and oasa.bond.
	Any object satisfying this protocol can serve as an edge
	in the chemistry graph.
	"""

	# --- graph.edge attributes ---
	_vertices: list
	properties_: dict
	disconnected: bool

	# --- bond attributes ---
	_order: typing.Optional[int]
	aromatic: typing.Optional[int]
	type: str
	stereochemistry: typing.Any
	line_color: typing.Optional[str]
	wavy_style: typing.Optional[str]
	center: typing.Optional[bool]

	# --- graph.edge properties ---

	@property
	def neighbor_edges(self) -> list:
		"""Return neighbor edges from both endpoint vertices."""
		...

	# --- graph.edge methods ---

	def set_vertices(self, vs: list) -> None:
		"""Set the two vertices this edge connects."""
		...

	def get_vertices(self) -> list:
		"""Return the list of two endpoint vertices."""
		...

	def get_neighbor_edges2(self) -> tuple:
		"""Return two lists of neighbor edges, one per side."""
		...

	def copy(self) -> "ChemEdgeProtocol":
		"""Return a shallow copy of this edge."""
		...

	# --- bond properties ---

	@property
	def vertices(self) -> list:
		"""Return the two vertices as a list."""
		...

	@vertices.setter
	def vertices(self, vs: list) -> None:
		...

	@property
	def order(self) -> int:
		"""Return bond order (1-3 normal, 4 aromatic)."""
		...

	@order.setter
	def order(self, order: int) -> None:
		...

	@property
	def length(self) -> float:
		"""Return bond length from vertex coordinates."""
		...

	# --- bond methods ---

	def matches(self, other: "ChemEdgeProtocol") -> bool:
		"""Return True if bond orders match."""
		...


#============================================
@typing.runtime_checkable
class ChemGraphProtocol(typing.Protocol):
	"""Protocol for chemistry graph (molecule) objects.

	Covers the interface from oasa.graph.graph and oasa.molecule.
	Any object satisfying this protocol can serve as a molecule
	container in the chemistry system.
	"""

	# --- graph attributes ---
	vertices: list
	edges: set
	disconnected_edges: set

	# --- molecule aliases ---
	atoms: list
	bonds: set
	stereochemistry: list

	# --- factory methods ---

	def create_vertex(self, vertex_class: typing.Optional[type] = None) -> ChemVertexProtocol:
		"""Create and return a new vertex (atom)."""
		...

	def create_edge(self) -> ChemEdgeProtocol:
		"""Create and return a new edge (bond)."""
		...

	def create_graph(self) -> "ChemGraphProtocol":
		"""Create and return a new graph (molecule)."""
		...

	# --- graph mutation ---

	def add_vertex(self, v: typing.Optional[ChemVertexProtocol] = None) -> typing.Optional[ChemVertexProtocol]:
		"""Add a vertex to the graph. Return the vertex or None if duplicate."""
		...

	def add_edge(
		self,
		v1: ChemVertexProtocol,
		v2: ChemVertexProtocol,
		e: typing.Optional[ChemEdgeProtocol] = None,
	) -> typing.Optional[ChemEdgeProtocol]:
		"""Add an edge between v1 and v2. Return the edge or None on failure."""
		...

	def delete_vertex(self, v: ChemVertexProtocol) -> None:
		"""Remove a vertex from the vertex list (no edge cleanup)."""
		...

	def remove_vertex(self, v: ChemVertexProtocol) -> None:
		"""Disconnect all edges and remove vertex from the graph."""
		...

	def disconnect(
		self, v1: ChemVertexProtocol, v2: ChemVertexProtocol
	) -> typing.Optional[ChemEdgeProtocol]:
		"""Remove the edge between v1 and v2. Return the edge or None."""
		...

	def disconnect_edge(self, e: ChemEdgeProtocol) -> None:
		"""Remove an edge from the graph."""
		...

	def insert_a_graph(self, gr: "ChemGraphProtocol") -> None:
		"""Insert all vertices and edges from another graph."""
		...

	# --- graph query ---

	def get_edge_between(
		self, v1: ChemVertexProtocol, v2: ChemVertexProtocol
	) -> typing.Optional[ChemEdgeProtocol]:
		"""Return the edge between v1 and v2, or None."""
		...

	def is_connected(self) -> bool:
		"""Return True if the graph is connected."""
		...

	def is_edge_a_bridge(self, e: ChemEdgeProtocol) -> int:
		"""Return 1 if edge is a bridge, else 0."""
		...

	def get_connected_components(self) -> typing.Iterator:
		"""Yield sets of vertices for each connected component."""
		...

	def get_disconnected_subgraphs(self) -> list:
		"""Return list of subgraphs for disconnected components."""
		...

	# --- ring perception ---

	def get_smallest_independent_cycles(self) -> list:
		"""Return list of smallest independent cycles as vertex sets."""
		...

	def get_smallest_independent_cycles_e(self) -> set:
		"""Return set of smallest independent cycles as edge sets."""
		...

	def get_all_cycles(self) -> set:
		"""Return all cycles as frozensets of vertices."""
		...

	def vertex_subgraph_to_edge_subgraph(self, cycle: set) -> set:
		"""Convert a vertex set to the corresponding edge set."""
		...

	def edge_subgraph_to_vertex_subgraph(self, cycle: set) -> set:
		"""Convert an edge set to the corresponding vertex set."""
		...

	# --- copy ---

	def copy(self) -> "ChemGraphProtocol":
		"""Return a shallow copy of the graph."""
		...

	def deep_copy(self) -> "ChemGraphProtocol":
		"""Return a deep copy with new vertex and edge objects."""
		...

	# --- temporary disconnect ---

	def temporarily_disconnect_edge(self, e: ChemEdgeProtocol) -> ChemEdgeProtocol:
		"""Move edge to disconnected set. Return the edge."""
		...

	def reconnect_temporarily_disconnected_edges(self) -> None:
		"""Reconnect all temporarily disconnected edges."""
		...

	# --- molecule-specific ---

	def add_stereochemistry(self, stereo: typing.Any) -> None:
		"""Add a stereochemistry descriptor."""
		...

	def remove_stereochemistry(self, stereo: typing.Any) -> None:
		"""Remove a stereochemistry descriptor."""
		...

	@property
	def weight(self) -> float:
		"""Return molecular weight."""
		...

	@property
	def charge(self) -> int:
		"""Return net molecular charge."""
		...

	def get_formula_dict(self) -> dict:
		"""Return the molecular formula as a dictionary."""
		...

	def mark_vertices_with_distance_from(self, v: ChemVertexProtocol) -> int:
		"""Mark all vertices with distance from v. Return max distance."""
		...

	def find_path_between(
		self,
		start: ChemVertexProtocol,
		end: ChemVertexProtocol,
		dont_go_through: typing.Optional[list] = None,
	) -> typing.Optional[list]:
		"""Find a path between start and end vertices."""
		...
