#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------

"""Home of the bond class.

"""



import importlib
import oasa

from bkchem import misc

from bkchem.singleton_store import Screen
from bkchem.parents import meta_enabled, line_colored, drawable, with_line, interactive, child_with_paper

try:
  from bkchem.bond_cdml import BondCDMLMixin
  from bkchem.bond_display import BondDisplayMixin
  from bkchem.bond_drawing import BondDrawingMixin
  from bkchem.bond_render_ops import BondRenderOpsMixin
  from bkchem.bond_type_control import BondTypeControlMixin
except ImportError:
  # Support legacy top-level import mode (sys.path points at bkchem module dir).
  BondCDMLMixin = importlib.import_module("bond_cdml").BondCDMLMixin
  BondDisplayMixin = importlib.import_module("bond_display").BondDisplayMixin
  BondDrawingMixin = importlib.import_module("bond_drawing").BondDrawingMixin
  BondRenderOpsMixin = importlib.import_module("bond_render_ops").BondRenderOpsMixin
  BondTypeControlMixin = importlib.import_module("bond_type_control").BondTypeControlMixin


### NOTE: now that all classes are children of meta_enabled, so the read_standard_values method
### is called during their __init__ (in fact meta_enabled.__init__), therefore these values are
### not set in __init__ itself


class bond(
  BondRenderOpsMixin,
  BondTypeControlMixin,
  BondDrawingMixin,
  BondDisplayMixin,
  BondCDMLMixin,
  meta_enabled,
  line_colored,
  drawable,
  with_line,
  interactive,
  child_with_paper,
  oasa.bond,
):
  # note that all children of simple_parent have default meta infos set
  # therefore it is not necessary to provide them for all new classes if they
  # don't differ

  object_type = 'bond'
  # these values will be automaticaly read from paper.standard on __init__
  # bond_width couldn't be because it has sign that is important
  # widths need to be calculated therefore are also not here (to be fixed)
  meta__used_standard_values = ['line_color','double_length_ratio']
  # undo related metas
  meta__undo_properties = line_colored.meta__undo_properties + \
                          with_line.meta__undo_properties + \
                          ('molecule', 'type', 'order', 'atom1', 'atom2',
                           'center', 'bond_width','double_length_ratio', 'wedge_width',
                           'simple_double','auto_bond_sign')




  def __init__( self, standard=None, atoms=(), package=None, molecule=None, type='n', order=1,
                simple_double=1):
    # initiation
    self.molecule = molecule
    oasa.bond.__init__( self, order=order, vs=atoms, type=type)
    meta_enabled.__init__( self, standard=standard)
    line_colored.__init__( self)
    drawable.__init__( self)
    with_line.__init__( self)

    # bond data
    self.type = type
      #Bond types:
      # n = normal
      # w = wedge (3d out of screen)
      # h = hashed (3d into screen)
      # a = any stereochemistry
      # b = bold
      # d = dotted - - - -
      # o = dotted . . . .
      # s = wavy
      # q = wide rectangle (Haworth)
    self.order = order
    if atoms:
      self.atom1, self.atom2 = atoms

    # canvas data
    self.item = None  #Used for selection, sometimes not displayed (eg. is a straight line for hashed bonds).
    self.second = []  #see below --v
    self.third = []   #Accessory items, used by double bonds ( both if centered, one if not ) and triple bonds (both, always centered).
    self.items = []   #Used as main item to display by bonds with more items (hashed, dotted, ...)
    self._render_item_ids = []  # Shared render-ops draw path output ids.
    self.selector = None
    self._selected = 0

    # implicit values
    self.center = None  #boolean, used by double bonds. If self.center -> only self.second and self.third are displayed.
    self.auto_bond_sign = 1
    self.simple_double = simple_double  #TODO this is an option for non-normal bonds with order > 1. Currently does not affect appearence (BUG).
    self.equithick = 0
    self.wavy_style = None

    if package:
      self.read_package( package)


  # Override of drawable.dirty
  @property
  def dirty(self):
    return self.__dirty # or self.atom1.dirty or self.atom2.dirty


  @dirty.setter
  def dirty(self, dirty):
    self.__dirty = dirty


  @property
  def molecule(self):
    return self.__molecule


  @molecule.setter
  def molecule(self, mol):
    self.__molecule = mol


  @property
  def type(self):
    return self.__type


  @type.setter
  def type(self, mol):
    self.__type = mol
    self.__dirty = 1


  @property
  def order(self):
    return oasa.bond.order.__get__(self)


  @order.setter
  def order(self, mol):
    oasa.bond.order.__set__(self, mol)
    self.__dirty = 1


  @property
  def atom1(self):
    try:
      return self._vertices[0]
    except IndexError:
      return None


  @atom1.setter
  def atom1(self, mol):
    try:
      self._vertices[0] = mol
    except IndexError:
      self._vertices = [mol, None]
    self.__dirty = 1


  @property
  def atom2(self):
    try:
      return self._vertices[1]
    except IndexError:
      return None


  @atom2.setter
  def atom2(self, mol):
    try:
      self._vertices[1] = mol
    except IndexError:
      self._vertices = [None, mol]
    self.__dirty = 1


  @property
  def atoms(self):
    return self._vertices


  @atoms.setter
  def atoms(self, mol):
    self._vertices = mol
    self.__dirty = 1


  @property
  def center(self):
    return self.__center


  @center.setter
  def center(self, mol):
    self.__center = mol
    self.__dirty = 1


  @property
  def bond_width(self):
    return self.__bond_width


  @bond_width.setter
  def bond_width(self, mol):
    self.__bond_width = mol
    self.__dirty = 1


  @property
  def wedge_width(self):
    return self.__wedge_width


  @wedge_width.setter
  def wedge_width(self, mol):
    self.__wedge_width = mol
    self.__dirty = 1


  @property
  def simple_double(self):
    return self.__simple_double


  @simple_double.setter
  def simple_double(self, mol):
    self.__simple_double = mol
    self.__dirty = 1


  @property
  def double_length_ratio(self):
    return self.__double_length_ratio


  @double_length_ratio.setter
  def double_length_ratio(self, mol):
    self.__double_length_ratio = mol
    self.__dirty = 1


  @property
  def auto_bond_sign(self):
    return self.__auto_bond_sign


  @auto_bond_sign.setter
  def auto_bond_sign(self, mol):
    self.__auto_bond_sign = mol
    self.__dirty = 1


  @property
  def parent(self):
    """Returns self.molecule.

    """
    return self.molecule


  @parent.setter
  def parent(self, par):
    self.molecule = par


  def read_standard_values( self, standard, old_standard=None):
    meta_enabled.read_standard_values( self, standard, old_standard=old_standard)
    # wedge width
    if not old_standard or (standard.wedge_width != old_standard.wedge_width):
      self.wedge_width = Screen.any_to_px( standard.wedge_width)
    # line width
    if not old_standard or (standard.line_width != old_standard.line_width):
      self.line_width = Screen.any_to_px( standard.line_width)
    # bond width
    if not old_standard or (standard.bond_width != old_standard.bond_width):
      if hasattr( self, 'bond_width'):
        self.bond_width = misc.signum( self.bond_width) * Screen.any_to_px( standard.bond_width)
      else:
        self.bond_width = Screen.any_to_px( standard.bond_width)

