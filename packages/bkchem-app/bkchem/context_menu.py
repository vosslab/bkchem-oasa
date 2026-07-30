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

import builtins
import os
import tkinter

from oasa import periodic_table as PT

from bkchem import bkchem_utils
from bkchem import marks
from bkchem import parents
from bkchem import interactors
import bkchem.chem_compat

from bkchem.atom_lib import BkAtom
from bkchem.group_lib import BkGroup
from bkchem.queryatom_lib import BkQueryatom
from bkchem.singleton_store import Store

# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)



class context_menu( tkinter.Menu):

  def __init__( self, selected: object, **kw) -> None:
    tkinter.Menu.__init__( self, Store.app, tearoff=0, **kw)
    self.selected = selected
    self.changes_made = 0
    items, self.configurable = configuration_items( self.selected)

    # then sort the items and polulate the menu
    keys = sorted(items.keys())
    for key in keys:
      casc = tkinter.Menu( self, tearoff=0)
      self.add_cascade( label=key, menu=casc)
      for (v1, attr, objs, v0) in items[ key]:
        casc.add_command( label=v1, command=bkchem_utils.lazy_apply( self.callback, (attr, objs, v0)))

    # commands
    if items and len( [o for o in self.selected if o.object_type != 'mark']):
      # marks do not have entry in properties dialog
      self.add_separator()
    i = False
    i += self.register_command_by_object_type( _("Center bond"), ('bond',), center)
    i += self.register_command_by_class_name( _("Expand group"), ('group',), expand_groups)
    i += self.register_command_by_object_type( _("Set atom number"), ('atom',), set_atom_number)
    i += self.register_command_through_filter( mark_template_atom_filter, self.selected)
    i += self.register_command_through_filter( mark_template_bond_filter, self.selected)

    # common commands
    if len( [o for o in self.selected if o.object_type != 'mark']):
      # marks do not have entry in properties dialog
      if i:
        self.add_separator()
      self.add_command( label=_("Properties"), command=Store.app.paper.config_selected)


  def callback( self, command: object, objects: object, value: object) -> None:
    for o in objects:
      self.set_value( o, command, value)
    self.finish()


  def set_value( self, o: object, name: object, value: object) -> None:
    """little more enhanced version of bkchem_utils.set_attr_or_property"""
    if name in setter_functions:
      f = setter_functions[ name]
      f( o, value)
      self.changes_made = 1
    else:
      if bkchem_utils.set_attr_or_property( o, name, value):
        o.redraw()
        self.changes_made = 1


  def finish( self) -> None:
    """finishes one callback session"""
    if self.changes_made:
      Store.app.paper.start_new_undo_record()
      Store.app.paper.add_bindings()


  def close( self, event: object) -> None:
    self.unpost()


  def post( self, x: object, y: object) -> None:
    tkinter.Menu.post( self, x, y)
    if os.name != 'nt':
      self.grab_set()


  def register_command_by_object_type( self, label: object, types: object, callback: object) -> bool:
    apply_to = []
    for t in types:
      apply_to.extend( [o for o in self.selected if o.object_type == t])
    return self._register_command( label, apply_to, callback)


  def register_command_by_class_name( self, label: object, types: object, callback: object) -> bool:
    apply_to = []
    for t in types:
      apply_to.extend( [o for o in self.selected if o.__class__.__name__ == t])
    return self._register_command( label, apply_to, callback)


  def _register_command( self, label: object, apply_to: object, callback: object) -> bool:
    if not apply_to:
      return False
    self.add_command( label=label,
                      command=lambda : self.apply_command( callback, apply_to))
    return True


  def register_command_through_filter( self, filter_f: object, objs: object) -> bool:
    ret = filter_f( objs)
    if ret:
      label, callback, apply_to = ret
      return self._register_command( label, apply_to, callback)
    else:
      return False


  def apply_command( self, callback: object, apply_to: object) -> None:
    callback( apply_to)
    Store.app.paper.start_new_undo_record()
    Store.app.paper.add_bindings()



