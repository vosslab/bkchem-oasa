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

import copy
import math
import cairo

from oasa import atom_colors
from oasa import geometry
from oasa import oasa_utils as misc
from oasa import render_ops
from oasa.render_lib.data_types import BondRenderContext
from oasa.render_lib.data_types import make_attach_constraints
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.bond_ops import build_bond_ops
from oasa import safe_xml
from oasa import transform3d_lib as transform3d



class cairo_out(object):
  """Draw OASA molecules using cairo.

  Cairo supports different 'surfaces' which represent different file formats.
  This object implements PNG file drawing, but should be general enough
  to work with other formats, provided modified version of create_surface and
  write_surface methods are provided when this class is subclassed.

  Usage:

  c = cairo_out( scaling=2.0, margin=10, font_size=20, bond_width=6)
  c.show_hydrogens_on_hetero = True
  c.mol_to_cairo( mol, 'outfile.png') # mol is oasa molecule

  # attributes can be set in constructor or afterwards as normal attributes
  # default options are set and described in the cairo_out.default_options dictionary
  """

  _temp_margin = 200

  atom_colors_minimal = atom_colors.atom_colors_minimal
  atom_colors_full = atom_colors.atom_colors_full

  # all the following values are settable using the constructor, e.g.
  # cairo_out( margin=20, bond_width=3.0)
  # all metrics is scaled properly, the values corespond to pixels only
  # when scaling is 1.0
  default_options = {
    'scaling': 2.0,
    # target DPI for PNG output when scaling is not explicitly set
    'dpi': 600,
    # target PNG width in pixels when scaling is not explicitly set (set to None to disable)
    'target_width_px': 1500,
    # should atom coordinates be rounded to whole pixels before rendering?
    # This improves image sharpness but might slightly change the geometry
    'align_coords': True,
    # the following also draws hydrogens on shown carbons
    'show_hydrogens_on_hetero': False,
    'show_carbon_symbol': False,
    'margin': 15,
    'line_width': 1.0,
    'bold_line_width_multiplier': 1.2,
    # how far second bond is drawn
    'bond_width': 6.0,
    'wedge_width': 6.0,
    'font_name': "Arial",
    'font_size': 16,
    'font_weight': "bold",
    # background color in RGBA
    'background_color': (1,1,1,1),
    'color_atoms': True,
    'color_bonds': True,
    'space_around_atom': 2,
    # you can choose between atom_colors_full, atom_colors_minimal
    # or provide a custom dictionary
    'atom_colors': atom_colors_full,
    # proportion between subscript and normal letters size
    'subscript_size_ratio': 0.8,
    # how much to shorten second line of double and triple bonds (0-0.5)
    'bond_second_line_shortening': 0.15,
    # the following two are just for playing
    # - without antialiasing the output is ugly
    'antialias_text': True,
    'antialias_drawing': True,
    # this will only change appearance of overlapping text
    'add_background_to_text': False,
    # should text be converted to curves?
    'text_to_curves': False,
    }


  def __init__( self, **kw):
    self._scaling_overridden = False
    for k, v in list(self.__class__.default_options.items()):
      setattr( self, k, v)
    # list of paths that contribute to the bounding box (probably no edges)
    self._vertex_to_bbox = {} # vertex-to-bbox mapping
    self._bboxes = [] # for overall bbox calcualtion
    for k,v in list(kw.items()):
      if k in self.__class__.default_options:
        setattr( self, k, v)
        if k == 'scaling':
          self._scaling_overridden = True
      else:
        raise Exception( "unknown attribute '%s' passed to constructor" % k)


  def draw_mol( self, mol):
    if not self.surface:
      raise Exception( "You must initialize cairo surface before drawing, use 'create_surface' to do it.")
    self.molecule = mol
    for v in mol.vertices:
      self._draw_vertex( v)
    self._shown_vertices = set( self._vertex_to_bbox.keys())
    for e in copy.copy( mol.edges):
      self._draw_edge( e)


  def create_surface( self, w, h, format):
    """currently implements PNG writting, but might be overriden to write other types;
    w and h are minimal estimated width and height"""
    # trick - we use bigger surface and then copy from it to a new surface and crop
    if format == "png":
      self.surface = cairo.ImageSurface( cairo.FORMAT_ARGB32, w, h)
    elif format == "pdf":
      self.surface = cairo.PDFSurface( self.filename, w, h)
    elif format == "svg":
      self.surface = cairo.SVGSurface( self.filename, w, h)
    else:
      raise Exception( "unknown format '%s'" % format)


  def init_surface( self):
    """make all necessary operations to prepare a surface for drawing:
    set antialiasing as requested, create background, etc."""
    pass


  def create_dummy_surface( self, w, h):
    self.surface = cairo.ImageSurface( cairo.FORMAT_A1, w, h)


  def write_surface( self):
    """finishes the surface and write it to the file if necessary"""
    self.context.show_page()
    if isinstance( self.surface, cairo.ImageSurface):
      self.surface.write_to_png( self.filename)
    self.surface.finish()


  def mols_to_cairo( self, mols, filename, format="png"):
    x1, y1, x2, y2 = None, None, None, None
    for mol in mols:
      for v in mol.vertices:
        v.y = -v.y # flip coords - molfiles have them the other way around
        if self.align_coords:
          v.x = self._round( v.x)
          v.y = self._round( v.y)
        if x1 == None or x1 > v.x:
          x1 = v.x
        if x2 == None or x2 < v.x:
          x2 = v.x
        if y1 == None or y1 > v.y:
          y1 = v.y
        if y2 == None or y2 < v.y:
          y2 = v.y
    w = int( x2 - x1)
    h = int( y2 - y1)
    self._bboxes.append( (x1,y1,x2,y2))

    # dummy surface to get complete size of the drawing
    # Because it is not possible to calculate the bounding box of a drawing before its drawn (mainly
    # because we don't know the size of text items), this object internally draws to a surface with
    # large margins to get the bbox
    _w = int( self.scaling*w+2*self.scaling*self._temp_margin)
    _h = int( self.scaling*h+2*self.scaling*self._temp_margin)
    self.create_dummy_surface( _w, _h)
    self.context = cairo.Context( self.surface)
    [self.draw_mol( mol) for mol in mols]
    x1, y1, x2, y2 = self._get_bbox()
    x1, y1 = self.context.user_to_device( x1, y1)
    x2, y2 = self.context.user_to_device( x2, y2)
    if format == "png" and not self._scaling_overridden:
      base_width = (x2 - x1) + 2 * self.margin
      if self.target_width_px:
        if self.target_width_px <= 0:
          raise ValueError( "target_width_px must be > 0")
        if base_width:
          self.scaling = float( self.target_width_px) / float( base_width)
      elif self.dpi:
        if self.dpi <= 0:
          raise ValueError( "dpi must be > 0")
        self.scaling = float( self.dpi) / 72.0
    width = int( self.scaling*(x2-x1) + 2*self.margin*self.scaling)
    height = int( self.scaling*(y2-y1) + 2*self.margin*self.scaling)

    # now paint for real
    self.filename = filename
    self.create_surface( width, height, format)
    self.context = cairo.Context( self.surface)
    if not self.antialias_drawing:
      self.context.set_antialias( cairo.ANTIALIAS_NONE)
    if not self.antialias_text:
      options = self.context.get_font_options()
      options.set_antialias( cairo.ANTIALIAS_NONE)
      self.context.set_font_options( options)
    self.context.translate( round( -x1*self.scaling+self.scaling*self.margin), round( -y1*self.scaling+self.scaling*self.margin))
    self.context.scale( self.scaling, self.scaling)
    self.context.rectangle( x1, y1, w, h)
    self._set_source_color( self.background_color)
    self.context.paint()
    self.context.new_path()
    self.context.set_source_rgb( 0, 0, 0)
    [self.draw_mol( mol) for mol in mols]
    # write the content to the file
    self.write_surface()
    # flip y coordinates back
    for v in mol.vertices:
      v.y = -v.y


  def mol_to_cairo( self, mol, filename, format="png"):
    """This is a convenience method kept for backward compatibility,
    it just calls mols_to_cairo internally"""
    return self.mols_to_cairo( [mol], filename, format=format)


  def _round( self, x):
    if self.line_width % 2:
      return round( x) + 0.5
    return round( x)

  def _draw_edge( self, e):
    # at first detect the need to make 3D adjustments
    self._transform = transform3d.Transform3d()
    self._invtransform = transform3d.Transform3d()
    transform = None
    if e.order > 1:
      atom1,atom2 = e.vertices
      for n in atom1.neighbors + atom2.neighbors:
        # e.atom1 and e.atom2 are in this list as well
        if n.z != 0:
          # engage 3d transform prior to detection of where to draw
          transform = self._get_3dtransform_for_drawing( e)
          #transform = None
          break
      if transform:
        for n in atom1.neighbors + atom2.neighbors:
          n.coords = transform.transform_xyz( *n.coords)
        self._transform = transform
        self._invtransform = transform.get_inverse()
    # // end of 3D adjustments
    # now the code itself
    coords = self._where_to_draw_from_and_to( e)
    if coords:
      start = coords[:2]
      end = coords[2:]
      label_targets = {}
      for v, ((ox, oy), bbox) in self._vertex_to_bbox.items():
        dx = v.x - ox
        dy = v.y - oy
        adj_bbox = (bbox[0]+dx, bbox[1]+dy, bbox[2]+dx, bbox[3]+dy)
        label_targets[v] = make_box_target(adj_bbox)
      constraints = make_attach_constraints(line_width=self.line_width)
      context = BondRenderContext(
        molecule=self.molecule,
        line_width=self.line_width,
        bond_width=self.bond_width,
        wedge_width=self.wedge_width,
        bold_line_width_multiplier=self.bold_line_width_multiplier,
        bond_second_line_shortening=self.bond_second_line_shortening,
        color_bonds=self.color_bonds,
        atom_colors=self.atom_colors,
        shown_vertices=self._shown_vertices,
        bond_coords=None,
        bond_coords_provider=self._bond_coords_for_edge,
        point_for_atom=self._point_for_atom,
        label_targets=label_targets,
        attach_targets=label_targets,
        attach_constraints=constraints,
      )
      ops = build_bond_ops( e, start, end, context)
      render_ops.ops_to_cairo( self.context, ops)

    if transform:
      # if transform was used, we need to transform back
      for n in atom1.neighbors + atom2.neighbors:
        n.coords = self._invtransform.transform_xyz( *n.coords)


  def _point_for_atom( self, atom):
    return (atom.x, atom.y)


  def _bond_coords_for_edge( self, edge):
    coords = self._where_to_draw_from_and_to( edge)
    if not coords:
      return None
    return (coords[:2], coords[2:])


  def _where_to_draw_from_and_to( self, b):
    def fix_bbox( a):
      x, y = a.x, a.y
      data = self._vertex_to_bbox.get( a, None)
      if data:
        (ox, oy), bbox = data
        dx = x - ox
        dy = y - oy
        bbox = [bbox[0]+dx,bbox[1]+dy,bbox[2]+dx,bbox[3]+dy]
        return bbox
      return None
    # at first check if the bboxes are not overlapping
    atom1, atom2 = b.vertices
    x1, y1 = atom1.x, atom1.y
    x2, y2 = atom2.x, atom2.y
    bbox1 = fix_bbox( atom1)
    bbox2 = fix_bbox( atom2)
    if bbox1 and bbox2 and geometry.do_rectangles_intersect( bbox1, bbox2):
      return None
    # then we continue with computation
    if bbox1:
      x1, y1 = geometry.intersection_of_line_and_rect( (x1,y1,x2,y2), bbox1, round_edges=0)
    if bbox2:
      x2, y2 = geometry.intersection_of_line_and_rect( (x1,y1,x2,y2), bbox2, round_edges=0)
    if geometry.point_distance( x1, y1, x2, y2) <= 1.0:
      return None
    else:
      return (x1, y1, x2, y2)


  def _is_there_place( self, atom, x, y):
    x1, y1 = atom.x, atom.y
    angle1 = geometry.clockwise_angle_from_east( x-x1, y-y1)
    for n in atom.neighbors:
      angle = geometry.clockwise_angle_from_east( n.x-x1, n.y-y1)
      if abs( angle - angle1) < 0.3:
        return False
    return True


  def _find_place_around_atom( self, atom):
    x, y = atom.x, atom.y
    coords = [(a.x,a.y) for a in atom.neighbors]
    # now we can compare the angles
    angles = [geometry.clockwise_angle_from_east( x1-x, y1-y) for x1,y1 in coords]
    angles.append( 2*math.pi + min( angles))
    angles = sorted(angles, reverse=True)
    diffs = misc.list_difference( angles)
    i = diffs.index( max( diffs))
    angle = (angles[i] +angles[i+1]) / 2
    return angle


  def _draw_vertex( self, v):
    pos = sum( [(a.x < v.x) and -1 or 1 for a in v.neighbors if abs(a.x-v.x)>0.2])
    if 'show_symbol' in v.properties_:
      show_symbol = v.properties_['show_symbol']
    else:
      show_symbol = (v.symbol != "C" or v.degree == 0 or self.show_carbon_symbol)
    if show_symbol:
      x = v.x
      y = v.y
      text = v.symbol
      # RADICAL
      if v.multiplicity > 1:
        text += "."*(v.multiplicity-1)
      hs = ""
      if self.show_hydrogens_on_hetero or v.properties_.get( 'show_hydrogens', False):
        if v.get_hydrogen_count() == 1:
          hs = "H"
        elif v.get_hydrogen_count() > 1:
          hs = "H<sub>%d</sub>" % v.get_hydrogen_count()
      if not hs:
        pos = -1
      if pos <= 0:
        text += hs
      else:
        text = hs + text
      # charge
      charge = ""
      if v.charge == 1:
        charge = "<sup>+</sup>"
      elif v.charge == -1:
        charge = "<sup>&#x2212;</sup>"
      elif v.charge > 1:
        charge = "<sup>%d+</sup>" % v.charge
      elif v.charge < -1:
        charge = "<sup>%d&#x2212;</sup>" % abs( v.charge)
      if charge:
        if self._is_there_place( v, v.x+3, v.y-2) or v.charge < 0:
          # we place negative charge regardless of available place
          # otherwise minus might be mistaken for a bond
          text += charge
          charge = ""

      # coloring
      if self.color_atoms:
        color = self.atom_colors.get( v.symbol, (0,0,0))
      else:
        color = (0,0,0)
      center_letter = pos <= 0 and 'first' or 'last'
      bbox = self._draw_text( (x,y), text, center_letter=center_letter, color=color)
      self._vertex_to_bbox[v] = ((x,y), geometry.expand_rectangle( bbox, self.space_around_atom))

      # sometimes charge is done here, if it wasn't done before
      if charge:
        assert v.charge > 0
        # if charge was not dealt with we change its appearance from 2+ to ++
        charge = v.charge * "+"
        if self._is_there_place( v, v.x, v.y-10):
          angle = 1.5*math.pi
        elif self._is_there_place( v, v.x, v.y+10):
          angle = 0.5*math.pi
        else:
          angle = self._find_place_around_atom( v)
        self.context.set_font_size( self.subscript_size_ratio * self.font_size)
        xbearing, ybearing, width, height, x_advance, y_advance = self.context.text_extents( charge)
        x0 = v.x + 40*math.cos( angle)
        y0 = v.y + 40*math.sin( angle)
        line = (v.x,v.y,x0,y0)
        charge_bbox = [x0-0.5*width,y0-0.5*height,x0+0.5*width,y0+0.5*height]
        x1, y1 = geometry.intersection_of_line_and_rect( line, bbox, round_edges=0)
        x2, y2 = geometry.intersection_of_line_and_rect( line, charge_bbox, round_edges=0)
        x2, y2 = geometry.elongate_line( x1,y1,x2,y2, -self.space_around_atom)
        x = x0 + x1 - x2
        y = y0 + y1 - y2
        # draw
        self.context.set_source_rgb( *color)
        self.context.move_to( round( x-xbearing-0.5*width), round( y+0.5*height))
        if self.text_to_curves:
          self.context.text_path( charge)
          self.context.fill()
        else:
          self.context.show_text( charge)


  def _get_3dtransform_for_drawing( self, b):
    """this is a helper method that returns a transform3d which rotates
    a bond and its neighbors to coincide with the x-axis and rotates neighbors to be in (x,y)
    plane."""
    atom1, atom2 = b.vertices
    x1,y1,z1 = atom1.coords
    x2,y2,z2 = atom2.coords
    t = geometry.create_transformation_to_coincide_point_with_z_axis( [x1,y1,z1],[x2,y2,z2])
    x,y,z = t.transform_xyz( x2,y2,z2)
    # now rotate to make the plane of neighbor atoms coincide with x,y plane
    angs = []
    for n in atom1.neighbors + atom2.neighbors:
      if n is not atom1 and n is not atom2:
        nx,ny,nz = t.transform_xyz( *n.coords)
        ang = math.atan2( ny, nx)
        if ang < -0.00001:
          ang += math.pi
        angs.append( ang)
    ang = sum( angs) / len( angs)
    t.set_rotation_z( ang + math.pi/2.0)
    t.set_rotation_y( math.pi/2.0)
    return t


  ## ------------------------------ lowlevel drawing methods ------------------------------
  def _draw_text( self, xy, text, font_name=None, font_size=None, center_letter=None,
                  color=(0,0,0)):
    class text_chunk(object):
      def __init__( self, text, attrs=None):
        self.text = text
        self.attrs = attrs or set()

    def collect_chunks( element, chunks, above):
      above.append( element.tag)
      if element.text:
        chunks.append( text_chunk( element.text, attrs=set( above)))
      for child in list(element):
        collect_chunks( child, chunks, above)
        if child.tail:
          chunks.append( text_chunk( child.tail, attrs=set( above)))
      above.pop()

    # parse the text for markup
    try:
      root = safe_xml.parse_xml_string( "<x>%s</x>" % text)
    except Exception:
      chunks = [text_chunk( text)]
    else:
      chunks = []
      collect_chunks( root, chunks, [])

    if not font_name:
      font_name = self.font_name
    if not font_size:
      font_size = self.font_size

    # font properties
    if self.font_weight == "bold":
      weight = cairo.FONT_WEIGHT_BOLD
    elif self.font_weight == "normal":
      weight = cairo.FONT_WEIGHT_NORMAL
    else:
      raise ValueError( "unknown font_weight '%s'" % self.font_weight)
    self.context.select_font_face( font_name, cairo.FONT_SLANT_NORMAL, weight)
    self.context.set_font_size( font_size)
    asc, desc, letter_height, _a, _b = self.context.font_extents()
    x, y = xy
    if center_letter == 'first':
      if "sup" in chunks[0].attrs or 'sub' in chunks[0].attrs:
        self.context.set_font_size( int( font_size * self.subscript_size_ratio))
      else:
        self.context.set_font_size( font_size)
      xbearing, ybearing, width, height, x_advance, y_advance = self.context.text_extents( chunks[0].text[0])
      x -= 0.5*x_advance
      y += 0.5*height
    elif center_letter == 'last':
      # this is more complicated - we must do a dry run of the text layout
      _dx = 0
      for i,chunk in enumerate( chunks):
        if "sup" in chunk.attrs or 'sub' in chunk.attrs:
          self.context.set_font_size( int( font_size * self.subscript_size_ratio))
        else:
          self.context.set_font_size( font_size)
        xbearing, ybearing, width, height, x_advance, y_advance = self.context.text_extents( chunk.text)
        _dx += x_advance
      # last letter
      xbearing, ybearing, width, height, x_advance, y_advance = self.context.text_extents( chunk.text[-1])
      x -= _dx - 0.5*x_advance
      y += 0.5*height

    self.context.new_path()
    x1 = round( x)
    bbox = None
    for chunk in chunks:
      y1 = round( y)
      if "sup" in chunk.attrs:
        y1 -= asc / 2
        self.context.set_font_size( int( font_size * self.subscript_size_ratio))
      elif "sub" in chunk.attrs:
        y1 += asc / 2
        self.context.set_font_size( int( font_size * self.subscript_size_ratio))
      else:
        self.context.set_font_size( font_size)
      xbearing, ybearing, width, height, x_advance, y_advance = self.context.text_extents( chunk.text)
      # background
      if self.add_background_to_text:
        self.context.rectangle( x1+xbearing, y1+ybearing, width, height)
        self._set_source_color( self.background_color)
        self.context.fill()
        #self.context.set_line_width( 3)
        #self.context.stroke()
      # text itself
      _bbox = [x1+xbearing, y1+ybearing, x1+xbearing+width, y1+ybearing+height]
      self._bboxes.append( _bbox)
      # store bbox for the first chunk only
      if not bbox or center_letter=='last':
        bbox = _bbox
      self.context.set_source_rgb( *color)
      self.context.move_to( x1, y1)
      if self.text_to_curves:
        self.context.text_path( chunk.text)
        self.context.fill()
      else:
        self.context.show_text( chunk.text)
      #self.context.fill()
      x1 += x_advance
    return bbox


  # not used
  def _draw_rectangle( self, coords, fill_color=(1,1,1)):
    #outline = self.paper.itemcget( item, 'outline')
    x1, y1, x2, y2 = coords
    self.context.set_line_join( cairo.LINE_JOIN_MITER)
    self.context.rectangle( x1, y1, x2-x1, y2-y1)
    self.context.set_source_rgb( *fill_color)
    self.context.fill_preserve()
    #self.context.set_line_width( width)
    #self.set_cairo_color( outline)
    self.context.stroke()


  def _create_cairo_path( self, points, closed=False):
    points = [self._invtransform.transform_xyz( p[0],p[1],0)[:2] for p in points]
    x, y = points[0]
    self.context.move_to( x, y)
    for (x,y) in points[1:]:
      self.context.line_to( x, y)
    if closed:
      self.context.close_path()


  def _get_bbox( self):
    bbox = list( self._bboxes[0])
    for _bbox in self._bboxes[1:]:
      x1,y1,x2,y2 = _bbox
      if x1 < bbox[0]:
        bbox[0] = x1
      if y1 < bbox[1]:
        bbox[1] = y1
      if x2 > bbox[2]:
        bbox[2] = x2
      if y2 > bbox[3]:
        bbox[3] = y2
    return bbox


  def _set_source_color( self, color):
    """depending on the value of color uses the proper method,
    either set_source_rgb or set_source_rgba"""
    if len( color) == 3:
      self.context.set_source_rgb( *color)
    elif len( color) == 4:
      self.context.set_source_rgba( *color)
    else:
      raise ValueError( "wrong specification of color '%s'" % color)



def mol_to_png( mol, filename, **kw):
  c = cairo_out( **kw)
  c.mol_to_cairo( mol, filename)


def mols_to_png( mols, filename, **kw):
  c = cairo_out( **kw)
  c.mols_to_cairo( mols, filename)


def mol_to_cairo( mol, filename, format, **kw):
  c = cairo_out( **kw)
  c.mol_to_cairo( mol, filename, format=format)


def mols_to_cairo( mols, filename, format, **kw):
  c = cairo_out( **kw)
  c.mols_to_cairo( mols, filename, format=format)



if __name__ == "__main__":

  from oasa import smiles_lib as smiles

  mol = smiles.text_to_mol( "FCCSCl", calc_coords=30)
  #mol.vertices[0].properties_['show_hydrogens'] = False
  #mol.vertices[1].properties_['show_symbol'] = False
  #mol.vertices[2].properties_['show_symbol'] = True
  mol_to_png( mol, "output.png", show_hydrogens_on_hetero=True, scaling=2)

##   from . import inchi
##   mol = inchi.text_to_mol( "1/C7H6O2/c8-7(9)6-4-2-1-3-5-6/h1-5H,(H,8,9)", include_hydrogens=False, calc_coords=30)
##   mol_to_png( mol, "output.png")
