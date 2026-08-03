"""QThread workers for async OASA operations."""

# Standard Library
import dataclasses
import enum

# PIP3 modules
import PySide6.QtCore


class WorkerLifecycleState(enum.StrEnum):
	"""Observable frontend lifetime state for one native worker."""

	RUNNING = "running"
	DELIVERY_INVALIDATED = "delivery-invalidated"
	RETIRING = "retiring"
	FINISHED = "finished"


class WorkerTerminalOutcome(enum.StrEnum):
	"""Terminal delivery outcome after the native callable returns."""

	COMPLETED = "completed"
	FAILED = "failed"
	DELIVERY_CANCELLED = "delivery-cancelled"


#============================================
class OasaWorker(PySide6.QtCore.QThread):
	"""Generic worker thread for running OASA operations off the main thread.

	Wraps any callable and executes it in a background thread. Emits
	``result`` with the result on success, or ``error`` with a message
	if an exception is raised. The ``progress`` signal is available for
	callables that report progress, though the default callable does not
	use it.

	Args:
		func: The callable to execute in the background thread.
		*args: Positional arguments passed to func.
		**kwargs: Keyword arguments passed to func.
	"""

	# emitted with the return value of the callable on success
	result = PySide6.QtCore.Signal(object)
	# emitted with an error string, or structured text-preparation error
	error = PySide6.QtCore.Signal(object)
	# emitted with an integer 0-100 for progress reporting
	progress = PySide6.QtCore.Signal(int)
	# Emitted after the callable has returned and before QThread.finished.
	terminal_outcome = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, func: object, *args: object, **kwargs: object) -> None:
		"""Initialize the worker with a callable and its arguments.

		Args:
			func: The callable to execute.
			*args: Positional arguments for func.
			**kwargs: Keyword arguments for func.
		"""
		super().__init__()
		self._func = func
		self._args = args
		self._kwargs = kwargs
		self._lifecycle_state = WorkerLifecycleState.RUNNING
		self._terminal_outcome = None
		self._delivery_invalidated = False
		self.finished.connect(self._on_thread_finished)

	#============================================
	@property
	def lifecycle_state(self) -> WorkerLifecycleState:
		"""Return this worker's current frontend lifecycle state."""
		return self._lifecycle_state

	#============================================
	@property
	def outcome(self) -> WorkerTerminalOutcome | None:
		"""Return the terminal delivery outcome after native work completes."""
		return self._terminal_outcome

	#============================================
	def requestInterruption(self) -> None:
		"""Invalidate future delivery without claiming to preempt native work."""
		self._delivery_invalidated = True
		if self._lifecycle_state is WorkerLifecycleState.RUNNING:
			self._lifecycle_state = WorkerLifecycleState.DELIVERY_INVALIDATED
		super().requestInterruption()

	#============================================
	@PySide6.QtCore.Slot()
	def _on_thread_finished(self) -> None:
		"""Publish the terminal lifetime state at Qt's finished boundary."""
		self._lifecycle_state = WorkerLifecycleState.FINISHED

	#============================================
	def run(self) -> None:
		"""Execute the callable in the worker thread.

		Calls the stored function with its arguments. On success, emits
		``result`` with the return value. Native ``QThread.finished`` remains
		the separate lifetime signal. On exception, emits ``error`` with the
		exception message string.  Interactive text preparation errors retain
		their stage so the GUI can preserve parser-specific dialog labels.
		"""
		try:
			result = self._func(*self._args, **self._kwargs)
		except Exception as exc:
			if self._delivery_invalidated or self.isInterruptionRequested():
				outcome = WorkerTerminalOutcome.DELIVERY_CANCELLED
			else:
				outcome = WorkerTerminalOutcome.FAILED
				if isinstance(exc, TextImportPreparationError):
					self.error.emit(exc)
				else:
					self.error.emit(str(exc))
		else:
			if self._delivery_invalidated or self.isInterruptionRequested():
				outcome = WorkerTerminalOutcome.DELIVERY_CANCELLED
			else:
				outcome = WorkerTerminalOutcome.COMPLETED
				self.result.emit(result)
		self._terminal_outcome = outcome
		self._lifecycle_state = WorkerLifecycleState.RETIRING
		self.terminal_outcome.emit(outcome)