def configuration_items( selected: object) -> tuple[dict, dict]:
  """Build the dynamic context-menu choices for the supplied presentation objects."""
  already_there = []
  configured = {}
  items = {}
  for obj_type in list(configurable.keys()):
    if bkchem_utils.myisstr(obj_type):
      objs = [o for o in selected if o.object_type == obj_type]
    else:
      objs = [o for o in selected if isinstance( o, obj_type)]

    if not objs:
      continue
    for attr in configurable[ obj_type]:
      if bkchem_utils.myisstr(attr):
        # attr can be either a string (key of config_values)
        vals = config_values[ attr]
      elif callable(attr):
        # or it can be a callable that takes list of objects and returns the desired tuple
        attr, vals = attr( objs)
      else:
        raise TypeError(f"Unsupported context-menu configuration: {attr!r}")

      if vals and attr not in already_there:
        items[ vals[ I18N_NAME]] = []
        configured[ obj_type] = configured.get( obj_type, []) + [attr]
        for v in vals[ VALUES]:
          if isinstance(v, tuple):
            items[ vals[ I18N_NAME]].append( (v[1], attr, objs, v[0]))
          else:
            items[ vals[ I18N_NAME]].append( (v, attr, objs, v))
        # to know what is already there
        already_there.append( attr)
      elif vals: # attr is already there
        for tup in items[ vals[ I18N_NAME]]:
          tup[2].extend( objs)
  return items, configured



# functions used in configurable

def draw_mark_circle( objs: object) -> object:
  """used in configurable for marks to choose if there is any mark that ability to have circle around"""
  circled = [o for o in objs if hasattr( o, "draw_circle")]
  if not circled:
    return "draw_circle", None
  else:
    return "draw_circle", (_("Circle around mark"), ((True, _("yes")), (False, _("no"))))


def show_number( objs: object) -> object:
  with_number = [o for o in objs if o.object_type == "atom" and hasattr( o, "number") and o.number != None]
  if not with_number:
    return "show_number", None
  else:
    return "show_number", (_("Show number"), ((True, _("yes")), (False, _("no"))))


def atom_valency( objs: object) -> object:
  # atom valency
  atoms = [o for o in objs if hasattr( o, 'valency') and isinstance( o, BkAtom)]
  # the names must be the same
  if bkchem_utils.has_one_value_only( [a.symbol for a in atoms]):
    name = atoms[0].symbol
    return "valency", (_('Atom valency'), (0,)+PT.periodic_table[ name]['valency'])
  return "valency", None


def mark_size( objs: object) -> object:
  os = [o for o in objs if hasattr( o, "marks")]
  if os:
    return "mark_size", (_("Mark size"), (2,4,6,8,10,12,14,16,18,20,25,30,40,50))
  else:
    return "mark_size", None


# command filters

def mark_template_atom_filter( objs: object) -> object:
  atms = [o for o in objs if bkchem.chem_compat.is_chemistry_vertex( o) and o.degree==1]
  if len( atms) == 1:
    return _("Mark as template atom"), set_template_atom, atms
  else:
    return None


def mark_template_bond_filter( objs: object) -> object:
  bonds = [o for o in objs if bkchem.chem_compat.is_chemistry_edge( o)]
  if len( bonds) == 1:
    return _("Mark as template bond"), set_template_bond, bonds
  else:
    return None



# CONFIGURABLE VALUES

config_values = { 'show':             ( _("Show symbol"),        (('yes',_("yes")),
                                                                  ('no', _("no")))),
                  'show_hydrogens':   ( _("Hydrogens"),          (('on',_("on")),
                                                                  ('off', _("off")))),
                  'font_size':        ( _("Font size"),          (8,10,12,14,16,18)),
                  'line_width':       ( _("Line width"),         (1.0,1.5,2.0,2.5,3.0)),
                  'bond_width':       ( _("Bond width"),         (3,4,5,6,7,8,9,10)),
                  'wedge_width':      ( _("Wedge/Hatch width"),  (3,4,5,6,7,8,9,10)),
                  'pos':              ( _("Symbol positioning"), (("center-first",_("center first")),
                                                                  ("center-last", _("center last")))),
                  'auto_bond_sign':   ( _("Bond positioning"),   ((1, _("auto")),
                                                                  (-1, _("anti-auto")))),
                  'order':            ( _("Bond order"),         (0,1,2,3)),
                  'size':             ( _("Mark size"),          (2,3,4,5,6,8,10,12,14,16,18,20,25,30,40,50)),
                  'number':           ( _("Atom number"),        ('1','2','3','4','5','6','7','8','9','10','11','12')),
                  'area_color':       ( _("Area color"),         (('', _("transparent")),
                                                                  ('white', _("white")),
                                                                  ('yellow', _("yellow")),
                                                                  ('green', _("green")),
                                                                  ('blue', _("blue")),
                                                                  ('red', _("red")),
                                                                  ('black', _("black")))),
                  'line_color':       ( _("Line color"),         (('', _("transparent")),
                                                                  ('white', _("white")),
                                                                  ('yellow', _("yellow")),
                                                                  ('green', _("green")),
                                                                  ('blue', _("blue")),
                                                                  ('red', _("red")),
                                                                  ('black', _("black")))),
                  'free_sites':       ( _("Free sites"),         (0,1,2,3,4,5,6)),
                  'symbol':           ( _("Atom symbol"),        ("C","O","N","H","S","P","F","Cl","Br","I","B")),
                  'group':            ( _("Group"),              ("CHO","COOH","COOCH3","OCH3","Bn","OBn","Bz","OBz","Ts","OTs","Ms","OMs","NO2"))

                  }


