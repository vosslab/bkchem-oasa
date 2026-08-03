"""Focused structural CDML group contracts for the Qt frontend."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.action_registry
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.group_item
import bkchem_qt.io.cdml_document_io
import oasa.cdml_document
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
def test_builtin_group_projection_keeps_expand_action_disabled(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A builtin group remains outside the narrow implicit expansion route."""
	document = bkchem_qt.io.cdml_document_io.decode_compatibility_cdml_string(_GROUP_CDML)
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
		assert document.groups_selected
		assert not registry.is_enabled("chemistry.expand_groups", document)


#============================================
def test_group_observation_keeps_nameless_partial_font_labels_selectable() -> None:
	"""A legacy-visible label remains selectable without gaining expansion authority."""
	cdml = _GROUP_CDML.replace('name="COOH" ', '').replace(
		'family="Helvetica" size="14"', 'family="Helvetica"',
	)
	backend = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	projection_snapshot = backend.projection_snapshot()
	document = bkchem_qt.io.cdml_document_io.hydrate_synchronized_cdml_document(
		projection_snapshot,
	)
	group = document.molecules[0].groups[0]
	assert group.supported and group.name == "" and not group.implicit_expandable
	assert dict(group.font_attributes) == {"family": "Helvetica"}


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

	document = bkchem_qt.io.cdml_document_io.decode_compatibility_cdml_string(_GROUP_CDML)
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	disposal_state: dict[str, bool] = {}
	item = GroupItemProbe(document.molecules[0].groups[0], disposal_state)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		scene.addItem(item)
		document.clear()
		assert disposal_state == {"connected_after_dispose": False}
		document.set_scene(None)
