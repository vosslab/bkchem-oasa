# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for codec registry usage in bkchem oasa_bridge."""

# Local repo modules
import conftest
import pytest


conftest.add_bkchem_to_sys_path()
conftest.add_oasa_to_sys_path()

# local repo modules
import oasa
import oasa_bridge


class DummyCodec:
	def __init__(self):
		self.read_text_calls = []
		self.write_text_calls = []
		self.read_file_calls = []
		self.write_file_calls = []
		self.read_text_result = None
		self.read_file_result = None
		self.write_text_result = ""

	def read_text(self, text, **kwargs):
		self.read_text_calls.append((text, kwargs))
		return self.read_text_result

	def write_text(self, mol, **kwargs):
		self.write_text_calls.append((mol, kwargs))
		return self.write_text_result

	def read_file(self, file_obj, **kwargs):
		self.read_file_calls.append((file_obj, kwargs))
		return self.read_file_result

	def write_file(self, mol, file_obj, **kwargs):
		self.write_file_calls.append((mol, file_obj, kwargs))


class DummyMol:
	def __init__(self):
		self.cleaned = False

	def remove_unimportant_hydrogens(self):
		self.cleaned = True

	def is_connected(self):
		return True


class DummyDisconnectedMol:
	def __init__(self, parts):
		self._parts = parts

	def is_connected(self):
		return False

	def get_disconnected_subgraphs(self):
		return list(self._parts)


class DummyPaper:
	def __init__(self, molecules):
		self.molecules = list(molecules)


class DummySelectionPaper:
	def __init__(self, selected):
		self._selected = list(selected)

	def selected_to_unique_top_levels(self):
		return self._selected, self._selected


class DummyObject:
	def __init__(self, object_type):
		self.object_type = object_type


#============================================
def test_oasa_bridge_mol_to_smiles_uses_registry(monkeypatch):
	codec = DummyCodec()
	codec.write_text_result = "CC"
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)

	dummy_mol = DummyMol()
	monkeypatch.setattr(oasa_bridge, "bkchem_mol_to_oasa_mol",
						lambda mol: dummy_mol)

	result = oasa_bridge.mol_to_smiles("bkchem_mol")
	assert result == "CC"
	assert dummy_mol.cleaned
	assert codec.write_text_calls


#============================================
def test_oasa_bridge_read_inchi_uses_registry(monkeypatch):
	codec = DummyCodec()
	dummy_mol = DummyMol()
	codec.read_text_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(oasa_bridge, "oasa_mol_to_bkchem_mol",
						lambda mol, paper: ("bkchem", mol, paper))

	result = oasa_bridge.read_inchi("InChI=1S/CH4/h1H4", paper="paper")
	assert result == ("bkchem", dummy_mol, "paper")
	assert codec.read_text_calls
	text, kwargs = codec.read_text_calls[0]
	assert text.startswith("InChI=")
	assert kwargs.get("calc_coords") == 1
	assert kwargs.get("include_hydrogens") is False


#============================================
def test_oasa_bridge_read_molfile_uses_registry(monkeypatch):
	codec = DummyCodec()
	dummy_mol = DummyMol()
	codec.read_file_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(oasa_bridge, "oasa_mol_to_bkchem_mol",
						lambda mol, paper: ("bkchem", mol, paper))

	result = oasa_bridge.read_molfile("file", paper="paper")
	assert result == [("bkchem", dummy_mol, "paper")]
	assert codec.read_file_calls


#============================================
def test_oasa_bridge_read_molfile_disconnected(monkeypatch):
	codec = DummyCodec()
	part_a = DummyMol()
	part_b = DummyMol()
	dummy_mol = DummyDisconnectedMol([part_a, part_b])
	codec.read_file_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(oasa_bridge, "oasa_mol_to_bkchem_mol",
						lambda mol, paper: ("bkchem", mol, paper))

	result = oasa_bridge.read_molfile("file", paper="paper")
	assert result == [("bkchem", part_a, "paper"), ("bkchem", part_b, "paper")]


#============================================
def test_oasa_bridge_write_molfile_uses_registry(monkeypatch):
	codec = DummyCodec()
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)

	dummy_mol = DummyMol()
	monkeypatch.setattr(oasa_bridge, "bkchem_mol_to_oasa_mol",
						lambda mol: dummy_mol)

	oasa_bridge.write_molfile("bkchem_mol", "file")
	assert codec.write_file_calls
	assert codec.write_file_calls[0][0] is dummy_mol


#============================================
def test_oasa_bridge_read_cml_uses_registry(monkeypatch):
	codec = DummyCodec()
	part_a = DummyMol()
	part_b = DummyMol()
	codec.read_file_result = DummyDisconnectedMol([part_a, part_b])
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(
		oasa_bridge,
		"oasa_mol_to_bkchem_mol",
		lambda mol, paper: ("bkchem", mol, paper),
	)

	result = oasa_bridge.read_cml("file", paper="paper", version=2)
	assert result == [("bkchem", part_a, "paper"), ("bkchem", part_b, "paper")]
	assert codec.read_file_calls


#============================================
def test_oasa_bridge_write_cml_is_disabled():
	with pytest.raises(ValueError) as error:
		oasa_bridge.write_cml("mol", "file", version=1)
	assert "CML export is not supported" in str(error.value)


#============================================
def test_oasa_bridge_write_cml_from_paper_is_disabled():
	with pytest.raises(ValueError) as error:
		oasa_bridge.write_cml_from_paper(DummyPaper(["one"]), "file", version=2)
	assert "CML export is not supported" in str(error.value)


#============================================
def test_oasa_bridge_read_cdxml_uses_registry(monkeypatch):
	codec = DummyCodec()
	dummy_mol = DummyMol()
	codec.read_file_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(
		oasa_bridge,
		"oasa_mol_to_bkchem_mol",
		lambda mol, paper: ("bkchem", mol, paper),
	)

	result = oasa_bridge.read_cdxml("file", paper="paper")
	assert result == [("bkchem", dummy_mol, "paper")]
	assert codec.read_file_calls


#============================================
def test_validate_selected_molecule_requires_exactly_one_selected():
	paper = DummySelectionPaper([])
	with pytest.raises(ValueError) as error:
		oasa_bridge.validate_selected_molecule(paper)
	assert str(error.value) == "No molecule selected."


#============================================
def test_validate_selected_molecule_rejects_multiple():
	selected = [DummyObject("molecule"), DummyObject("molecule")]
	paper = DummySelectionPaper(selected)
	with pytest.raises(ValueError) as error:
		oasa_bridge.validate_selected_molecule(paper)
	assert "molecules selected." in str(error.value)


#============================================
def test_validate_selected_molecule_returns_single_molecule():
	selected = [DummyObject("atom"), DummyObject("molecule")]
	paper = DummySelectionPaper(selected)
	result = oasa_bridge.validate_selected_molecule(paper)
	assert result.object_type == "molecule"
