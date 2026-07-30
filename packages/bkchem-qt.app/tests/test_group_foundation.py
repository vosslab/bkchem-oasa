"""Focused structural CDML group contracts for the Qt frontend."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.action_registry
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.group_item
import bkchem_qt.io.cdml_io
import tests.graphics_test_retirement


_GROUP_CDML = """<cdml version="0.15" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
	<molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
	<group id="g1" name="COOH" group-type="builtin" pos="center-first"><font family="Helvetica" size="14"/>
	<point x="2cm" y="1cm"/></group><bond id="b1" start="a1" end="g1" type="n" order="1"/></molecule></cdml>"""


#============================================
class _ActionApp:
	"""Small registration host exposing the selection state under test."""

	#============================================
	def __init__(self, document: object) -> None:
		"""Retain the document used by Chemistry action predicates."""
		self.document = document


#============================================
def test_group_projection_is_selectable_and_enables_group_action(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A loaded group reaches the same selection predicate as its menu action."""
	document = bkchem_qt.io.cdml_io.load_cdml_document_string(_GROUP_CDML)
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	group = document.molecules[0].groups[0]
	item = bkchem_qt.canvas.items.group_item.GroupItem(group)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		scene.addItem(item)
		item.setSelected(True)
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		bkchem_qt.actions.chemistry_actions.register_chemistry_actions(
				registry, _ActionApp(document),
			)
		assert (document.groups_selected, registry.is_enabled("chemistry.expand_groups", document)) == (True, True)


#============================================
#============================================
#============================================
def test_group_item_teardown_disconnects_before_scene_clear(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A group projection follows the session's explicit graphics disposal path."""
	class GroupItemProbe(bkchem_qt.canvas.items.group_item.GroupItem):
		"""Capture disposal state before native scene retirement invalidates the wrapper."""

		#============================================
		def __init__(self, group_model: object, disposal_state: dict[str, bool]) -> None:
			"""Create one group item that records its post-disconnect state."""
			super().__init__(group_model)
			self._disposal_state = disposal_state

		#============================================
		def dispose(self) -> None:
			"""Record callback detachment while the native wrapper remains valid."""
			super().dispose()
			self._disposal_state["connected_after_dispose"] = self._connected

	document = bkchem_qt.io.cdml_io.load_cdml_document_string(_GROUP_CDML)
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	disposal_state: dict[str, bool] = {}
	item = GroupItemProbe(document.molecules[0].groups[0], disposal_state)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		scene.addItem(item)
		document.clear()
		assert disposal_state == {"connected_after_dispose": False}
		document.set_scene(None)
