# SPDX-License-Identifier: LGPL-3.0-or-later
#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#--------------------------------------------------------------------------

"""Shared registry for OASA import/export codecs."""

# Standard Library
import io


_CODECS = {}
_ALIASES = {}
_EXTENSIONS = {}
_DEFAULTS_REGISTERED = False


class Codec(object):
	"""Container for codec metadata and helpers."""

	def __init__(
		self,
		name,
		module=None,
		extensions=None,
		description=None,
		text_to_mol=None,
		mol_to_text=None,
		file_to_mol=None,
		mol_to_file=None,
	):
		self.name = _normalize_name(name)
		if not self.name:
			raise ValueError("Codec name is required.")
		self.module = module
		self.description = description or ""
		self.extensions = _normalize_extensions(extensions)
		if module is not None:
			if text_to_mol is None:
				text_to_mol = getattr(module, "text_to_mol", None)
			if mol_to_text is None:
				mol_to_text = getattr(module, "mol_to_text", None)
			if file_to_mol is None:
				file_to_mol = getattr(module, "file_to_mol", None)
			if mol_to_file is None:
				mol_to_file = getattr(module, "mol_to_file", None)
		self.text_to_mol = text_to_mol
		self.mol_to_text = mol_to_text
		self.file_to_mol = file_to_mol
		self.mol_to_file = mol_to_file
		self.reads_text = bool(self.text_to_mol)
		self.writes_text = bool(self.mol_to_text)
		self.reads_files = bool(self.file_to_mol or self.text_to_mol)
		self.writes_files = bool(self.mol_to_file or self.mol_to_text)


	#============================================
	def read_text(self, text, **kwargs):
		if not self.text_to_mol:
			raise ValueError(f"Codec '{self.name}' does not support text input.")
		return self.text_to_mol(text, **kwargs)


	#============================================
	def read_file(self, file_obj, **kwargs):
		if self.file_to_mol:
			return self.file_to_mol(file_obj, **kwargs)
		if not self.text_to_mol:
			raise ValueError(f"Codec '{self.name}' does not support file input.")
		return self.text_to_mol(file_obj.read(), **kwargs)


	#============================================
	def write_text(self, mol, **kwargs):
		if not self.mol_to_text:
			raise ValueError(f"Codec '{self.name}' does not support text output.")
		return self.mol_to_text(mol, **kwargs)


	#============================================
	def write_file(self, mol, file_obj, **kwargs):
		if self.mol_to_file:
			return self.mol_to_file(mol, file_obj, **kwargs)
		if not self.mol_to_text:
			raise ValueError(f"Codec '{self.name}' does not support file output.")
		text = self.mol_to_text(mol, **kwargs)
		if isinstance(file_obj, io.TextIOBase):
			file_obj.write(text)
		else:
			file_obj.write(text.encode("utf-8"))


#============================================
def register_codec(codec, aliases=None, replace=False):
	name = _normalize_name(codec.name)
	if not name:
		raise ValueError("Codec name is required.")
	if not replace and name in _CODECS:
		raise ValueError(f"Codec '{name}' is already registered.")
	_CODECS[name] = codec
	for ext in codec.extensions:
		if not ext:
			continue
		if not replace and ext in _EXTENSIONS and _EXTENSIONS[ext] != name:
			raise ValueError(f"Extension '{ext}' is already registered.")
		_EXTENSIONS[ext] = name
	if aliases:
		for alias in aliases:
			register_alias(alias, name, replace=replace)
	return codec


#============================================
def register_alias(alias, name, replace=False):
	alias_key = _normalize_name(alias)
	name_key = _normalize_name(name)
	if not alias_key or not name_key:
		raise ValueError("Alias and codec name are required.")
	if not replace and alias_key in _ALIASES:
		raise ValueError(f"Alias '{alias_key}' is already registered.")
	_ALIASES[alias_key] = name_key


#============================================
def register_module_codec(name, module, extensions=None, description=None, aliases=None):
	codec = Codec(
		name=name,
		module=module,
		extensions=extensions,
		description=description,
	)
	return register_codec(codec, aliases=aliases)


#============================================
def reset_registry():
	global _DEFAULTS_REGISTERED
	_CODECS.clear()
	_ALIASES.clear()
	_EXTENSIONS.clear()
	_DEFAULTS_REGISTERED = False


#============================================
def _normalize_name(name):
	if not name:
		return ""
	return str(name).strip().lower()


#============================================
def _normalize_extension(ext):
	if not ext:
		return ""
	text = str(ext).strip().lower()
	if not text:
		return ""
	if not text.startswith("."):
		text = "." + text
	return text


#============================================
def _normalize_extensions(extensions):
	if not extensions:
		return []
	result = []
	for ext in extensions:
		normalized = _normalize_extension(ext)
		if normalized and normalized not in result:
			result.append(normalized)
	return result