#============================================
class CoordGeneratorWorker(OasaWorker):
	"""Worker for coordinate generation via OASA.

	Runs ``coords_generator.calculate_coords()`` in a background thread
	so that expensive RDKit coordinate generation does not block the GUI.

	Args:
		mol: OASA molecule to generate coordinates for.
		bond_length: Target bond length (default 1.0).
		force: Force regeneration flag (default 1).
	"""

	#============================================
	def __init__(self, mol: object, bond_length: float = 1.0,
			force: int = 1) -> None:
		"""Initialize the coordinate generator worker.

		Args:
			mol: OASA molecule object.
			bond_length: Target average bond length.
			force: 0 to skip if coords exist, 1 to regenerate.
		"""
		super().__init__(_generate_coords, mol, bond_length, force)


#============================================
def _generate_coords(mol: object, bond_length: float, force: int) -> object:
	"""Generate 2D coordinates for an OASA molecule.

	Args:
		mol: OASA molecule object to modify in place.
		bond_length: Target average bond length.
		force: Force regeneration flag.

	Returns:
		The molecule with updated coordinates.
	"""
	import oasa.coords_generator
	oasa.coords_generator.calculate_coords(mol, bond_length=bond_length, force=force)
	return mol


#============================================
class FileImportWorker(OasaWorker):
	"""Worker that parses and prepares an imported chemistry source.

	Coordinate generation, complete-document serialization, and strict backend
	validation are OASA work, so they remain off the GUI thread.  The result is
	a frozen plain CDML value; it never carries an OASA graph into Qt.

	Args:
		codec_name: OASA codec name (e.g. ``molfile`` or ``smiles``).
		file_path: Path to the file to import.
	"""

	#============================================
	def __init__(
			self, codec_name: str, file_path: str,
			) -> None:
		"""Initialize a complete chemistry import worker.

		File codecs retain their established complete-document replacement route.
		Interactive text inputs use :class:`TextMoleculeInsertionWorker` so they
		produce a bounded proposal for an existing authoritative session.
		"""
		super().__init__(_read_and_prepare_import, codec_name, file_path)


#============================================
def _read_file(codec_name: str, file_path: str) -> object:
	"""Read one chemistry file inside complete-CDML import preparation.

	Args:
		codec_name: OASA codec name string.
		file_path: Path to the chemistry file.

	Returns:
		OASA molecule parsed from the file.
	"""
	import oasa.codec_registry
	codec = oasa.codec_registry.get_codec(codec_name)
	with open(file_path, "r") as f:
		mol = codec.read_file(f)
	return mol


#============================================
def _read_and_prepare_import(codec_name: str, file_path: str) -> "PreparedCompleteCDML | None":
	"""Parse an import and return one backend-valid complete CDML document.

	Args:
		codec_name: OASA codec name string.
		file_path: Path to the chemistry file.

	Returns:
		Frozen serializable complete-CDML value, or ``None`` for no molecules.
	"""
	mol = _read_file(codec_name, file_path)
	if mol is None:
		return None
	from oasa import coords_generator
	coords_generator.calculate_coords(mol, bond_length=1.0, force=0)
	if mol.is_connected():
		molecules = [mol]
	else:
		molecules = list(mol.get_disconnected_subgraphs())
	from oasa import cdml_document, cdml_writer
	complete_cdml = cdml_writer.molecules_to_complete_document(molecules)
	canonical_cdml = cdml_document.CDMLDocument.parse(
		complete_cdml, validation="strict",
	).serialize()
	prepared = PreparedCompleteCDML(canonical_cdml, file_path)
	return prepared


#============================================
class TextImportPreparationError(ValueError):
	"""Describe the user-facing stage that failed preparing text import.

	Args:
		stage: Stable preparation stage identifier for a GUI error mapper.
		message: Exception text safe to present to the user.
	"""

	#============================================
	def __init__(self, stage: str, message: str) -> None:
		"""Store a stage and its explanatory error text."""
		super().__init__(message)
		self.stage = stage


@dataclasses.dataclass(frozen=True)
class PreparedMoleculeInsertion:
	"""Immutable plain proposal ready for one backend molecule insertion."""

	proposal_cdml: str
	expected_revision: int
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class PreparedCompleteCDML:
	"""Immutable backend-valid document replacement from one external path."""

	complete_cdml: str
	source_label: str


