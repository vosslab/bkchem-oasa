"""Tests for legacy BKChem parser construction without global OASA state."""

# local repo modules
import bkchem.classes
import bkchem.atom_lib
import bkchem.group_lib
import bkchem.main
import bkchem.molecule_lib
import bkchem.queryatom_lib
import oasa.molecule_lib
import oasa.oasa_config


#============================================
class _Paper:
	"""Minimal non-GUI paper context for backend molecule construction."""

	def __init__(self) -> None:
		self.standard = bkchem.classes.standard()


#============================================
class _FakeInterpreter:
	"""Enough of Tcl's public interface for constructor configuration."""

	def call(self, *args: object) -> None:
		return None


#============================================
class _FakeTk:
	"""Non-native Tk stand-in for the legacy constructor path."""

	def __init__(self) -> None:
		self.tk = _FakeInterpreter()


#============================================
def _fake_pixels(self: object, text: object) -> int:
	"""Supply a deterministic screen DPI without creating a Cocoa window."""
	return 72


#============================================
def _no_op(self: object, *args: object) -> None:
	"""Replace visual Tk setup in the non-GUI constructor regression."""
	return None


#============================================
def _fake_color(name: object) -> str:
	"""Return a stable palette value for non-GUI startup coverage."""
	return "#000"


#============================================
def _no_arg() -> None:
	"""Replace a no-argument module-level startup hook."""
	return None


#============================================
def _unexpected_molecule() -> object:
	"""Fail if group parsing reads the legacy process-wide factory."""
	msg = "Config.molecule_class should not be used"
	raise RuntimeError(msg)


#============================================
def test_group_formula_uses_its_paper_molecule_factory(monkeypatch: object) -> None:
	"""Implicit groups retain BKChem atoms while Config is intentionally unusable."""
	monkeypatch.setattr(
		oasa.oasa_config.Config,
		"molecule_class",
		_unexpected_molecule,
	)
	paper = _Paper()
	molecule = bkchem.molecule_lib.BkMolecule(paper=paper)
	group = molecule.create_vertex(bkchem.group_lib.BkGroup)
	molecule.add_vertex(group)
	group.set_name("CH3OH", occupied_valency=0)
	assert (
		type(group.group_graph),
		type(group.group_graph.vertices[0]),
	) == (bkchem.molecule_lib.BkMolecule, bkchem.atom_lib.BkAtom)


#============================================
def test_query_formula_uses_its_paper_molecule_factory(monkeypatch: object) -> None:
	"""Query formula parsing requests BKChem graph construction explicitly."""
	monkeypatch.setattr(
		oasa.oasa_config.Config,
		"molecule_class",
		_unexpected_molecule,
	)
	paper = _Paper()
	molecule = bkchem.molecule_lib.BkMolecule(paper=paper)
	query = molecule.create_vertex(bkchem.queryatom_lib.BkQueryatom)
	molecule.add_vertex(query)
	graph = query.interpret_name("CH3")
	assert isinstance(graph, bkchem.molecule_lib.BkMolecule)


#============================================
def test_legacy_startup_keeps_oasa_default_factory(monkeypatch: object) -> None:
	"""Constructing the Tk shell no longer changes OASA's process-wide default."""
	monkeypatch.setattr(bkchem.main, "Tk", _FakeTk)
	monkeypatch.setattr(bkchem.main.BKChem, "winfo_fpixels", _fake_pixels)
	monkeypatch.setattr(bkchem.main.BKChem, "option_add", _no_op)
	monkeypatch.setattr(bkchem.main.BKChem, "tk_setPalette", _no_op)
	monkeypatch.setattr(bkchem.main.theme_manager, "get_active_theme_name", _no_arg)
	monkeypatch.setattr(bkchem.main.theme_manager, "get_color", _fake_color)
	monkeypatch.setattr(bkchem.main.Store, "app", None)
	monkeypatch.setattr(bkchem.main.Screen, "dpi", 72)
	monkeypatch.setattr(
		oasa.oasa_config.Config,
		"molecule_class",
		oasa.molecule_lib.Molecule,
	)
	app = object.__new__(bkchem.main.BKChem)
	bkchem.main.BKChem.__init__(app)
	assert oasa.oasa_config.Config.molecule_class is oasa.molecule_lib.Molecule
