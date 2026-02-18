"""CDML serialization mixin methods for BKChem bonds."""

import oasa

from bkchem import dom_extensions

from bkchem.singleton_store import Store, Screen


class BondCDMLMixin:
  """CDML read/write helpers extracted from bond.py."""

  def read_package(self, package):
    """Read a dom element package and set internal state according to it."""
    b = ["no", "yes"]
    type = package.getAttribute("type")
    if type:
      type_char = type[0]
      normalized, legacy = oasa.bond_semantics.normalize_bond_type_char(type_char)
      self.type = normalized or "n"
      self.order = int(type[1])
      if legacy:
        self.properties_["legacy_bond_type"] = legacy
    else:
      self.type = "n"
      self.order = 1
    self.id = package.getAttribute("id")
    if package.getAttribute("bond_width"):
      self.bond_width = float(package.getAttribute("bond_width")) * self.paper.real_to_screen_ratio()
    if package.getAttribute("line_width"):
      self.line_width = float(package.getAttribute("line_width"))
    if package.getAttribute("wedge_width"):
      self.wedge_width = float(package.getAttribute("wedge_width"))
    if package.getAttribute("center"):
      self.center = b.index(package.getAttribute("center"))
    else:
      self.center = None
    if package.getAttribute("color"):
      self.line_color = package.getAttribute("color")
    if package.getAttribute("double_ratio"):
      self.double_length_ratio = float(package.getAttribute("double_ratio"))
    if package.getAttribute("simple_double"):
      self.simple_double = int(package.getAttribute("simple_double"))
    if package.getAttribute("auto_sign"):
      self.auto_bond_sign = int(package.getAttribute("auto_sign"))
    if package.getAttribute("equithick"):
      self.equithick = int(package.getAttribute("equithick"))
    else:
      self.equithick = 0
    if package.getAttribute("wavy_style"):
      self.wavy_style = package.getAttribute("wavy_style")
    self.atom1 = Store.id_manager.get_object_with_id(package.getAttribute("start"))
    self.atom2 = Store.id_manager.get_object_with_id(package.getAttribute("end"))
    oasa.cdml_bond_io.read_cdml_bond_attributes(
      package,
      self,
      known_attrs=oasa.cdml_bond_io.CDML_ALL_ATTRS,
    )
    oasa.bond_semantics.canonicalize_bond_vertices(self)

  def post_read_analysis(self):
    """Run post-load analysis for double bond positioning."""
    if self.order == 2:
      sign, center = self._compute_sign_and_center()
      if self.bond_width and self.bond_width * sign < 0:
        self.auto_bond_sign = -1

  def get_package(self, doc):
    """Return a DOM element describing the object in CDML."""
    b = ["no", "yes"]
    bnd = doc.createElement("bond")
    dom_extensions.setAttributes(
      bnd,
      (
        ("type", "%s%d" % (self.type, self.order)),
        ("start", self.atom1.id),
        ("end", self.atom2.id),
        ("id", str(self.id)),
      ),
    )
    values = {}
    values["line_width"] = str(self.line_width)
    values["double_ratio"] = str(self.double_length_ratio)
    if hasattr(self, "equithick") and self.equithick:
      values["equithick"] = str(1)
    if self.order != 1:
      values["bond_width"] = str(self.bond_width * self.paper.screen_to_real_ratio())
      if self.order == 2 and self.center is not None:
        values["center"] = b[int(self.center)]
        if self.auto_bond_sign != 1:
          values["auto_sign"] = str(self.auto_bond_sign)
    if self.type != "n":
      values["wedge_width"] = str(self.wedge_width * self.paper.screen_to_real_ratio())
    if self.line_color != "#000":
      values["color"] = self.line_color
    if self.type != "n" and self.order != 1:
      values["simple_double"] = str(int(self.simple_double))
    if self.wavy_style:
      values["wavy_style"] = self.wavy_style
    defaults = {
      "color": "#000",
      "auto_sign": "1",
      "equithick": "0",
      "simple_double": "1",
    }
    if self.paper and self.paper.standard:
      defaults["line_width"] = str(Screen.any_to_px(self.paper.standard.line_width))
      defaults["double_ratio"] = str(self.paper.standard.double_length_ratio)
      defaults["bond_width"] = str(
        Screen.any_to_px(self.paper.standard.bond_width)
        * self.paper.screen_to_real_ratio()
      )
      defaults["wedge_width"] = str(
        Screen.any_to_px(self.paper.standard.wedge_width)
        * self.paper.screen_to_real_ratio()
      )
    present = oasa.cdml_bond_io.get_cdml_present(self)
    optional_attrs = oasa.cdml_bond_io.select_cdml_attributes(
      values,
      defaults=defaults,
      present=present,
    )
    unknown_attrs = oasa.cdml_bond_io.collect_unknown_cdml_attributes(
      self,
      known_attrs=oasa.cdml_bond_io.CDML_ALL_ATTRS,
      present=present,
    )
    if optional_attrs or unknown_attrs:
      dom_extensions.setAttributes(bnd, tuple(optional_attrs + unknown_attrs))
    return bnd