#============================================
def _ensure_defaults_registered():
	global _DEFAULTS_REGISTERED
	if _DEFAULTS_REGISTERED:
		return
	from oasa import cdml
	from oasa import cdml_writer
	from oasa import inchi_lib as inchi
	from oasa import molfile_lib as molfile
	from oasa import smiles_lib as smiles
	from oasa.codecs import cdxml
	from oasa.codecs import cdsvg
	from oasa.codecs import cml
	from oasa.codecs import cml2
	from oasa.codecs import render

	register_module_codec(
		"smiles",
		smiles,
		extensions=[".smi", ".smiles"],
		aliases=["s"],
	)
	register_module_codec(
		"inchi",
		inchi,
		extensions=[".inchi", ".txt"],
		aliases=["i"],
	)
	register_module_codec(
		"molfile",
		molfile,
		extensions=[".mol"],
		aliases=["m"],
	)
	register_codec(
		Codec(
			name="cdml",
			text_to_mol=cdml.text_to_mol,
			mol_to_text=cdml_writer.mol_to_text,
			file_to_mol=cdml.file_to_mol,
			mol_to_file=cdml_writer.mol_to_file,
			extensions=[".cdml"],
		),
		aliases=["c"],
	)
	register_codec(
		Codec(
			name="cml",
			# Keep import-only by wiring read callables explicitly.
			# Do not switch to register_module_codec() for legacy CML codecs.
			text_to_mol=cml.text_to_mol,
			file_to_mol=cml.file_to_mol,
			extensions=[".cml", ".xml"],
		),
	)
	register_codec(
		Codec(
			name="cml2",
			# Keep import-only by wiring read callables explicitly.
			text_to_mol=cml2.text_to_mol,
			file_to_mol=cml2.file_to_mol,
			extensions=[],
		),
		aliases=["cml-2"],
	)
	register_module_codec(
		"cdxml",
		cdxml,
		extensions=[".cdxml"],
	)
	register_codec(
		Codec(
			name="svg",
			mol_to_file=render.svg_mol_to_file,
			extensions=[".svg"],
		),
	)
	register_codec(
		Codec(
			name="pdf",
			mol_to_file=render.pdf_mol_to_file,
			extensions=[".pdf"],
		),
	)
	register_codec(
		Codec(
			name="png",
			mol_to_file=render.png_mol_to_file,
			extensions=[".png"],
		),
	)
	register_codec(
		Codec(
			name="ps",
			mol_to_file=render.ps_mol_to_file,
			extensions=[".ps"],
		),
		aliases=["postscript"],
	)
	register_codec(
		Codec(
			name="cdsvg",
			text_to_mol=cdsvg.text_to_mol,
			mol_to_text=cdsvg.mol_to_text,
			file_to_mol=cdsvg.file_to_mol,
			mol_to_file=cdsvg.mol_to_file,
			extensions=[".cdsvg"],
		),
		aliases=["cd-svg"],
	)
	# RDKit-backed codecs
	from oasa.codecs import rdkit_formats
	register_codec(
		Codec(
			name="molfile_v3000",
			text_to_mol=rdkit_formats.molfile_v3000_text_to_mol,
			mol_to_text=rdkit_formats.molfile_v3000_mol_to_text,
			file_to_mol=rdkit_formats.molfile_v3000_file_to_mol,
			mol_to_file=rdkit_formats.molfile_v3000_mol_to_file,
			description="Molfile V3000",
		),
		aliases=["mol-v3000", "v3000"],
	)
	register_codec(
		Codec(
			name="sdf",
			text_to_mol=rdkit_formats.sdf_text_to_mol,
			mol_to_text=rdkit_formats.sdf_mol_to_text,
			file_to_mol=rdkit_formats.sdf_file_to_mol,
			mol_to_file=rdkit_formats.sdf_mol_to_file,
			extensions=[".sdf"],
			description="SDF (Structure Data File)",
		),
	)
	register_codec(
		Codec(
			name="sdf_v3000",
			text_to_mol=rdkit_formats.sdf_v3000_text_to_mol,
			mol_to_text=rdkit_formats.sdf_v3000_mol_to_text,
			file_to_mol=rdkit_formats.sdf_v3000_file_to_mol,
			mol_to_file=rdkit_formats.sdf_v3000_mol_to_file,
			description="SDF V3000",
		),
		aliases=["sdf-v3000"],
	)
	register_codec(
		Codec(
			name="smarts",
			mol_to_text=rdkit_formats.smarts_mol_to_text,
			mol_to_file=rdkit_formats.smarts_mol_to_file,
			extensions=[".sma"],
			description="SMARTS (export-only)",
		),
	)
	_DEFAULTS_REGISTERED = True


#============================================
def get_codec(name):
	_ensure_defaults_registered()
	key = _normalize_name(name)
	if key in _ALIASES:
		key = _ALIASES[key]
	codec = _CODECS.get(key)
	if not codec:
		raise KeyError(f"Codec '{name}' is not registered.")
	return codec


#============================================
def list_codecs():
	_ensure_defaults_registered()
	return sorted(_CODECS.keys())


#============================================
def get_codec_by_extension(ext):
	_ensure_defaults_registered()
	key = _normalize_extension(ext)
	if not key:
		raise ValueError("Extension is required.")
	name = _EXTENSIONS.get(key)
	if not name:
		raise KeyError(f"No codec registered for extension '{key}'.")
	return _CODECS[name]


#============================================
def get_registry_snapshot():
	"""Return registry capabilities for runtime discovery."""
	_ensure_defaults_registered()
	snapshot = {}
	for name, codec in sorted(_CODECS.items()):
		snapshot[name] = {
			"extensions": list(codec.extensions),
			"reads_text": codec.reads_text,
			"writes_text": codec.writes_text,
			"reads_files": codec.reads_files,
			"writes_files": codec.writes_files,
		}
	return snapshot