#============================================
class TextMoleculeInsertionWorker(OasaWorker):
	"""Prepare one text-derived molecule proposal off the GUI thread.

	The worker boundary carries only scalar source text and immutable proposal
	data.  It is shared by the interactive SMILES, InChI, and peptide actions;
	Qt models are deliberately not part of the result.
	"""

	#============================================
	def __init__(
			self, codec_name: str, source_text: str, expected_revision: int,
			token_stem: str, target_mean_bond_length: float,
			insertion_anchor: tuple[float, float], label: str,
			) -> None:
		"""Capture one complete plain-data insertion request."""
		super().__init__(
			_prepare_text_molecule_insertion,
			codec_name,
			source_text,
			expected_revision,
			token_stem,
			target_mean_bond_length,
			insertion_anchor,
			label,
		)


#============================================
def _prepare_text_molecule_insertion(
		codec_name: str, source_text: str, expected_revision: int, token_stem: str,
		target_mean_bond_length: float, insertion_anchor: tuple[float, float],
		label: str,
		) -> PreparedMoleculeInsertion:
	"""Return one positioned immutable proposal for a text chemistry route."""
	if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
		raise ValueError("Text insertion revision must be an integer")
	if not isinstance(label, str) or not label.strip():
		raise ValueError("Text insertion label must be non-empty text")
	molecules = _prepare_text_import(codec_name, source_text)
	try:
		from oasa import cdml_writer, insertion_geometry
		insertion_geometry.place_molecules_for_insertion(
			molecules, target_mean_bond_length, insertion_anchor,
		)
		proposal_cdml = cdml_writer.molecules_to_insertion_proposal(
			molecules, token_stem=token_stem,
		)
	except Exception as exc:
		raise TextImportPreparationError(codec_name, str(exc)) from exc
	prepared = PreparedMoleculeInsertion(proposal_cdml, expected_revision, label)
	return prepared


#============================================
def _prepare_text_import(codec_name: str, source_text: str) -> list:
	"""Prepare one supported interactive chemistry source off the GUI thread.

	The returned values are pure OASA components consumed immediately by the
	common plain-data proposal builder.  They never cross into a Qt model or
	local undo operation.

	Args:
		codec_name: ``smiles``, ``inchi``, or ``peptide`` text route.
		source_text: Dialog input to parse and position.

	Returns:
		Connected OASA molecule components with generated 2D coordinates.

	Raises:
		TextImportPreparationError: If a parser or coordinate preparation stage
			fails.  The stage preserves the dialog's error vocabulary.
	"""
	if codec_name == "smiles":
		try:
			from oasa import smiles_lib
			mol = smiles_lib.text_to_mol(source_text)
		except Exception as exc:
			raise TextImportPreparationError("smiles", str(exc)) from exc
	elif codec_name == "inchi":
		try:
			from oasa import inchi_lib
			mol = inchi_lib.text_to_mol(source_text)
		except Exception as exc:
			raise TextImportPreparationError("inchi", str(exc)) from exc
	elif codec_name == "peptide":
		mol = _prepare_peptide_molecule(source_text)
	else:
		raise ValueError("Unsupported text import codec: %s" % codec_name)
	try:
		from oasa import coords_generator
		coords_generator.calculate_coords(mol, bond_length=1.0, force=1)
	except Exception as exc:
		raise TextImportPreparationError("coordinates", str(exc)) from exc
	if mol.is_connected():
		return [mol]
	return list(mol.get_disconnected_subgraphs())


#============================================
def _prepare_peptide_molecule(sequence_text: str) -> object:
	"""Validate one peptide sequence and turn it into pure OASA chemistry."""
	from oasa import peptide_utils
	sequence = sequence_text.strip().upper()
	supported = tuple(sorted(peptide_utils.AMINO_ACID_SMILES))
	bad_letters = sorted({
		letter for letter in sequence
		if letter not in peptide_utils.AMINO_ACID_SMILES
	})
	if bad_letters:
		raise TextImportPreparationError(
			"peptide-validation",
			"Unrecognized amino acid code(s): %s\nSupported: %s" % (
				", ".join(bad_letters), ", ".join(supported),
			),
		)
	try:
		smiles_text = peptide_utils.sequence_to_smiles(sequence)
	except ValueError as exc:
		raise TextImportPreparationError("peptide", str(exc)) from exc
	try:
		from oasa import smiles_lib
		return smiles_lib.text_to_mol(smiles_text)
	except Exception as exc:
		raise TextImportPreparationError("peptide-smiles", str(exc)) from exc
