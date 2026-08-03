"""Focused plain-data behavior checks for UserTemplateMode."""

# Standard Library
import dataclasses

# PIP3 modules
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.modes.user_template_mode


@dataclasses.dataclass(frozen=True)
class _Descriptor:
	"""Plain descriptor whose payload must remain outside the mode boundary."""

	catalog_key: str
	label: str

	@property
	def template_cdml(self) -> str:
		"""Reject accidental descriptor-payload access from the projection mode."""
		raise RuntimeError("UserTemplateMode must not read template CDML")


@dataclasses.dataclass(frozen=True)
class _Outcome:
	"""Minimal session-owned placement result."""

	message: str


#============================================
def _mode(
		qapp: object, catalog: tuple[object, ...] = (),
		) -> bkchem_qt.modes.user_template_mode.UserTemplateMode:
	"""Create a QObject-owned mode without graphics wrappers."""
	mode = bkchem_qt.modes.user_template_mode.UserTemplateMode(
		object(), parent=qapp, catalog=catalog,
	)
	return mode


#============================================
def test_descriptor_projection_submits_only_selected_plain_intent(qapp: object) -> None:
	"""A mode can place a selected descriptor without ever reading its CDML."""
	mode = _mode(qapp, (_Descriptor("one", "One"), _Descriptor("two", "Two")))
	intent = {"key": None, "anchor": None}

	def submit(key: str, anchor: tuple[float, float]) -> _Outcome:
		"""Keep the latest plain intent at the session boundary."""
		intent["key"] = key
		intent["anchor"] = anchor
		return _Outcome("Inserted")

	mode.set_user_template_action(submit)
	mode.on_submode_switch(0, "two")
	mode.mouse_press(PySide6.QtCore.QPointF(12.5, -3.0), None)

	assert intent == {"key": "two", "anchor": (12.5, -3.0)}


#============================================
def test_cleared_catalog_is_inert(qapp: object) -> None:
	"""Clearing the catalog leaves a raising session callback untouched."""
	mode = _mode(qapp, (_Descriptor("one", "One"),))
	status = {"message": None}

	def should_not_submit(_key: str, _anchor: tuple[float, float]) -> _Outcome:
		"""Expose an accidental persistent submission immediately."""
		raise RuntimeError("A cleared catalog must be inert")

	mode.status_message.connect(lambda message: status.__setitem__("message", message))
	mode.set_user_template_action(should_not_submit)
	mode.set_catalog(())
	mode.mouse_press(PySide6.QtCore.QPointF(10.0, 20.0), None)

	assert status["message"] == "No user templates available"


#============================================
def test_catalog_replacement_retains_explicit_selection(qapp: object) -> None:
	"""A selected key that survives replacement remains the submitted key."""
	mode = _mode(qapp, (_Descriptor("one", "One"), _Descriptor("two", "Two")))
	intent = {"key": None}

	def submit(key: str, _anchor: tuple[float, float]) -> _Outcome:
		"""Capture the current logical selection at submission time."""
		intent["key"] = key
		return _Outcome("Inserted")

	mode.set_user_template_action(submit)
	mode.on_submode_switch(0, "two")
	mode.set_catalog((_Descriptor("two", "Changed"), _Descriptor("three", "Three")))
	mode.mouse_press(PySide6.QtCore.QPointF(1.0, 2.0), None)

	assert intent["key"] == "two"


#============================================
@pytest.mark.parametrize(
	"catalog",
	(
		[_Descriptor("one", "One")],
		(_Descriptor("", "One"),),
		(_Descriptor("one", " "),),
		(_Descriptor("one", "One"), _Descriptor("one", "Again")),
	),
)
def test_invalid_catalog_is_rejected(qapp: object, catalog: object) -> None:
	"""Only immutable descriptors with unique nonblank keys and labels are valid."""
	with pytest.raises(ValueError):
		_mode(qapp, catalog)
