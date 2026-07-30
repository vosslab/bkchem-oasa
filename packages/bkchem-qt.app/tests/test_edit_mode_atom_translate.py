"""Focused EditMode routing checks for backend-authoritative atom nudging."""

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.models.document_object
import bkchem_qt.models.document_session
import bkchem_qt.undo.commands


#============================================
class _Receiver:
	"""Record a session-owned atom translation without a local model mutation."""

	#============================================
	def __init__(self) -> None:
		"""Create an empty operation receipt."""
		self.request = None

	#============================================
	def submit(self, targets: tuple[tuple[str, str], ...], delta: tuple[float, float]) -> object:
		"""Capture the plain immutable request and return the normal outcome shape."""
		self.request = targets, delta
		return bkchem_qt.models.document_session.PersistentActionOutcome(
			"accepted", "Nudge Selected Atoms accepted", None, True,
		)


#============================================
def _durable_atom(main_window: object, identifier: str) -> object:
	"""Create one selectable atom with its projected durable address."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	atom = draw_mode._create_atom_at(20.0, 20.0, "C")
	atom.atom_model._chem_atom.id = identifier
	atom.atom_model.bind_backend_durable_id(identifier)
	atom.atom_model._molecule_model.mol_id = "m1"
	return atom


#============================================
def _presentation(main_window: object) -> object:
	"""Create one selected non-atom item that an atom nudge must ignore."""
	model = bkchem_qt.models.document_object.PresentationObject(
		"polyline", attributes={"id": "line1"}, points=[(40.0, 20.0, None), (70.0, 20.0, None)],
	)
	item = bkchem_qt.canvas.document_projection.create_presentation_item(model)
	main_window.document.undo_stack.push(
		bkchem_qt.undo.commands.AddPresentationObjectCommand(
			main_window.document, main_window.scene, model, item,
		),
	)
	return item


#============================================
def test_edit_mode_nudge_ignores_selected_presentation_items(main_window: object) -> None:
	"""Mixed selection sends only atoms and does not create local undo history."""
	atom = _durable_atom(main_window, "a1")
	presentation = _presentation(main_window)
	main_window._mode_manager.set_mode("edit")
	mode = main_window._mode_manager.current_mode
	receiver = _Receiver()
	mode.set_atom_translate_operation(receiver.submit)
	atom.setSelected(True)
	presentation.setSelected(True)
	undo_count = main_window.document.undo_stack.count()
	mode._nudge_selected(2.0, 0.0)

	assert receiver.request == ((("m1", "a1"),), (2.0, 0.0))
	assert (atom.atom_model.x, main_window.document.undo_stack.count()) == (20.0, undo_count)


#============================================
def test_edit_mode_idless_atom_makes_the_complete_nudge_inert(main_window: object) -> None:
	"""One unaddressable selected atom blocks every atom in the gesture."""
	first = _durable_atom(main_window, "a1")
	second = _durable_atom(main_window, "a2")
	second.atom_model.bind_backend_durable_id(None)
	main_window._mode_manager.set_mode("edit")
	mode = main_window._mode_manager.current_mode
	receiver = _Receiver()
	mode.set_atom_translate_operation(receiver.submit)
	first.setSelected(True)
	second.setSelected(True)
	mode._nudge_selected(2.0, 0.0)

	assert receiver.request is None
	assert (first.atom_model.x, second.atom_model.x) == (20.0, 20.0)
