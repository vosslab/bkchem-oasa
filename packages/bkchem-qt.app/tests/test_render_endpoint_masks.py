"""Focused visual-geometry contracts for Qt atom and bond render items."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets
import pytest

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
def _horizontal_line_lengths(item: object) -> list[float]:
	"""Return horizontal portable line lengths from longest to shortest."""
	return sorted(
		(abs(operation.points[1][0] - operation.points[0][0])
			for operation in item._ops if operation.kind == "line"),
		reverse=True,
	)


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
def test_explicit_carbon_label_clips_its_bond_endpoint(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A visible carbon glyph and its bond share one backend label target."""
	del qapp
	carbon, nitrogen, bond_item = _bond_with_explicit_carbon_label()
	left, right = _horizontal_line_ends(bond_item)

	assert carbon.x < left < right < nitrogen.x


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
def test_standalone_double_bond_uses_topology_and_authored_line_ratio(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The compatibility projection retains OASA's uncentered-lane contract."""
	del qapp
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	atoms = [molecule.create_atom(symbol="C") for _index in range(3)]
	for atom, point in zip(atoms, ((0.0, 0.0), (80.0, 0.0), (80.0, 40.0)), strict=True):
		atom.set_xyz(point[0], point[1], 0.0)
		molecule.add_atom(atom)
	double_bond = molecule.create_bond(order=2, bond_type="n")
	molecule.add_bond(atoms[0], atoms[1], double_bond)
	initial_ratio = 0.7
	double_bond.double_length_ratio = initial_ratio
	branch = molecule.create_bond(order=1, bond_type="n")
	molecule.add_bond(atoms[1], atoms[2], branch)
	item = bkchem_qt.canvas.items.bond_item.BondItem(double_bond)
	baseline = _horizontal_line_lengths(item)
	double_bond.double_length_ratio = 0.5
	updated = _horizontal_line_lengths(item)

	assert baseline[-1] == pytest.approx(baseline[0] * initial_ratio)
	assert updated[0] == pytest.approx(baseline[0])
	assert updated[-1] == pytest.approx(updated[0] * 0.5)


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
