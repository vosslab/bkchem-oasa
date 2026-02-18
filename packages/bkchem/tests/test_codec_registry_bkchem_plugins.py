# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for BKChem registry-driven format loading."""

# Standard Library
import os

# Third Party
import pytest

# Local repo modules
import conftest

# local repo modules
import format_loader

from singleton_store import Store


class _DummyPaper:
	def __init__(self, properties=None):
		self._properties = properties or {}

	def get_paper_property(self, key):
		return self._properties.get(key)


class _DummyPreferences:
	def __init__(self, values):
		self._values = dict(values)

	def get_preference(self, key):
		return self._values.get(key)


#============================================
def test_load_gui_manifest_rejects_unknown_top_level(tmp_path):
	manifest_path = tmp_path / "format_menus.yaml"
	manifest_path.write_text("formats: {}\nextra: 1\n", encoding="utf-8")
	with pytest.raises(ValueError) as error:
		format_loader.load_gui_manifest(path=str(manifest_path))
	assert "unknown top-level keys" in str(error.value)


#============================================
def test_load_gui_manifest_rejects_unknown_option_key(tmp_path):
	manifest_path = tmp_path / "format_menus.yaml"
	manifest_path.write_text(
		"\n".join(
			[
				"formats:",
				"  inchi:",
				"    display_name: InChI",
				"    scope: selected_molecule",
				"    gui_options:",
				"      - key: program_path",
				"        source: preference",
				"        preference_key: inchi_program_path",
				"        unknown: nope",
			]
		) + "\n",
		encoding="utf-8",
	)
	with pytest.raises(ValueError) as error:
		format_loader.load_gui_manifest(path=str(manifest_path))
	assert "unknown gui option keys" in str(error.value)


#============================================
def test_load_format_entries_joins_registry_and_manifest(monkeypatch):
	backend = {
		"cdxml": {
			"extensions": [".cdxml"],
			"reads_text": True,
			"writes_text": True,
			"reads_files": True,
			"writes_files": True,
		},
		"inchi": {
			"extensions": [".inchi"],
			"reads_text": True,
			"writes_text": True,
			"reads_files": True,
			"writes_files": True,
		},
	}
	gui = {
		"cdxml": {
			"display_name": "CDXML",
			"scope": "paper",
			"gui_options": [],
		},
		"inchi": {
			"display_name": "InChI",
			"menu_capabilities": ["export"],
			"scope": "selected_molecule",
			"gui_options": [],
		},
	}
	monkeypatch.setattr(format_loader, "load_backend_capabilities", lambda: backend)
	monkeypatch.setattr(format_loader, "load_gui_manifest", lambda path=None: gui)
	entries = format_loader.load_format_entries()
	assert entries["cdxml"]["can_import"] is True
	assert entries["cdxml"]["can_export"] is True
	assert entries["inchi"]["can_import"] is False
	assert entries["inchi"]["can_export"] is True
	assert entries["cdxml"]["extensions"] == [".cdxml"]


#============================================
def test_load_format_entries_rejects_unknown_codec(monkeypatch):
	backend = {
		"cdxml": {
			"extensions": [".cdxml"],
			"reads_text": True,
			"writes_text": True,
			"reads_files": True,
			"writes_files": True,
		},
	}
	gui = {
		"missing_codec": {
			"display_name": "Missing",
			"scope": "paper",
			"gui_options": [],
		}
	}
	monkeypatch.setattr(format_loader, "load_backend_capabilities", lambda: backend)
	monkeypatch.setattr(format_loader, "load_gui_manifest", lambda path=None: gui)
	with pytest.raises(ValueError) as error:
		format_loader.load_format_entries()
	assert "missing in OASA registry snapshot" in str(error.value)


#============================================
def test_resolve_gui_kwargs_handles_preference_and_paper_property():
	old_pm = Store.pm
	try:
		Store.pm = _DummyPreferences({"inchi_program_path": "/usr/local/bin/inchi"})
		paper = _DummyPaper(properties={"crop_svg": True})
		options = [
			{
				"key": "program_path",
				"source": "preference",
				"preference_key": "inchi_program_path",
				"required": True,
			},
			{
				"key": "crop",
				"source": "paper_property",
				"property_key": "crop_svg",
			},
		]
		assert format_loader.resolve_gui_kwargs(paper, options) == {
			"program_path": "/usr/local/bin/inchi",
			"crop": True,
		}
	finally:
		Store.pm = old_pm


#============================================
def test_resolve_gui_kwargs_required_preference_missing_raises():
	old_pm = Store.pm
	try:
		Store.pm = _DummyPreferences({})
		paper = _DummyPaper()
		options = [
			{
				"key": "program_path",
				"source": "preference",
				"preference_key": "inchi_program_path",
				"required": True,
			},
		]
		with pytest.raises(ValueError) as error:
			format_loader.resolve_gui_kwargs(paper, options)
		assert "Missing required option 'program_path'" in str(error.value)
	finally:
		Store.pm = old_pm


