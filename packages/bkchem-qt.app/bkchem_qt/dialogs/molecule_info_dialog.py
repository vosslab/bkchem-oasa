"""Read-only molecular composition details from authoritative OASA facts."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
def _composition_text(chemistry: object) -> str:
	"""Format backend mass fractions without recalculating chemistry in Qt."""
	return ", ".join(
		"%s: %.3f%%" % (symbol, percentage)
		for symbol, percentage in chemistry.mass_percentages
	)


#============================================
def _chemistry_lines(chemistry: object) -> list[str]:
	"""Return consistent formula and mass presentation lines."""
	return [
		"Formula: %s" % chemistry.formula,
		"Average molecular weight: %.4f" % chemistry.molecular_weight,
		"Monoisotopic mass: %.8f" % chemistry.monoisotopic_mass,
		"Composition by mass: %s" % _composition_text(chemistry),
	]


#============================================
def format_molecule_summary(observation: object) -> str:
	"""Format one immutable backend observation for selectable display."""
	lines = []
	if len(observation.records) > 1:
		lines.extend(("Individual molecules", "====================", ""))
	for index, record in enumerate(observation.records):
		lines.extend((
			"Name: %s" % (record.name or "(unnamed)"),
			"ID: %s" % record.molecule_id,
			"Chemistry graph: %d atom%s, %d bond%s" % (
				record.atom_count, "" if record.atom_count == 1 else "s",
				record.bond_count, "" if record.bond_count == 1 else "s",
			),
			*_chemistry_lines(record.chemistry),
		))
		if index + 1 < len(observation.records):
			lines.extend(("", "--------------------", ""))
	if len(observation.records) > 1:
		lines.extend((
			"", "Combined selection", "==================", "",
			*_chemistry_lines(observation.aggregate),
		))
	return "\n".join(lines)


#============================================
class MoleculeInfoDialog(PySide6.QtWidgets.QDialog):
	"""Show selectable molecular facts without exposing mutable graph objects."""

	#============================================
	def __init__(
			self, observation: object,
			parent: PySide6.QtWidgets.QWidget | None = None,
			) -> None:
		"""Build a focused read-only details surface."""
		super().__init__(parent)
		self.setWindowTitle("Molecule Information")
		self.setMinimumSize(600, 420)
		self.resize(640, 520)
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		intro = PySide6.QtWidgets.QLabel(
			"Calculated by OASA from document revision %d. "
			"Implicit hydrogens are included." % observation.revision,
		)
		intro.setWordWrap(True)
		layout.addWidget(intro)
		self._details = PySide6.QtWidgets.QPlainTextEdit(
			format_molecule_summary(observation),
		)
		self._details.setReadOnly(True)
		self._details.setFont(
			PySide6.QtGui.QFontDatabase.systemFont(
				PySide6.QtGui.QFontDatabase.SystemFont.FixedFont,
			),
		)
		self._details.setAccessibleName("Molecule chemistry details")
		self._details.setAccessibleDescription(
			"Selectable OASA formula, mass, and elemental composition results.",
		)
		layout.addWidget(self._details, 1)
		buttons = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Close,
		)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

	#============================================
	@property
	def details_text(self) -> str:
		"""Return the exact visible details for behavior tests and copying."""
		return self._details.toPlainText()
