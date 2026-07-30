"""Tests for legacy parser construction without Config.molecule_class."""

# local repo modules
import oasa.linear_formula
import oasa.molecule_lib
import oasa.oasa_config
import oasa.smiles_lib


#============================================
class _InjectedMolecule(oasa.molecule_lib.Molecule):
	"""A graph class selected by an explicit caller-owned factory."""


#============================================
def _unexpected_molecule() -> object:
	"""Fail if a test accidentally falls back to the legacy global factory."""
	msg = "Config.molecule_class should not be used"
	raise RuntimeError(msg)


#============================================
def test_smiles_factory_bypasses_global_config(monkeypatch: object) -> None:
	"""An injected SMILES factory owns the parsed molecule class."""
	monkeypatch.setattr(
		oasa.oasa_config.Config,
		"molecule_class",
		_unexpected_molecule,
	)
	smiles = oasa.smiles_lib.Smiles(molecule_factory=_InjectedMolecule)
	smiles.read_smiles("CO")
	assert isinstance(smiles.structure, _InjectedMolecule)


#============================================
def test_formula_root_bypasses_global_config(monkeypatch: object) -> None:
	"""A supplied formula root is retained instead of allocating globally."""
	monkeypatch.setattr(
		oasa.oasa_config.Config,
		"molecule_class",
		_unexpected_molecule,
	)
	root = _InjectedMolecule()
	formula = oasa.linear_formula.linear_formula("CH3OH", root_molecule=root)
	assert formula.molecule is root


#============================================
def test_formula_root_preserves_nested_smiles_factory(monkeypatch: object) -> None:
	"""A root-selected graph family also owns nested !SMILES fragments."""
	monkeypatch.setattr(
		oasa.oasa_config.Config,
		"molecule_class",
		_unexpected_molecule,
	)
	root = _InjectedMolecule()
	formula = oasa.linear_formula.linear_formula(root_molecule=root)
	parsed = formula.parse_form("(!CO)", mol=root)
	assert parsed is root
