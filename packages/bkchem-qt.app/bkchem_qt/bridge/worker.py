"""QThread workers for async OASA operations."""

# PIP3 modules
import PySide6.QtCore


#============================================
class OasaWorker(PySide6.QtCore.QThread):
	"""Generic worker thread for running OASA operations off the main thread.

	Wraps any callable and executes it in a background thread. Emits
	``finished`` with the result on success, or ``error`` with a message
	if an exception is raised. The ``progress`` signal is available for
	callables that report progress, though the default callable does not
	use it.

	Args:
		func: The callable to execute in the background thread.
		*args: Positional arguments passed to func.
		**kwargs: Keyword arguments passed to func.
	"""

	# emitted with the return value of the callable on success
	finished = PySide6.QtCore.Signal(object)
	# emitted with the error message string on failure
	error = PySide6.QtCore.Signal(str)
	# emitted with an integer 0-100 for progress reporting
	progress = PySide6.QtCore.Signal(int)

	#============================================
	def __init__(self, func, *args, **kwargs):
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

	#============================================
	def run(self) -> None:
		"""Execute the callable in the worker thread.

		Calls the stored function with its arguments. On success, emits
		``finished`` with the return value. On exception, emits ``error``
		with the exception message string.
		"""
		try:
			result = self._func(*self._args, **self._kwargs)
			self.finished.emit(result)
		except Exception as exc:
			self.error.emit(str(exc))


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
	def __init__(self, mol, bond_length: float = 1.0, force: int = 1):
		"""Initialize the coordinate generator worker.

		Args:
			mol: OASA molecule object.
			bond_length: Target average bond length.
			force: 0 to skip if coords exist, 1 to regenerate.
		"""
		super().__init__(_generate_coords, mol, bond_length, force)


#============================================
def _generate_coords(mol, bond_length: float, force: int):
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
class FileReaderWorker(OasaWorker):
	"""Worker for reading chemistry files via OASA codecs.

	Runs the codec file reading in a background thread so that
	large files do not block the GUI event loop.

	Args:
		codec_name: OASA codec name (e.g. 'molfile', 'smiles').
		file_path: Path to the file to read.
	"""

	#============================================
	def __init__(self, codec_name: str, file_path: str):
		"""Initialize the file reader worker.

		Args:
			codec_name: OASA codec name string.
			file_path: Path to the chemistry file.
		"""
		super().__init__(_read_file, codec_name, file_path)


#============================================
def _read_file(codec_name: str, file_path: str):
	"""Read a chemistry file using an OASA codec.

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
