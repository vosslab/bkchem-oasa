"""Render-ops drawing mixin for BKChem bonds."""

import math
from warnings import warn

import oasa

from oasa import geometry
from oasa import render_ops
from oasa.render_lib.data_types import BondRenderContext
from oasa.render_lib.data_types import make_attach_constraints
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.bond_ops import build_bond_ops
from oasa.render_lib.bond_ops import haworth_front_edge_geometry
from oasa import wedge_geometry

from bkchem import bkchem_utils


class BondRenderOpsMixin:
  """Shared OASA render-ops based drawing path for BKChem bonds."""

  def draw(self, automatic="none"):
    """Draw bond through shared render ops instead of per-type Tk geometry."""
    if self.item:
      warn("drawing bond that is probably drawn already", UserWarning, 2)

    draw_type = self.type
    if draw_type in ("l", "r"):
      draw_type = "h"
      self.type = "h"

    if (automatic != "none" or self.center is None) and self.order == 2:
      sign, center = self._compute_sign_and_center()
      self.bond_width = self.auto_bond_sign * sign * abs(self.bond_width)
      if automatic == "both":
        self.center = center

    transform = None
    self._transform = oasa.transform3d_lib.Transform3d()
    if self.order != 1 or draw_type != "n":
      for neighbor in self.atom1.neighbors + self.atom2.neighbors:
        if neighbor.z != 0:
          transform = self._get_3dtransform_for_drawing()
          break
      if transform:
        for atom in self.molecule.atoms:
          atom.transform(transform)
        self._transform = transform.get_inverse()

    try:
      x1, y1 = self.atom1.get_xy_on_paper()
      x2, y2 = self.atom2.get_xy_on_paper()
      bbox1 = list(bkchem_utils.normalize_coords(self.atom1.bbox(substract_font_descent=True)))
      bbox2 = list(bkchem_utils.normalize_coords(self.atom2.bbox(substract_font_descent=True)))
      if geometry.do_rectangles_intersect(bbox1, bbox2):
        return None
      ops = self._build_bond_ops((x1, y1), (x2, y2))
      item_ids = self._render_ops_to_tk_canvas(ops)
      self._set_rendered_items(item_ids)
    finally:
      if self._transform:
        for atom in self.molecule.atoms:
          atom.transform(self._transform)
        self._transform = None

  def _build_bond_ops(self, start, end):
    label_targets = {}
    shown_vertices = set()
    for atom in (self.atom1, self.atom2):
      if atom.show:
        shown_vertices.add(atom)
        bbox = bkchem_utils.normalize_coords(atom.bbox(substract_font_descent=True))
        label_targets[atom] = make_box_target(tuple(bbox))
    bond_width_value = self.bond_width
    if bond_width_value is None and self.paper and self.paper.standard:
      bond_width_value = self.paper.standard.bond_width
    wedge_width_value = self.wedge_width
    if wedge_width_value is None and self.paper and self.paper.standard:
      wedge_width_value = self.paper.standard.wedge_width
    line_width = float(self.line_width or 1.0)
    bond_width = abs(float(self.paper.real_to_canvas(bond_width_value or line_width)))
    wedge_width = abs(float(self.paper.real_to_canvas(wedge_width_value or line_width)))
    bold_multiplier = wedge_width / max(line_width, 1e-6)
    constraints = make_attach_constraints(line_width=line_width)
    context = BondRenderContext(
      molecule=self.molecule,
      line_width=line_width,
      bond_width=bond_width,
      wedge_width=wedge_width,
      bold_line_width_multiplier=bold_multiplier,
      bond_second_line_shortening=max(0.0, (1.0 - float(self.double_length_ratio or 1.0)) / 2.0),
      color_bonds=False,
      shown_vertices=shown_vertices,
      label_targets=label_targets,
      attach_targets=label_targets,
      point_for_atom=lambda atom: atom.get_xy_on_paper(),
      attach_constraints=constraints,
    )
    return build_bond_ops(self, start, end, context)

  def _set_rendered_items(self, item_ids):
    ids = [item_id for item_id in item_ids if item_id is not None]
    self._render_item_ids = list(ids)
    if not ids:
      self.item = None
      self.second = []
      self.third = []
      self.items = []
      return
    self.item = ids[0]
    self.second = []
    self.third = []
    self.items = ids[1:]
    self.paper.register_id(self.item, self)

  def _render_ops_to_tk_canvas(self, ops):
    created = []
    for op in render_ops.sort_ops(ops):
      if isinstance(op, render_ops.LineOp):
        color = op.color or self.line_color
        item = self._create_line_with_transform(
          (op.p1[0], op.p1[1], op.p2[0], op.p2[1]),
          tags=("bond",),
          width=op.width,
          fill=color,
          capstyle=op.cap or "butt",
          joinstyle=op.join or "round",
        )
        created.append(item)
        continue
      if isinstance(op, render_ops.PolygonOp):
        coords = []
        for x, y in op.points:
          coords.extend((x, y))
        item = self._create_polygon_with_transform(
          tuple(coords),
          tags=("bond",),
          width=op.stroke_width or 0.0,
          fill=op.fill or "",
          outline=op.stroke or "",
          joinstyle="round",
        )
        created.append(item)
        continue
      if isinstance(op, render_ops.CircleOp):
        cx, cy = op.center
        r = op.radius
        item = self._create_oval_with_transform(
          (cx - r, cy - r, cx + r, cy + r),
          tags=("bond",),
          width=op.stroke_width or 0.0,
          fill=op.fill or "",
          outline=op.stroke or "",
        )
        created.append(item)
        continue
      if isinstance(op, render_ops.PathOp):
        if op.fill and op.fill != "none":
          polygon = self._path_commands_to_polygon(op.commands)
          if polygon:
            coords = []
            for x, y in polygon:
              coords.extend((x, y))
            item = self._create_polygon_with_transform(
              tuple(coords),
              tags=("bond",),
              width=op.stroke_width if op.stroke else 0.0,
              fill=op.fill,
              outline=op.stroke or "",
              joinstyle=op.join or "round",
            )
            created.append(item)
        if op.stroke and op.stroke != "none":
          points = self._path_commands_to_polyline(op.commands)
          if len(points) >= 2:
            coords = []
            for x, y in points:
              coords.extend((x, y))
            item = self._create_line_with_transform(
              tuple(coords),
              tags=("bond",),
              width=op.stroke_width or self.line_width,
              fill=op.stroke,
              capstyle=op.cap or "round",
              joinstyle=op.join or "round",
              smooth=1,
            )
            created.append(item)
    return created

  def _path_commands_to_polyline(self, commands):
    points = []
    step_length = max(2.0, self.line_width)
    for command, data in commands:
      if command in ("M", "L"):
        points.append((data[0], data[1]))
        continue
      if command == "ARC":
        cx, cy, radius, angle_start, angle_end = data
        arc_points = self._arc_points((cx, cy), radius, angle_start, angle_end, step_length)
        if points and arc_points:
          if geometry.point_distance(points[-1][0], points[-1][1], arc_points[0][0], arc_points[0][1]) < 0.01:
            arc_points = arc_points[1:]
        points.extend(arc_points)
    return points

  def _path_commands_to_polygon(self, commands):
    points = self._path_commands_to_polyline(commands)
    if points and points[0] != points[-1]:
      points.append(points[0])
    return points

  def _arc_points(self, center, radius, angle_start, angle_end, step_length):
    if radius <= 0:
      return []
    angle_delta = angle_end - angle_start
    if angle_delta == 0:
      return []
    arc_length = abs(angle_delta) * radius
    if step_length <= 0:
      step_length = 1.0
    steps = max(6, int(round(arc_length / step_length)))
    step = angle_delta / steps
    cx, cy = center
    points = []
    for i in range(steps + 1):
      angle = angle_start + step * i
      points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return points

  # Compatibility helper retained for existing wedge regression tests.
  def _rounded_wedge_polygon(self, coords):
    x1, y1, x2, y2 = coords
    wide_width = self.paper.real_to_canvas(self.wedge_width)
    narrow_width = self.line_width
    if wide_width <= 0:
      return None
    try:
      wedge = wedge_geometry.rounded_wedge_geometry(
        (x1, y1),
        (x2, y2),
        wide_width,
        narrow_width=narrow_width,
      )
    except ValueError:
      return None
    points = self._path_commands_to_polygon(wedge["path_commands"])
    if not points:
      return None
    polygon = []
    for x, y in points:
      polygon.extend((x, y))
    return polygon

  # Compatibility helper retained for existing Haworth front-edge test.
  def _draw_q1(self):
    coords = self._where_to_draw_from_and_to()
    if not coords:
      return None
    x1, y1, x2, y2 = coords
    thickness = self.paper.real_to_canvas(self.wedge_width)
    geometry_info = haworth_front_edge_geometry((x1, y1), (x2, y2), thickness)
    if not geometry_info:
      return None
    start, end, _normal, _cap_radius = geometry_info
    self.item = self._create_line_with_transform(
      (start[0], start[1], end[0], end[1]),
      width=thickness,
      fill=self.line_color,
      capstyle="round",
      joinstyle="round",
    )
    self.paper.addtag_withtag("bond", self.item)
    self.paper.register_id(self.item, self)
    self.second = []
    self.third = []
    self.items = []
    self._render_item_ids = [self.item]
