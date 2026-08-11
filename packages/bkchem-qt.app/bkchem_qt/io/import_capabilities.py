"""Truthful file-import capabilities for the PySide6 application.

This registry is deliberately narrower than the OASA codec registry.  It
contains only native CDML and codecs that the Qt ``FileImportWorker`` can
turn into backend-owned document sessions today. Do not add a format merely
because OASA can write it or because the legacy Tk application listed it.
"""

# Standard Library
import dataclasses

# local repo modules
import oasa.codec_registry


@dataclasses.dataclass(frozen=True)
class ImportCapability:
	"""One file format the Qt application can truthfully open."""

	codec_name: str
	extensions: tuple[str, ...]
	label: str
	description: str
	route: str


# Keep this conservative until each additional codec has a Qt session test.
# CDML is a native document route, while every other entry is parsed by the
# session-owned FileImportWorker.
_IMPORT_CAPABILITIES = (
	ImportCapability(
		codec_name="cdml",
		extensions=(".cdml",),
		label="BKChem CDML",
		description="BKChem native document",
		route="native",
	),
	ImportCapability(
		codec_name="cdsvg",
		extensions=(".svg", ".svgz", ".cdsvg"),
		label="BKChem CD-SVG",
		description="SVG with embedded editable BKChem CDML",
		route="worker",
	),
	ImportCapability(
		codec_name="molfile",
		extensions=(".mol",),
		label="MDL Molfile",
		description="MDL Molfile (V2000/V3000)",
		route="worker",
	),
	ImportCapability(
		codec_name="sdf",
		extensions=(".sdf",),
		label="Structure Data File",
		description="Structure-Data File",
		route="worker",
	),
	ImportCapability(
		codec_name="smiles",
		extensions=(".smi", ".smiles"),
		label="SMILES",
		description="SMILES structure",
		route="worker",
	),
	ImportCapability(
		codec_name="cdxml",
		extensions=(".cdxml",),
		label="ChemDraw XML",
		description="ChemDraw XML molecule",
		route="worker",
	),
	ImportCapability(
		codec_name="cml",
		extensions=(".cml",),
		label="Chemical Markup Language",
		description="CML molecule",
		route="worker",
	),
)


#============================================
def all_import_capabilities() -> tuple[ImportCapability, ...]:
	"""Return every format accepted by the Qt Open dialog."""
	_validate_capabilities()
	return _IMPORT_CAPABILITIES


#============================================
def worker_import_capabilities() -> tuple[ImportCapability, ...]:
	"""Return the non-native formats shown in File > Import."""
	_validate_capabilities()
	return tuple(
		capability for capability in _IMPORT_CAPABILITIES
		if capability.route == "worker"
	)


#============================================
def capability_for_extension(extension: str) -> ImportCapability:
	"""Resolve an advertised extension or fail clearly.

	Args:
		extension: A filename extension, with or without a leading dot.

	Returns:
		The matching Qt import capability.

	Raises:
		ValueError: If the extension is not advertised by the Qt application.
	"""
	normalized = _normalize_extension(extension)
	for capability in all_import_capabilities():
		if normalized in capability.extensions:
			return capability
	raise ValueError(
		"Unsupported chemistry import extension: %s" % (normalized or extension)
	)


#============================================
def chemistry_file_filter() -> str:
	"""Build the QFileDialog filter from the same advertised capabilities."""
	capabilities = all_import_capabilities()
	all_patterns = " ".join(
		_pattern(extension) for capability in capabilities
		for extension in capability.extensions
	)
	sections = ["Chemistry Files (%s)" % all_patterns]
	for capability in capabilities:
		patterns = " ".join(_pattern(extension) for extension in capability.extensions)
		sections.append("%s (%s)" % (capability.label, patterns))
	sections.append("All Files (*)")
	return ";;".join(sections)


#============================================
def capability_file_filter(capability: ImportCapability) -> str:
	"""Build the chooser filter for a single Import cascade item."""
	_validate_capability(capability)
	patterns = " ".join(_pattern(extension) for extension in capability.extensions)
	return "%s (%s);;All Files (*)" % (capability.label, patterns)


#============================================
def _normalize_extension(extension: str) -> str:
	"""Return one normalized dotted extension."""
	result = extension.strip().lower()
	if result and not result.startswith("."):
		return "." + result
	return result


#============================================
def _pattern(extension: str) -> str:
	"""Convert one normalized extension to a Qt file-dialog glob."""
	return "*%s" % extension


#============================================
def _validate_capabilities() -> None:
	"""Ensure every advertised worker format has a readable OASA codec."""
	for capability in _IMPORT_CAPABILITIES:
		_validate_capability(capability)


#============================================
def _validate_capability(capability: ImportCapability) -> None:
	"""Validate a capability before it is shown to the user."""
	if capability.route not in ("native", "worker"):
		raise RuntimeError(
			"Qt import capability '%s' has invalid route '%s'." % (
				capability.codec_name, capability.route,
			)
		)
	if not capability.extensions:
		raise RuntimeError(
			"Qt import capability '%s' has no file extension."
			% capability.codec_name
		)
	codec = oasa.codec_registry.get_codec(capability.codec_name)
	if not codec.reads_files and not codec.reads_documents:
		raise RuntimeError(
			"Qt import capability '%s' has no readable OASA import codec."
			% capability.codec_name
		)
	for extension in capability.extensions:
		try:
			extension_codec = oasa.codec_registry.get_import_codec_by_extension(
				extension,
			)
		except KeyError as exc:
			raise RuntimeError(
				"Qt import capability '%s' advertises unresolved extension '%s'."
				% (capability.codec_name, extension)
			) from exc
		if extension_codec.name != capability.codec_name:
			raise RuntimeError(
				"Qt import extension '%s' resolves to '%s', not '%s'."
				% (extension, extension_codec.name, capability.codec_name)
			)
