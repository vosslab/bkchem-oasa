"""Focused Qt presentation checks for canonical CDML bond styles."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets
import shiboken6

# local repo modules
import bkchem_qt.actions.context_menu
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.main_window
import bkchem_qt.models.bond_model
import bkchem_qt.models.document
import bkchem_qt.dialogs.bond_dialog
import bkchem_qt.widgets.property_dock
import bkchem_qt.widgets.edit_ribbon
import oasa.bond_lib


_ORDINARY_CODES = ('n','w','h','a','b','d','o','s')


#============================================
def _combo_choices(combo: PySide6.QtWidgets.QComboBox) -> tuple[tuple[object, str], ...]:
	"""Return the stored code and visible label from a concrete Qt combo."""
	return tuple(
		(combo.itemData(index), combo.itemText(index))
		for index in range(combo.count())
	)


#============================================
def _delete_qobject(
		qapp: PySide6.QtWidgets.QApplication,
		target: PySide6.QtCore.QObject,
		) -> None:
	"""Retire one independently-owned Qt wrapper through deferred deletion."""
	assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, target)


#============================================
def _bond_item(main_window: object) -> object:
	"""Create one projected bond through the public backend-synchronized Draw route."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	if draw_mode is None:
		raise AssertionError("DrawMode did not activate")
	position = PySide6.QtCore.QPointF(180.0, 160.0)
	draw_mode.mouse_press(position, None)
	draw_mode.mouse_release(position, None)
	for item in main_window.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			return item
	raise AssertionError("Draw gesture did not produce a projected BondItem")


#============================================
def _submenu(menu: PySide6.QtWidgets.QMenu, title: str) -> PySide6.QtWidgets.QMenu:
	"""Return one concrete context-menu submenu by its user-facing title."""
	for submenu in menu.findChildren(PySide6.QtWidgets.QMenu):
		if submenu.title() == title:
			return submenu
	raise AssertionError(f"Context menu has no {title} submenu")


#============================================
def _trigger_context_types(type_menu: PySide6.QtWidgets.QMenu, bond_item: object) -> tuple:
	"""Exercise each visible Set Type choice and return its applied CDML code."""
	codes = []
	for action in type_menu.actions():
		action.trigger()
		codes.append(bond_item.bond_model.type)
	return tuple(codes)


#============================================
def test_generic_bond_surfaces_offer_only_ordinary_styles(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Editor, dialog, dock, and real context menu agree on generic bond choices."""
	ribbon = bkchem_qt.widgets.edit_ribbon.EditRibbon()
	model = bkchem_qt.models.bond_model.BondModel(oasa.bond_lib.Bond(type="n"))
	dialog = bkchem_qt.dialogs.bond_dialog.BondDialog(model)
	document = bkchem_qt.models.document.Document()
	dock = bkchem_qt.widgets.property_dock.PropertyDock(document)
	menu = None
	try:
		bond_item = _bond_item(main_window)
		menu = bkchem_qt.actions.context_menu._bond_context_menu(
			bond_item, main_window.view,
		)
		type_menu = _submenu(menu, "Set Type")
		generic_codes = (
			tuple(code for code, _label in _combo_choices(ribbon._type_combo)),
			tuple(code for code, _label in _combo_choices(dialog._type_combo)),
			tuple(code for code, _label in _combo_choices(dock._bond_type_combo)),
			_trigger_context_types(type_menu, bond_item),
		)

		assert generic_codes == (_ORDINARY_CODES,) * 4
		assert all("q" not in codes for codes in generic_codes)
	finally:
		if menu is not None:
			_delete_qobject(qapp, menu)
		dock.set_document(None)
		_delete_qobject(qapp, dock)
		_delete_qobject(qapp, document)
		_delete_qobject(qapp, dialog)
		_delete_qobject(qapp, model)
		_delete_qobject(qapp, ribbon)


#============================================
def test_existing_haworth_bond_is_accurately_displayed(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Existing q bonds retain their visible code and Haworth label in edit surfaces."""
	model = bkchem_qt.models.bond_model.BondModel(oasa.bond_lib.Bond(type="q"))
	dialog = bkchem_qt.dialogs.bond_dialog.BondDialog(model)
	document = bkchem_qt.models.document.Document()
	dock = bkchem_qt.widgets.property_dock.PropertyDock(document)
	try:
		dock._set_bond_type_choices("q")
		haworth_choices = (
			_combo_choices(dialog._type_combo)[-1],
			_combo_choices(dock._bond_type_combo)[-1],
		)

		assert haworth_choices == (("q", "Haworth front edge"), ("q", "Haworth front edge"))
	finally:
		dock.set_document(None)
		_delete_qobject(qapp, dock)
		_delete_qobject(qapp, document)
		_delete_qobject(qapp, dialog)
		_delete_qobject(qapp, model)


#============================================
def test_show_context_menu_retires_transient_menu_tree(
		main_window: object, qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The production modal context-menu path releases its temporary Qt tree."""
	bond_item = _bond_item(main_window)
	scene_position = bond_item.sceneBoundingRect().center()
	view_position = main_window.view.mapFromScene(scene_position)
	screen_position = main_window.view.mapToGlobal(view_position)
	captured_menus: list[PySide6.QtWidgets.QMenu] = []
	destroyed: list[bool] = []

	def record_destroyed(*_args: object) -> None:
		"""Record Qt's deferred destruction of the popup root."""
		destroyed.append(True)

	# ``exec()`` starts a nested Qt loop, so this callback observes the native
	# popup while production owns it and closes it through ordinary Qt delivery.
	def close_popup() -> None:
		"""Capture the production popup and end its modal loop."""
		popup = qapp.activePopupWidget()
		if not isinstance(popup, PySide6.QtWidgets.QMenu):
			raise AssertionError("Context menu did not enter the Qt popup loop")
		captured_menus.extend((popup, *popup.findChildren(PySide6.QtWidgets.QMenu)))
		popup.destroyed.connect(record_destroyed)
		popup.close()

	PySide6.QtCore.QTimer.singleShot(0, close_popup)
	bkchem_qt.actions.context_menu.show_context_menu(
		main_window.view, scene_position, screen_position,
	)
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)
	qapp.processEvents()

	assert (
		captured_menus
		and destroyed
		and not any(shiboken6.isValid(menu) for menu in captured_menus)
	)
