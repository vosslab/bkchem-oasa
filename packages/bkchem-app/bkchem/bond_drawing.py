"""Drawing-related mixin methods for BKChem bonds."""

from oasa import geometry
from oasa.render_lib.data_types import make_attach_constraints
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.attach_resolution import resolve_attach_endpoint

from bkchem import bkchem_utils


class BondDrawingMixin:
  """Shared drawing helpers extracted from bond.py."""

  def _where_to_draw_from_and_to(self):
    x1, y1 = self.atom1.get_xy_on_paper()
    x2, y2 = self.atom2.get_xy_on_paper()
    bbox1 = list(bkchem_utils.normalize_coords(self.atom1.bbox(substract_font_descent=True)))
    bbox2 = list(bkchem_utils.normalize_coords(self.atom2.bbox(substract_font_descent=True)))
    if geometry.do_rectangles_intersect(bbox1, bbox2):
      return None
    # Resolve clipping against shared target primitives instead of ad-hoc rect math.
    if self.atom1.show:
      x1, y1 = resolve_attach_endpoint(
        bond_start=(x2, y2),
        target=make_box_target(tuple(bbox1)),
        interior_hint=(x1, y1),
        constraints=make_attach_constraints(direction_policy="line"),
      )
    if self.atom2.show:
      x2, y2 = resolve_attach_endpoint(
        bond_start=(x1, y1),
        target=make_box_target(tuple(bbox2)),
        interior_hint=(x2, y2),
        constraints=make_attach_constraints(direction_policy="line"),
      )

    if geometry.point_distance(x1, y1, x2, y2) <= 1.0:
      return None
    return (x1, y1, x2, y2)

  def _create_line_with_transform(self, coords, **kw):
    """Pass through to paper.create_line with optional 3D transform."""
    if self._transform:
      coords = self._transform.transform_xy_flat_list(coords)
    return self.paper.create_line(coords, **kw)

  def _create_oval_with_transform(self, coords, **kw):
    """Pass through to paper.create_oval with optional 3D transform."""
    if self._transform:
      coords = self._transform.transform_xy_flat_list(coords)
    return self.paper.create_oval(coords, **kw)

  def _create_polygon_with_transform(self, coords, **kw):
    """Pass through to paper.create_polygon with optional 3D transform."""
    if self._transform:
      coords = self._transform.transform_xy_flat_list(coords)
    return self.paper.create_polygon(coords, **kw)
