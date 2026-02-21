"""Display/interaction mixin methods for BKChem bonds."""

from bkchem import theme_manager
from oasa import geometry


class BondDisplayMixin:
  """UI/display helpers extracted from bond.py."""

  def redraw(self, recalc_side=0):
    if not getattr(self, "_bond__dirty", 0):
      pass
      # print("redrawing non-dirty bond")
    if self.item:
      self.delete()
    self.draw(automatic=recalc_side and "both" or "none")
    # redraw selection attribute
    if self._selected:
      self.select()
    self._bond__dirty = 0

  def simple_redraw(self):
    """Very fast redraw that draws only a simple line instead of the bond."""
    [self.paper.delete(i) for i in self.second]
    self.second = []
    [self.paper.delete(i) for i in self.third]
    self.third = []
    if self.items:
      list(map(self.paper.delete, self.items))
      self.items = []
    self._render_item_ids = []
    x1, y1 = self.atom1.get_xy()
    x2, y2 = self.atom2.get_xy()
    x1, y1, x2, y2 = list(map(round, [x1, y1, x2, y2]))
    if self.item and not self.paper.type(self.item) == "line":
      self.paper.unregister_id(self.item)
      self.paper.delete(self.item)
      self.item = None
    if not self.item:
      # the bond might not be drawn because it was too short
      self.item = self.paper.create_line((x1, y1, x2, y2))
      self.paper.register_id(self.item, self)
    else:
      self.paper.coords(self.item, x1, y1, x2, y2)
    # use theme-mapped color for display while preserving stored color for CDML
    display_color = theme_manager.map_chemistry_color(self.line_color)
    self.paper.itemconfig(self.item, width=self.line_width, fill=display_color)

  def visible_items(self):
    """Return a list of canvas items displayed by this bond."""
    if getattr(self, "_render_item_ids", None):
      return list(self._render_item_ids)
    items = []
    if self.order in (1, 3):
      if self.type in "nwba":
        items = [self.item]
    elif self.order == 2:
      if not self.type == "h" and not self.center:
        items = [self.item]

    if self.second:
      items += self.second
    if self.third:
      items += self.third
    if self.items:
      items += self.items

    return items

  def focus(self):
    items = self.visible_items()

    if self.type in "nahds":
      [self.paper.itemconfig(item, fill=self.paper.highlight_color, width=self.line_width + 1) for item in items]
    elif self.type == "o":
      [self.paper.itemconfig(item, fill=self.paper.highlight_color, outline=self.paper.highlight_color) for item in items]
    elif self.type in "wb":
      [self.paper.itemconfigure(item, fill=self.paper.highlight_color) for item in items]

  def unfocus(self):
    items = self.visible_items()
    # use theme-mapped color when restoring from highlight
    display_color = theme_manager.map_chemistry_color(self.line_color)

    if self.type in "nahds":
      [self.paper.itemconfig(item, fill=display_color, width=self.line_width) for item in items]
    elif self.type == "o":
      [self.paper.itemconfig(item, fill=display_color, outline=display_color) for item in items]
    elif self.type in "wb":
      [self.paper.itemconfigure(item, fill=display_color) for item in items]

  def select(self):
    x1, y1 = self.atom1.get_xy_on_paper()
    x2, y2 = self.atom2.get_xy_on_paper()
    x = (x1 + x2) / 2
    y = (y1 + y2) / 2
    if self.selector:
      self.paper.coords(self.selector, x - 2, y - 2, x + 2, y + 2)
    else:
      self.selector = self.paper.create_rectangle(
        x - 2, y - 2, x + 2, y + 2, outline=self.paper.highlight_color
      )
    self._selected = 1

  def unselect(self):
    self.paper.delete(self.selector)
    self.selector = None
    self._selected = 0

  def move(self, dx, dy, use_paper_coords=False):
    """Move object with its selector (when present)."""
    if not use_paper_coords:
      dx = self.paper.real_to_canvas(dx)
      dy = self.paper.real_to_canvas(dy)
    items = [i for i in ([self.item] + self.second + self.third + self.items) if i]
    if self.selector:
      items.append(self.selector)
    [self.paper.move(o, dx, dy) for o in items]

  def delete(self):
    items = [self.item] + self.second + self.third + self.items
    if getattr(self, "_render_item_ids", None):
      items = list(self._render_item_ids)
    if self.selector:
      items += [self.selector]
      self.selector = None
    if self.item:
      self.paper.unregister_id(self.item)
    self.item = None
    self.second = []
    self.third = []
    self.items = []
    self._render_item_ids = []
    list(map(self.paper.delete, items))
    return self

  def bbox(self):
    """Return the object bbox as [x1, y1, x2, y2]."""
    return self.paper.bbox(self.item)

  def lift(self):
    [self.paper.lift(i) for i in self.items]
    if self.selector:
      self.paper.lift(self.selector)
    if self.second:
      [self.paper.lift(o) for o in self.second]
    if self.third:
      [self.paper.lift(o) for o in self.third]
    if self.item:
      self.paper.lift(self.item)

  def transform(self, tr):
    if not self.item:
      return
    for i in [self.item] + self.second + self.third + self.items:
      coords = self.paper.coords(i)
      tr_coords = tr.transform_xy_flat_list(coords)
      self.paper.coords(i, tuple(tr_coords))
    if self.selector:
      self.unselect()
      self.select()
    if self.order == 2 and not self.center and self.second:
      line = list(self.atom1.get_xy())
      line += self.atom2.get_xy()
      x, y = self.paper.coords(self.second[0])[0:2]
      sign = geometry.on_which_side_is_point(line, (x, y))
      if sign * self.bond_width < 0:
        self.bond_width *= -1

  def get_exportable_items(self):
    """Return (line_items, items) tuple used by exporters."""
    if getattr(self, "_render_item_ids", None):
      line_items = []
      items = []
      for item in self._render_item_ids:
        if self.paper.type(item) == "line":
          line_items.append(item)
        else:
          items.append(item)
      return line_items, items
    if self.type == "d":
      if self.simple_double and not self.center and not self.order in (0, 1):
        line_items = [self.item]
        items = self.second + self.third
      else:
        line_items = self.items
        items = self.second + self.third
    elif self.type == "o":
      if self.simple_double and not self.center and not self.order in (0, 1):
        line_items = [self.item]
        items = self.second + self.third
      else:
        line_items = []
        items = self.items + self.second + self.third
    else:
      if self.type == "h":
        items = self.items
      else:
        if self.center:
          items = []
        else:
          items = [self.item]
      if self.type == "n" or (not self.simple_double and not self.center):
        items += self.second
        items += self.third
        line_items = []
      else:
        line_items = self.second + self.third
    return line_items, items
