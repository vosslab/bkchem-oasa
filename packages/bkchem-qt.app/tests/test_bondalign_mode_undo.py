"""Focused public-mode checks for backend-authoritative atom alignment."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.models.document_session


#============================================
def _selected_atoms(main_window: object) -> tuple[object, object]:
	"""Create selected atoms and give the projection their durable test bindings."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	first = draw_mode._create_atom_at(0.0, 0.0, "C")
	second = draw_mode._create_atom_at(100.0, 100.0, "C")
	first.atom_model._chem_atom.id = "a1"
	second.atom_model._chem_atom.id = "a2"
	first.atom_model.bind_backend_durable_id("a1")
	second.atom_model.bind_backend_durable_id("a2")
	first.atom_model._molecule_model.mol_id = "m1"
	first.setSelected(True)
	second.setSelected(True)
	return first, second


#============================================
class _Receiver:
	"""Record the immutable request without owning a Qt geometry mutation."""

	#============================================
	def __init__(self) -> None:
		"""Record one explicit axis-and-target session-client call."""
		self.request = None

	#============================================
	def submit(self, axis: str, targets: tuple[tuple[str, str], ...]) -> object:
		"""Record the Qt-safe data and return the normal success shape."""
		self.request = (axis, targets)
		return bkchem_qt.models.document_session.PersistentActionOutcome(
			"accepted", "Align Selected Atoms accepted", None, True,
		)


#============================================
def test_bondalign_click_submits_immutable_request_without_qt_undo(main_window: object) -> None:
	"""Horizontal mode sends durable atom targets without a local transform command."""
	first, second = _selected_atoms(main_window)
	main_window._mode_manager.set_mode("bondalign")
	mode = main_window._mode_manager.current_mode
	receiver = _Receiver()
	mode.set_atom_align_operation(receiver.submit)
	undo_count = main_window.document.undo_stack.count()
	mode.mouse_press(PySide6.QtCore.QPointF(), object())

	assert receiver.request[0] == "horizontal"
	assert frozenset(receiver.request[1]) == {("m1", "a1"), ("m1", "a2")}
	assert (first.atom_model.y, second.atom_model.y, main_window.document.undo_stack.count()) == (0.0, 100.0, undo_count)


#============================================
def test_bondalign_submode_and_idless_atom_do_not_partially_commit(main_window: object) -> None:
	"""Vertical YAML selection is exact and an ID-less atom blocks the whole request."""
	first, second = _selected_atoms(main_window)
	main_window._mode_manager.set_mode("bondalign")
	mode = main_window._mode_manager.current_mode
	receiver = _Receiver()
	mode.set_atom_align_operation(receiver.submit)
	mode.set_submode("tovert")
	second.atom_model.bind_backend_durable_id(None)
	mode.mouse_press(PySide6.QtCore.QPointF(), object())

	assert mode._axis == "vertical" and receiver.request is None
	assert (first.atom_model.y, second.atom_model.y) == (0.0, 100.0)
