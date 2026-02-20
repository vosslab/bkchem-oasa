#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program

#--------------------------------------------------------------------------

"""Minimalistic graph implementation.

Suitable for analysis of chemical problems.
"""



import copy
import warnings

from oasa.graph.edge_lib import Edge
from oasa.graph.vertex_lib import Vertex
from oasa.graph.rx_backend import RxBackend



class Graph(object):
  """Provide a minimalistic graph implementation.

  Suitable for analysis of chemical problems,
  even if some care was taken to make the graph work with nonsimple graphs,
  there are cases where it won't!
  """
  uses_cache = True


  def __init__( self, vertices = []):
    if vertices:
      self.vertices = vertices
    else:
      self.vertices = []
    self.edges = set()
    self.disconnected_edges = set()
    self._cache = {}
    # rustworkx backend for accelerated graph algorithms
    self._rx_backend = RxBackend()


  def __str__( self):
    str = "graph G(V,E), |V|=%d, |E|=%d" % ( len( self.vertices), len( self.edges))
    return str


  def copy( self):
    """provides a really shallow copy, the vertex and edge objects will remain the same,
    only the graph itself is different"""
    c = self.create_graph()
    c.vertices = copy.copy( self.vertices)
    for e in self.edges:
      i, j = e.get_vertices()
      c.add_edge( i, j, e)
    return c


  def deep_copy( self):
    """provides a deep copy of the graph. The result is an isomorphic graph,
    all the used objects are different"""
    c = self.create_graph()
    for v in self.vertices:
      new = v.copy()
      c.add_vertex( new)
    for e in self.edges:
      v1, v2 = e.get_vertices()
      i1 = self.vertices.index( v1)
      i2 = self.vertices.index( v2)
      new_e = e.copy()
      c.add_edge( c.vertices[i1], c.vertices[i2], new_e)
    return c


  def create_vertex( self):
    return Vertex()


  def create_edge( self):
    return Edge()


  def create_graph( self):
    return self.__class__()


  def delete_vertex( self, v):
    self.vertices.remove( v)
    self._flush_cache()


  def add_vertex( self, v=None):
    """adds a vertex to a graph, if v argument is not given creates a new one.
    returns None if vertex is already present or the vertex instance if successful"""
    if not v:
      v = self.create_vertex()
    if v not in self.vertices:
      self.vertices.append( v)
    else:
      warnings.warn( "Added vertex is already present in graph %s" % str( v), UserWarning, 2)
      return None
    self._flush_cache()
    return v


  def add_edge( self, v1, v2, e=None):
    """adds an edge to a graph connecting vertices v1 and v2, if e argument is not given creates a new one.
    returns None if operation fails or the edge instance if successful"""
    i1 = self._get_vertex_index( v1)
    i2 = self._get_vertex_index( v2)
    if i1 is None or i2 is None:
      warnings.warn( "Adding edge to a vertex not present in graph failed (of course)", UserWarning, 3)
      return None
    # to get the vertices if v1 and v2 were indexes
    v1 = self.vertices[ i1]
    v2 = self.vertices[ i2]
    if not e:
      e = self.create_edge()
    e.set_vertices( (v1,v2))
    self.edges.add( e)
    v1.add_neighbor( v2, e)
    v2.add_neighbor( v1, e)
    self._flush_cache()
    return e


  def insert_a_graph( self, gr):
    """inserts all edges and vertices to the graph"""
    self.vertices.extend( gr.vertices)
    self.edges.update( gr.edges)
    self._flush_cache()


  def disconnect( self, v1, v2):
    """disconnects vertices v1 and v2, on success returns the edge"""
    if v1 is not None and v2 is not None:
      e = self.get_edge_between( v1, v2)
      if e:
        self.edges.remove( e)
        v1.remove_neighbor( v2)
        v2.remove_neighbor( v1)
      self._flush_cache()
      return e
    else:
      return None


  def disconnect_edge( self, e):
    self.edges.remove( e)
    v1, v2 = e.get_vertices()
    v1.remove_edge_and_neighbor( e)
    if v1 is not v2:
      v2.remove_edge_and_neighbor( e)
    self._flush_cache()


  def remove_vertex( self, v):
    for neigh in v.neighbors:
      self.disconnect( v, neigh)
    self.delete_vertex( v)


  def get_edge_between( self, v1, v2):
    """takes two vertices"""
    for e in v1.neighbor_edges:
      if e in v2.neighbor_edges:
        return e
    return None


  def temporarily_disconnect_edge( self, e):
    self.edges.remove( e)
    self.disconnected_edges.add( e)
    e.disconnected = True
    self._flush_cache()
    return e


  def reconnect_temporarily_disconnected_edge( self, e):
    assert e in self.disconnected_edges
    self.disconnected_edges.remove( e)
    self.edges.add( e)
    e.disconnected = False
    self._flush_cache()


  def reconnect_temporarily_disconnected_edges( self):
    while self.disconnected_edges:
      e = self.disconnected_edges.pop()
      e.disconnected = False
      self.edges.add( e)
    self._flush_cache()


  ## PROPERTIES METHODS
  ## BOOLEAN

  def is_connected( self):
    """Test whether the graph is connected using rustworkx (13x faster)."""
    return self._rx_backend.is_connected(self)


  def is_tree( self):
    if self.is_connected():
      return len( self.vertices)-1 == len( self.edges)
    else:
      return len( self.vertices)-len( list( self.get_connected_components())) == len( self.edges)


  def contains_cycle( self):
    """this assumes that the graph is connected"""
    return not self.is_tree()


  def is_edge_a_bridge( self, e):
    """Test whether an edge is a bridge using rustworkx bridges detection."""
    # compute all bridges at once, then check membership
    bridge_edges = self._rx_backend.bridges(self)
    if e in bridge_edges:
      return 1
    return 0


  def is_edge_a_bridge_fast_and_dangerous( self, e):
    """should be used only in case of repetitive questions for the same edge in cases
    where no edges are added to the graph between the questions (if brigde==1 the value
    is stored and returned, which is safe only in case no edges are added)"""
    try:
      return e.properties_['bridge']
    except:
      if self.is_edge_a_bridge( e):
        e.properties_['bridge'] = 1
        return 1
      else:
        return 0


  def get_pieces_after_edge_removal( self, e):
    self.temporarily_disconnect_edge( e)
    ps = [i for i in self.get_connected_components()]
    self.reconnect_temporarily_disconnected_edge( e)
    return ps


  ## ANALYSIS
  def get_connected_components( self):
    """Return connected components as list of sets of vertices.

    Uses rustworkx connected_components for performance (9x faster).
    """
    return self._rx_backend.get_connected_components(self)


  def get_disconnected_subgraphs( self):
    """returns the subgraphs of self, it is dangerous as it reuses the original vertices and
    edges, therefore it should be used only when the old self is no longer needed."""
    vss = self.get_connected_components()
    out = []
    for vs in vss:
      out.append( self.get_induced_subgraph_from_vertices( vs))
    return out


  def get_induced_subgraph_from_vertices( self, vs):
    """it creates a new graph, however uses the old vertices and edges!"""
    g = self.create_graph()
    for v in vs:
      g.add_vertex( v)
    for e in self.vertex_subgraph_to_edge_subgraph( vs):
      v1, v2 = e.get_vertices()
      if v1 in vs and v2 in vs:
        g.add_edge( v1, v2, e)  # BUG - it should copy the edge?
    return g


  def get_induced_copy_subgraph_from_vertices_and_edges( self, vertices, edges, add_back_links=False):
    """it creates a new graph, populates it with copies of vertices and edges;
    it only uses the vertices and edges that are supplied as argument;
    add_back_links - add x.properties_['original'] link to the original edges and vertices
    """
    c = self.create_graph()
    old_v_to_new_v = {}
    for v in vertices:
      new = v.copy()
      c.add_vertex( new)
      old_v_to_new_v[v] = new
      if add_back_links:
        new.properties_['original'] = v
    for e in edges:
      v1, v2 = e.get_vertices()
      if (v1 in old_v_to_new_v) and (v2 in old_v_to_new_v):
        # exclude edges to not-copied vertices (this prevents programmers errors and adds the possibility
        # to replace edges in this call by all edges)
        new_e = e.copy()
        if add_back_links:
          new_e.properties_['original'] = e
        c.add_edge( old_v_to_new_v[v1], old_v_to_new_v[v2], new_e)
    return c


  def get_smallest_independent_cycles( self):
    """Return list of sets of vertices forming smallest independent cycles.

    Uses rustworkx cycle_basis for performance (215x faster than pure Python).
    """
    return self._rx_backend.cycle_basis(self)


  def get_smallest_independent_cycles_dangerous_and_cached( self):
    try:
      return self._cache['cycles']
    except KeyError:
      self._cache['cycles'] = self.get_smallest_independent_cycles()
      return self._cache['cycles']



  def get_smallest_independent_cycles_e( self):
    """Return smallest independent cycles as frozensets of edges.

    Uses rustworkx cycle_basis (vertex version) and converts each
    vertex cycle to its edge subgraph. Much simpler and faster than
    the legacy BFS-based approach.
    """
    return self._rx_backend.cycle_basis_edges(self)


  def get_all_cycles_e( self):
    return list(map( self.vertex_subgraph_to_edge_subgraph, self.get_all_cycles()))


  def get_all_cycles( self):
    """
    implementation of:
    A New Algorithm for Exhaustive Ring Perception in a Molecular Graph
    Th. Hanser, Ph. Jauffret, and G. Kaufmann
    J. Chem. Inf. Comput. Sci., 1996, 36 (6), 1146-1152 . DOI: 10.1021/ci960322f
    """
    pgraph = self._get_p_graph()
    rings = set()
    for pv in copy.copy( pgraph.vertices):
      rings |= Graph._p_graph_remove( pv, pgraph)
    final_rings = set()
    for ring in rings:
      final_ring = frozenset( [v.properties_['original'] for v in ring])
      final_rings.add( final_ring)
    return final_rings


  def _get_p_graph( self):
    """helper method for p-graph (path graph) generation"""
    p = self.deep_copy()
    p.temporarily_strip_bridge_edges()
    # we count on order of vertices remaining the same
    for i,v in enumerate( self.vertices):
      p.vertices[i].properties_['original'] = v
    for e in p.edges:
      e.path_ = set( e.vertices)
    to_remove = [v for v in p.vertices if not v.neighbors]
    for v in to_remove:
      p.delete_vertex( v)
    return p


  @staticmethod
  def _p_graph_remove( v, pgraph):
    rings = set()
    neighbor_edge_vertex_pairs = list( v.get_neighbor_edge_pairs())
    new_edges = []
    for i,(ne1,nv1) in enumerate( neighbor_edge_vertex_pairs):
      for ne2,nv2 in neighbor_edge_vertex_pairs[i+1:]:
        if (nv1 is nv2 and (ne1.path_ & ne2.path_ == set( [v,nv2]))) or (ne1.path_ & ne2.path_ == set( [v])):
          new_path = ne1.path_ | ne2.path_
          new_edge = pgraph.create_edge()
          new_edge.path_ = new_path
          pgraph.add_edge( nv1, nv2, new_edge)
          new_edges.append( new_edge)
    for ne,nv in neighbor_edge_vertex_pairs:
      pgraph.disconnect_edge( ne)
    for e in new_edges:
      end1, end2 = e.vertices
      if end1 is end2:
        # we have a loop here
        rings.add( frozenset( e.path_))
        pgraph.disconnect_edge( e)
    pgraph.remove_vertex( v)
    return rings


  def mark_vertices_with_distance_from( self, v):
    """Mark all reachable vertices with BFS distance from v (2x faster).

    Side effect: sets v.properties_['d'] on each reachable vertex.

    Returns:
      Maximum distance (int) from v to any reachable vertex.
    """
    return self._rx_backend.distance_from(self, v)


  def clean_distance_from_vertices( self):
    for i in self.vertices:
      try:
        del i.properties_['d']
      except KeyError:
        pass


  def mark_edges_with_distance_from( self, e1):
    for e in self.edges:
      try:
        del e.properties_['d']
      except KeyError:
        pass
    marked = set( [e1])
    new = set( [e1])
    dist = 0
    e1.properties_['dist'] = dist
    while new:
      new_new = set()
      dist += 1
      for e in new:
        for ne in e.neighbor_edges:
          if not ne in marked:
            ne.properties_['dist'] = dist
            new_new.add( ne)
      new = new_new
      marked.update( new)


  def get_path_between_edges( self, e1, e2):
    self.mark_edges_with_distance_from( e1)
    if not "dist" in e2.properties_:
      return None
    else:
      path = [e2]
      _e = e2
      for i in range( e2.properties_['dist']-1, -1, -1):
        _e = [ee for ee in _e.neighbor_edges if ee.properties_['dist'] == i][0]
        path.append( _e)
      return path



  def get_diameter( self):
    """Return graph diameter using rustworkx distance matrix.

    Caches the result for repeated queries on unchanged graphs.
    """
    d = self._get_cache( "diameter")
    if d is not None:
      return d
    # delegate to rustworkx backend (49x faster than pure Python)
    result = self._rx_backend.get_diameter(self)
    self._set_cache( "diameter", result)
    return result


  def vertex_subgraph_to_edge_subgraph( self, cycle):
    ret = set()
    for v1 in cycle:
      for (e,n) in v1.get_neighbor_edge_pairs():
        if n in cycle:
          ret.add( e)
    return ret


  def edge_subgraph_to_vertex_subgraph( self, cycle):
    ret = set()
    for e in cycle:
      v1, v2 = e.get_vertices()
      ret.add( v1)
      ret.add( v2)
    return ret


  def get_new_induced_subgraph( self, vertices, edges):
    """returns a induced subgraph that is newly created and can be therefore freely
    changed without worry about the original."""
    sub = self.create_graph()
    vertex_map = {}
    i = 0
    for v in vertices:
      new_v = v.copy()
      sub.add_vertex( new_v)
      vertex_map[v] = i
      i += 1
    for e in edges:
      new_e = e.copy()
      v1, v2 = e.get_vertices()
      sub.add_edge( vertex_map[v1], vertex_map[v2], new_e)
    return sub


  def defines_connected_subgraph_e( self, edges):
    sub = self.get_new_induced_subgraph( self.edge_subgraph_to_vertex_subgraph( edges), edges)
    return sub.is_connected()


  def defines_connected_subgraph_v( self, vertices):
    sub = self.get_new_induced_subgraph( vertices, self.vertex_subgraph_to_edge_subgraph( vertices))
    return sub.is_connected()


  def find_path_between( self, start, end, dont_go_through=[]):
    """Find path between two vertices using rustworkx (7x faster).

    Args:
      start: Source vertex.
      end: Target vertex.
      dont_go_through: Optional list of vertices/edges to avoid.

    Returns:
      List of vertices from end to start, or None if no path exists.
    """
    if dont_go_through is None:
      dont_go_through = []
    return self._rx_backend.find_path_between(
      self, start, end, dont_go_through=dont_go_through
    )


  def sort_vertices_in_path( self, path, start_from=None):
    """returns None if there is no path"""
    rng = copy.copy( path)
    if start_from:
      a = start_from
      rng.remove( a)
    else:
      a = None
      # for acyclic path we need to find one end
      for at in path:
        if len([v for v in at.neighbors if v in path]) == 1:
          a = at
          rng.remove( at)
          break
      if not a:
        a = rng.pop() # for rings
    out = [a]
    while rng:
      try:
        a = [i for i in a.neighbors if i in rng][0]
      except IndexError:
        return None
      out.append( a)
      rng.remove( a)
    return out


  def temporarily_strip_bridge_edges( self):
    """strip all edges that are a bridge, thus leaving only the cycles connected"""
    bridge_found = True
    while bridge_found:
      vs = [v for v in self.vertices if v.degree == 1]
      while vs:
        for v in vs:
          # we have to ask the degree, because the bond might have been stripped in this run
          if v.degree:
            e = v.neighbor_edges[0]
            self.temporarily_disconnect_edge( e)
        vs = [v for v in self.vertices if v.degree == 1]
      bridge_found = False
      for e in self.edges:
        if self.is_edge_a_bridge( e):
          bridge_found = True
          break
      if bridge_found:
        self.temporarily_disconnect_edge( e)


  def path_exists( self, a1, a2):
    """Test whether a path exists between two vertices (5x faster)."""
    return self._rx_backend.has_path(self, a1, a2)


  ## MAXIMUM MATCHING RELATED STUFF
  ## MAXIMUM MATCHING
  def get_maximum_matching( self):
    """Return maximum cardinality matching using rustworkx.

    Returns:
      Tuple of (mate, nrex) where mate maps each vertex to its
      matched partner (or 0 if exposed) and nrex is the count
      of exposed vertices.
    """
    return self._rx_backend.max_matching(self)


  # PRIVATE METHODS
  def _get_vertex_index( self, v):
    """if v is already an index, return v, otherwise return index of v on None"""
    if isinstance(v, int) and v < len(self.vertices):
      return v
    try:
      return self.vertices.index( v)
    except ValueError:
      return None


  def _flush_cache( self):
    self._cache = {}
    # invalidate rustworkx backend so it rebuilds before next algorithm call
    self._rx_backend.mark_dirty()


  def _set_cache( self, name, value):
    if self.uses_cache:
      self._cache[ name] = value


  def _get_cache( self, name):
    return self._cache.get( name, None)



