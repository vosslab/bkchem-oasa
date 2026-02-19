#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#--------------------------------------------------------------------------

"""Registry-backed format loader for BKChem import/export menus."""

# Standard Library
import io
import os

# Third Party
import yaml

# local repo modules
from bkchem import oasa_bridge

from bkchem.singleton_store import Store


_ALLOWED_TOP_LEVEL_KEYS = {"formats"}
_ALLOWED_FORMAT_KEYS = {
	"display_name",
	"menu_capabilities",
	"scope",
	"gui_options",
}
_ALLOWED_OPTION_KEYS = {
	"key",
	"source",
	"preference_key",
	"property_key",
	"dialog_type",
	"required",
}
_ALLOWED_MENU_CAPABILITIES = {"import", "export"}
_ALLOWED_SCOPES = {"paper", "selected_molecule"}
_ALLOWED_OPTION_SOURCES = {"preference", "paper_property", "dialog"}


#============================================
def _manifest_path():
	return os.path.join(os.path.dirname(__file__), "format_menus.yaml")


#============================================
def load_backend_capabilities():
	"""Return registry capabilities keyed by codec name."""
	if not oasa_bridge.oasa_available:
		return {}
	return oasa_bridge.oasa.codec_registry.get_registry_snapshot()


#============================================
def _validate_gui_option(codec_name, option):
	if not isinstance(option, dict):
		raise ValueError(f"Format '{codec_name}' has a non-mapping gui option.")
	unknown = set(option.keys()) - _ALLOWED_OPTION_KEYS
	if unknown:
		joined = ", ".join(sorted(unknown))
		raise ValueError(f"Format '{codec_name}' has unknown gui option keys: {joined}")
	for required_key in ("key", "source"):
		if required_key not in option:
			raise ValueError(f"Format '{codec_name}' gui option is missing '{required_key}'.")
	source = option["source"]
	if source not in _ALLOWED_OPTION_SOURCES:
		raise ValueError(f"Format '{codec_name}' has unsupported gui option source '{source}'.")
	if source == "preference" and "preference_key" not in option:
		raise ValueError(f"Format '{codec_name}' preference option is missing 'preference_key'.")
	if source == "paper_property" and "property_key" not in option:
		raise ValueError(f"Format '{codec_name}' paper_property option is missing 'property_key'.")
	if source == "dialog" and "dialog_type" not in option:
		raise ValueError(f"Format '{codec_name}' dialog option is missing 'dialog_type'.")


#============================================
def load_gui_manifest(path=None):
	"""Load and validate GUI format metadata."""
	manifest_path = path or _manifest_path()
	with open(manifest_path, "r", encoding="utf-8") as handle:
		manifest = yaml.safe_load(handle) or {}
	if not isinstance(manifest, dict):
		raise ValueError("format_menus.yaml must contain a top-level mapping.")
	unknown_top_level = set(manifest.keys()) - _ALLOWED_TOP_LEVEL_KEYS
	if unknown_top_level:
		joined = ", ".join(sorted(unknown_top_level))
		raise ValueError(f"format_menus.yaml has unknown top-level keys: {joined}")
	formats = manifest.get("formats", {})
	if not isinstance(formats, dict):
		raise ValueError("format_menus.yaml 'formats' must be a mapping.")
	for codec_name, cfg in sorted(formats.items()):
		if not isinstance(cfg, dict):
			raise ValueError(f"Format '{codec_name}' config must be a mapping.")
		unknown = set(cfg.keys()) - _ALLOWED_FORMAT_KEYS
		if unknown:
			joined = ", ".join(sorted(unknown))
			raise ValueError(f"Format '{codec_name}' has unknown keys: {joined}")
		capabilities = cfg.get("menu_capabilities", [])
		if capabilities:
			if not isinstance(capabilities, list):
				raise ValueError(f"Format '{codec_name}' menu_capabilities must be a list.")
			for capability in capabilities:
				if capability not in _ALLOWED_MENU_CAPABILITIES:
					raise ValueError(
						f"Format '{codec_name}' has unsupported capability '{capability}'."
					)
		scope = cfg.get("scope", "paper")
		if scope not in _ALLOWED_SCOPES:
			raise ValueError(f"Format '{codec_name}' has unsupported scope '{scope}'.")
		options = cfg.get("gui_options", [])
		if not isinstance(options, list):
			raise ValueError(f"Format '{codec_name}' gui_options must be a list.")
		for option in options:
			_validate_gui_option(codec_name, option)
	return formats


