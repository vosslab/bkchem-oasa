"""Focused visual-geometry contracts for Qt atom and bond render items."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.canvas.items.render_ops_painter
import bkchem_qt.models.molecule_model
import bkchem_qt.themes.theme_loader


#============================================
def _bond_with_explicit_carbon_label() -> tuple[object, object, object]:
	"""Return a horizontal C--N bond whose endpoints both have labels."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	carbon = molecule.create_atom(symbol="C")
	nitrogen = molecule.create_atom(symbol="N")
	carbon.set_xyz(0.0, 0.0, 0.0)
	nitrogen.set_xyz(80.0, 0.0, 0.0)
	carbon.show = True
	molecule.add_atom(carbon)
	molecule.add_atom(nitrogen)
	bond = molecule.create_bond(order=1, bond_type="n")
	molecule.add_bond(carbon, nitrogen, bond)
	return carbon, nitrogen, bkchem_qt.canvas.items.bond_item.BondItem(bond)


#============================================
def _horizontal_line_ends(item: object) -> tuple[float, float]:
	"""Return left and right endpoints of the rendered single-bond line."""
	points = []
	for op in item._ops:
		if op.kind == "line":
			points.extend((op.points[0][0], op.points[1][0]))
	return min(points), max(points)


#============================================
def _render_local_item(item: object) -> PySide6.QtGui.QImage:
	"""Paint one item into a transparent local image for pixel inspection."""
	bounds = item.boundingRect()
	image = PySide6.QtGui.QImage(
		math.ceil(bounds.width()) + 4,
		math.ceil(bounds.height()) + 4,
		PySide6.QtGui.QImage.Format.Format_ARGB32,
	)
	image.fill(PySide6.QtCore.Qt.GlobalColor.transparent)
	painter = PySide6.QtGui.QPainter(image)
	painter.translate(2.0 - bounds.left(), 2.0 - bounds.top())
	item.paint(painter, PySide6.QtWidgets.QStyleOptionGraphicsItem())
	painter.end()
	return image


#============================================
def _atom_mask_color(item: object) -> PySide6.QtGui.QColor:
	"""Return the painted color just inside one portable atom-label mask."""
	mask = next(
		op for op in item._ops
		if op.kind == "polygon" and op.fill_role == "document-background"
	)
	bounds = item.boundingRect()
	left, top = mask.points[0]
	right, _bottom = mask.points[2]
	image = _render_local_item(item)
	return image.pixelColor(
		int((left + right) / 2.0 - bounds.left() + 2.0),
		int(top - bounds.top() + 3.0),
	)


#============================================
def test_nitrogen_font_change_shortens_only_its_bond_endpoint(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Endpoint clipping follows N typography without moving the C target."""
	del qapp
	_carbon, nitrogen, bond_item = _bond_with_explicit_carbon_label()
	baseline_carbon, baseline_nitrogen = _horizontal_line_ends(bond_item)
	nitrogen.font_size = 28
	large_carbon, large_nitrogen = _horizontal_line_ends(bond_item)

	assert large_nitrogen < baseline_nitrogen and large_carbon == baseline_carbon


#============================================
def test_hidden_endpoint_has_no_bond_label_clipping(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Hiding N removes its label target so its bond reaches the atom point."""
	del qapp
	_carbon, nitrogen, bond_item = _bond_with_explicit_carbon_label()
	nitrogen.show = False
	_left, right = _horizontal_line_ends(bond_item)

	assert right == nitrogen.x


#============================================
def test_bond_bounds_contain_its_full_selection_and_hover_axis(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Clipped depiction still reserves bounds for the raw interaction axis."""
	del qapp
	carbon, nitrogen, bond_item = _bond_with_explicit_carbon_label()
	bounds = bond_item.boundingRect()

	assert bounds.contains(carbon.x, carbon.y) and bounds.contains(nitrogen.x, nitrogen.y)


#============================================
def test_existing_atom_mask_tracks_dark_theme(
		main_window: object,
		) -> None:
	"""A cached atom mask resolves to the active dark-theme area color."""
	original_theme = main_window._theme_manager.current_theme
	main_window._theme_manager.apply_theme("light")
	try:
		molecule = bkchem_qt.models.molecule_model.MoleculeModel()
		atom = molecule.create_atom(symbol="O")
		molecule.add_atom(atom)
		item = bkchem_qt.canvas.items.atom_item.AtomItem(atom)
		main_window._theme_manager.apply_theme("dark")
		expected = bkchem_qt.themes.theme_loader.get_chemistry_colors("dark")["default_area"]

		assert _atom_mask_color(item).name() == expected
	finally:
		main_window._theme_manager.apply_theme(original_theme)


#============================================
def test_atom_label_mask_leaves_padded_corner_transparent(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The label mask is glyph-local while the padded item remains clickable."""
	del qapp
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	atom = molecule.create_atom(symbol="O")
	molecule.add_atom(atom)
	item = bkchem_qt.canvas.items.atom_item.AtomItem(atom)
	image = _render_local_item(item)

	assert image.pixelColor(1, 1).alpha() == 0 and item.shape().contains(PySide6.QtCore.QPointF(0.0, 0.0))