## WHAT OBJECT HAS WHAT CONFIGURABLE

configurable = {'atom':    ('show', 'font_size','show_hydrogens','pos','number', 'free_sites', show_number, atom_valency, mark_size),
                'text':    ('font_size',),
                'bond':    ('line_width','bond_width','order','auto_bond_sign','wedge_width'),
                'plus':    ('font_size',),
                'arrow':   ('line_width',),
                'mark':    ('size', draw_mark_circle),
                parents.area_colored: ('area_color',),
                parents.line_colored: ('line_color',),
                (BkAtom, BkQueryatom): ('symbol','group'),
                marks.electronpair: ('line_width',),
                }


I18N_NAME = 0
VALUES = 1


## SETTER FUNCTIONS

def set_show( o: object, value: object) -> None:
  o.show = value
  o.redraw()
  [b.redraw() for b in o.paper.bonds_to_update( exclude_selected_bonds=False)]


def set_show_hydrogens( o: object, value: object) -> None:
  o.show_hydrogens = value
  if o.show_hydrogens:
    o.show = 1  # hydrogens imply showing the symbol
  o.redraw()
  [b.redraw() for b in o.paper.bonds_to_update( exclude_selected_bonds=False)]


def set_bond_auto_sign( o: object, value: object) -> None:
  o.auto_bond_sign = value
  o.redraw( recalc_side=1)


def set_bond_width( o: object, value: object) -> None:
  o.bond_width = value
  o.redraw( recalc_side=1)


def set_symbol( a: object, name: object) -> None:
  v = a.molecule.create_vertex_according_to_text( a, name, interpret=True)
  a.copy_settings( v)
  a.molecule.replace_vertices( a, v)
  a.delete()
  v.draw()
  for b in v.neighbor_edges:
    b.redraw()


def set_mark_size( o: object, value: object) -> None:
  for mark in o.marks:
    mark.size = value
  o.redraw()


def set_symbol_pos( o: object, value: object) -> None:
  o.pos = value
  o.redraw()
  for b in o.neighbor_edges:
    b.redraw()


setter_functions = {'show': set_show,
                    'show_hydrogens': set_show_hydrogens,
                    'auto_bond_sign': set_bond_auto_sign,
                    'bond_width': set_bond_width,
                    'symbol': set_symbol,
                    'group': set_symbol,
                    'mark_size': set_mark_size,
                    'pos': set_symbol_pos}


# COMMANDS

def center( bonds: object) -> None:
  for b in bonds:
    b.center = 1
    b.redraw()


def expand_groups( groups: object) -> None:
  all_gs = set( [g for g in groups if isinstance( g, BkGroup)])
  mols = set( [g.molecule for g in all_gs])
  for mol in mols:
    gs = set( mol.vertices) & set( all_gs)
    mol.expand_groups( atoms=gs)


def set_atom_number( atoms: object) -> None:
  interactors.set_atom_number( atoms)


def set_template_atom( objs: object) -> None:
  if len( objs) == 1:
    a = objs[0]
    if bkchem.chem_compat.is_chemistry_vertex( a):
      a.molecule.mark_template_atom( a)


def set_template_bond( objs: object) -> None:
  if len( objs) == 1:
    b = objs[0]
    if bkchem.chem_compat.is_chemistry_edge( b):
      b.molecule.mark_template_bond( b)