#============================================
def load_format_entries():
	"""Join GUI metadata with registry capabilities."""
	backend = load_backend_capabilities()
	gui_formats = load_gui_manifest()
	entries = {}
	for codec_name, gui in sorted(gui_formats.items()):
		if codec_name not in backend:
			raise ValueError(f"Format '{codec_name}' is missing in OASA registry snapshot.")
		caps = backend[codec_name]
		menu_capabilities = gui.get("menu_capabilities", [])
		if not menu_capabilities:
			menu_capabilities = []
			if caps["reads_files"] or caps["reads_text"]:
				menu_capabilities.append("import")
			if caps["writes_files"] or caps["writes_text"]:
				menu_capabilities.append("export")
		can_import = "import" in menu_capabilities and (caps["reads_files"] or caps["reads_text"])
		can_export = "export" in menu_capabilities and (caps["writes_files"] or caps["writes_text"])
		entries[codec_name] = {
			"name": codec_name,
			"display_name": gui.get("display_name", codec_name),
			"menu_capabilities": list(menu_capabilities),
			"scope": gui.get("scope", "paper"),
			"gui_options": list(gui.get("gui_options", [])),
			"extensions": list(caps.get("extensions", [])),
			"can_import": can_import,
			"can_export": can_export,
		}
	return entries


#============================================
def resolve_gui_kwargs(paper, gui_options):
	"""Resolve GUI option values from their declared sources."""
	kwargs = {}
	for option in gui_options:
		key = option["key"]
		source = option["source"]
		required = bool(option.get("required"))
		value = None
		if source == "preference":
			if Store.pm:
				value = Store.pm.get_preference(option["preference_key"])
		elif source == "paper_property":
			value = paper.get_paper_property(option["property_key"])
		elif source == "dialog":
			raise ValueError(f"Dialog option source is not implemented for '{key}'.")
		if value in (None, ""):
			if required:
				raise ValueError(f"Missing required option '{key}'.")
			continue
		kwargs[key] = value
	return kwargs


#============================================
def _write_text_output(handle, text):
	if text and not text.endswith("\n"):
		text = text + "\n"
	data = text or ""
	if isinstance(handle, io.TextIOBase):
		handle.write(data)
	else:
		handle.write(data.encode("utf-8"))


#============================================
def import_format(codec_name, paper, filename):
	"""Import one file via oasa_bridge and return BKChem molecules."""
	with open(filename, "r") as handle:
		return oasa_bridge.read_codec_file(codec_name, handle, paper)


#============================================
def export_format(codec_name, paper, filename, scope, gui_options):
	"""Export one file via oasa_bridge using scope and resolved GUI options."""
	kwargs = resolve_gui_kwargs(paper, gui_options)
	with open(filename, "wb") as handle:
		if scope == "selected_molecule":
			mol = oasa_bridge.validate_selected_molecule(paper)
			# Bridge still returns preformatted text for SMILES/InChI instead of
			# exposing these via the generic codec write_file interface.
			if codec_name == "smiles":
				_write_text_output(handle, oasa_bridge.mol_to_smiles(mol))
				return
			if codec_name == "inchi":
				inchi, key, warnings = oasa_bridge.mol_to_inchi(
					mol,
					kwargs.get("program_path"),
				)
				lines = []
				if inchi:
					lines.append(inchi)
				if key:
					lines.append("InChIKey=" + key)
				if warnings:
					lines.extend(["# " + warning for warning in warnings])
				if lines:
					_write_text_output(handle, "\n".join(lines))
				return
			oasa_bridge.write_codec_file_from_selected_molecule(
				codec_name,
				paper,
				handle,
				**kwargs,
			)
			return
		oasa_bridge.write_codec_file_from_paper(codec_name, paper, handle, **kwargs)
