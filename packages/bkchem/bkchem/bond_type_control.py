"""Bond type/order control and geometry helpers for BKChem bonds."""

import math
from warnings import warn

from oasa import geometry

from bkchem import misc
from bkchem.singleton_store import Screen


class BondTypeControlMixin:
  """Behavior-preserving bond type/order management methods."""

  def toggle_type(self, only_shift=0, to_type='n', to_order=1, simple_double=1):
    self.simple_double = simple_double
    if not only_shift:
      if to_type != self.type:
        self.switch_to_type(to_type)
        self.switch_to_order(to_order)
      elif to_order == 1 and to_type in 'nd':
        v1 = self.atom1.free_valency
        v2 = self.atom2.free_valency
        if not v1 or not v2:
          self.switch_to_order(1)
        else:
          self.switch_to_order((self.order % 3) + 1)
      elif to_order != self.order:
        self.switch_to_order(to_order)
      else:
        if to_type in "ha":
          if self.equithick:
            self.equithick = 0
            self.atom1, self.atom2 = self.atom2, self.atom1
          else:
            self.equithick = 1

        if to_type in "w":
          self.atom1, self.atom2 = self.atom2, self.atom1
          if not self.center:
            self.bond_width = -self.bond_width
        elif to_order == 2:
          if self.center:
            self.bond_width = -self.bond_width
            self.auto_bond_sign = -self.auto_bond_sign
            self.center = 0
          elif self.bond_width > 0:
            self.bond_width = -self.bond_width
            self.auto_bond_sign = -self.auto_bond_sign
          else:
            self.center = 1
    elif self.order == 2:
      if self.center:
        self.bond_width = -self.bond_width
        self.auto_bond_sign = -self.auto_bond_sign
        self.center = 0
      elif self.bond_width > 0:
        self.bond_width = -self.bond_width
        self.auto_bond_sign = -self.auto_bond_sign
      else:
        self.center = 1
    self.redraw()

  def switch_to_type(self, type):
    if type in "wha" and self.type not in "wha":
      self.wedge_width = Screen.any_to_px(self.paper.standard.wedge_width)
    elif type not in "wha" and self.type in "wha":
      self.bond_width = Screen.any_to_px(self.paper.standard.bond_width)
    self.type = type

  def switch_to_order(self, order):
    self.order = order
    if self.order == 3:
      self.center = 0
    if self.order > 1:
      self._decide_distance_and_center()

  def _decide_distance_and_center(self):
    """According to molecular geometry decide bond.center and bond.bond_width."""
    if not self.bond_width:
      self.bond_width = self.standard.bond_width
    if self.order != 2:
      return
    sign, center = self._compute_sign_and_center()
    self.bond_width = self.auto_bond_sign * sign * abs(self.bond_width)
    self.center = center

  def _get_3dtransform_for_drawing(self):
    """Return transform3d rotating the bond onto x-axis and neighbors into plane."""
    x1, y1, z1 = self.atom1.get_xyz()
    x2, y2, z2 = self.atom2.get_xyz()
    t = geometry.create_transformation_to_coincide_point_with_z_axis([x1, y1, z1], [x2, y2, z2])
    x, y, z = t.transform_xyz(x2, y2, z2)
    angs = []
    for n in self.atom1.neighbors + self.atom2.neighbors:
      if n is not self.atom1 and n is not self.atom2:
        nx, ny, nz = t.transform_xyz(*n.get_xyz())
        ang = math.atan2(ny, nx)
        if ang < -0.00001:
          ang += math.pi
        angs.append(ang)
    if angs:
      ang = sum(angs) / len(angs)
    else:
      ang = 0
    t.set_rotation_z(ang + math.pi / 2.0)
    t.set_rotation_y(math.pi / 2.0)
    return t

  def _compute_sign_and_center(self):
    """Return tuple (sign, center) where sign is default sign of bond_width."""
    transform = None
    for n in self.atom1.neighbors + self.atom2.neighbors:
      if n.z != 0:
        transform = self._get_3dtransform_for_drawing()
        break
    if transform:
      for n in self.atom1.neighbors + self.atom2.neighbors:
        n.transform(transform)
    line = self.atom1.get_xy() + self.atom2.get_xy()
    atms = self.atom1.neighbors + self.atom2.neighbors
    atms = misc.difference(atms, [self.atom1, self.atom2])
    coords = [a.get_xy() for a in atms]
    circles = 0
    for ring in self.molecule.get_smallest_independent_cycles_dangerous_and_cached():
      if self.atom1 in ring and self.atom2 in ring:
        on_which_side = lambda xy: geometry.on_which_side_is_point(line, xy)
        circles += sum(map(on_which_side, [a.get_xy() for a in ring if a not in self.atoms]))
    if circles:
      side = circles
    else:
      sides = [geometry.on_which_side_is_point(line, xy, threshold=0.1) for xy in coords]
      side = sum(sides)
    if side == 0 and (len(self.atom1.neighbors) == 1 or len(self.atom2.neighbors) == 1):
      ret = (1, 1)
    else:
      ret = None
      if not circles:
        if self.atom1.show and self.atom2.show:
          ret = (1, 1)
        else:
          for i in range(len(sides)):
            if sides[i] and atms[i].__class__.__name__ == "atom":
              if atms[i].symbol == 'H':
                sides[i] *= 0.1
              elif atms[i].symbol != 'C':
                sides[i] *= 0.2
              side = sum(sides)
      if not ret:
        if side < 0:
          ret = (-1, 0)
        else:
          ret = (1, 0)
    if transform:
      inv = transform.get_inverse()
      for n in self.atom1.neighbors + self.atom2.neighbors:
        n.transform(inv)
    return ret

  def get_atoms(self):
    return self.get_vertices()

  def change_atoms(self, a1, a2):
    """Used in overlap situations, replace reference to atom a1 with a2."""
    if self.atom1 == a1:
      self.atom1 = a2
    elif self.atom2 == a1:
      self.atom2 = a2
    else:
      warn("not bonds' atom in bond.change_atoms(): " + str(a1), UserWarning, 2)