#============================================
def test_import_format_calls_bridge(monkeypatch, tmp_path):
	calls = []

	def _fake_read_codec_file(codec_name, file_obj, paper, **kwargs):
		calls.append((codec_name, file_obj.read(), paper, kwargs))
		return ["molecule"]

	monkeypatch.setattr(format_loader.oasa_bridge, "read_codec_file", _fake_read_codec_file)
	input_path = tmp_path / "input.cdxml"
	input_path.write_text("<CDXML/>", encoding="utf-8")
	result = format_loader.import_format("cdxml", paper="paper", filename=str(input_path))
	assert result == ["molecule"]
	assert calls == [("cdxml", "<CDXML/>", "paper", {})]


#============================================
def test_export_format_selected_scope_uses_bridge(monkeypatch, tmp_path):
	calls = []
	monkeypatch.setattr(format_loader.oasa_bridge, "validate_selected_molecule", lambda paper: object())

	def _fake_write_selected(codec_name, paper, file_obj, **kwargs):
		calls.append((codec_name, paper, kwargs))
		file_obj.write(b"ok\n")

	monkeypatch.setattr(
		format_loader.oasa_bridge,
		"write_codec_file_from_selected_molecule",
		_fake_write_selected,
	)
	output_path = tmp_path / "out.cdxml"
	format_loader.export_format(
		codec_name="cdxml",
		paper="paper",
		filename=str(output_path),
		scope="selected_molecule",
		gui_options=[],
	)
	assert calls == [("cdxml", "paper", {})]
	assert output_path.read_text(encoding="utf-8") == "ok\n"


#============================================
def test_export_format_smiles_selected_scope_writes_text(monkeypatch, tmp_path):
	monkeypatch.setattr(format_loader.oasa_bridge, "validate_selected_molecule", lambda paper: "mol")
	monkeypatch.setattr(format_loader.oasa_bridge, "mol_to_smiles", lambda mol: "CCO")
	output_path = tmp_path / "out.smi"
	format_loader.export_format(
		codec_name="smiles",
		paper="paper",
		filename=str(output_path),
		scope="selected_molecule",
		gui_options=[],
	)
	assert output_path.read_text(encoding="utf-8") == "CCO\n"


#============================================
def test_export_format_inchi_selected_scope_writes_key_and_warnings(monkeypatch, tmp_path):
	old_pm = Store.pm
	try:
		Store.pm = _DummyPreferences({"inchi_program_path": "/usr/local/bin/inchi"})
		monkeypatch.setattr(format_loader.oasa_bridge, "validate_selected_molecule", lambda paper: "mol")
		calls = []
		monkeypatch.setattr(
			format_loader.oasa_bridge,
			"mol_to_inchi",
			lambda mol, program: calls.append((mol, program)) or (
				"InChI=1S/CH4/h1H4",
				"VNWKTOKETHGBQD-UHFFFAOYSA-N",
				["warn"],
			),
		)
		output_path = tmp_path / "out.inchi"
		format_loader.export_format(
			codec_name="inchi",
			paper="paper",
			filename=str(output_path),
			scope="selected_molecule",
			gui_options=[
				{
					"key": "program_path",
					"source": "preference",
					"preference_key": "inchi_program_path",
					"required": True,
				},
			],
		)
		lines = output_path.read_text(encoding="utf-8").splitlines()
		assert lines[0] == "InChI=1S/CH4/h1H4"
		assert lines[1] == "InChIKey=VNWKTOKETHGBQD-UHFFFAOYSA-N"
		assert lines[2] == "# warn"
		assert calls == [("mol", "/usr/local/bin/inchi")]
	finally:
		Store.pm = old_pm


#============================================
def test_default_manifest_codecs_exist_in_registry_snapshot():
	backend = format_loader.load_backend_capabilities()
	gui = format_loader.load_gui_manifest()
	for codec_name in sorted(gui.keys()):
		assert codec_name in backend


#============================================
def test_manifest_has_no_retired_options_or_deprecated_exporters():
	entries = format_loader.load_format_entries()
	for retired in ("povray",):
		assert retired not in entries
	for import_only in ("cml", "cml2"):
		assert entries[import_only]["can_export"] is False
	retired_options = {
		"invert_coords",
		"scaling",
		"dpi",
		"target_width_px",
		"background_color",
	}
	for entry in entries.values():
		for option in entry.get("gui_options", []):
			assert option["key"] not in retired_options


#============================================
def test_render_formats_are_registry_backed_exports():
	entries = format_loader.load_format_entries()
	for codec_name in ("svg", "png", "pdf", "ps"):
		assert codec_name in entries
		assert entries[codec_name]["can_import"] is False
		assert entries[codec_name]["can_export"] is True


#============================================
def test_legacy_tk_render_plugins_removed_from_repo():
	root = conftest.repo_root()
	removed = (
		"packages/bkchem/bkchem/plugins/tk2cairo.py",
		"packages/bkchem/bkchem/plugins/cairo_lowlevel.py",
		"packages/bkchem/bkchem/plugins/pdf_cairo.py",
		"packages/bkchem/bkchem/plugins/png_cairo.py",
		"packages/bkchem/bkchem/plugins/svg_cairo.py",
		"packages/bkchem/bkchem/plugins/ps_cairo.py",
		"packages/bkchem/bkchem/plugins/ps_builtin.py",
		"packages/bkchem/bkchem/plugins/odf.py",
	)
	for rel_path in removed:
		assert not os.path.exists(os.path.join(root, rel_path))
