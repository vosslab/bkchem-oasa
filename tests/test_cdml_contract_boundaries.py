"""Architecture laws for the OASA/CDML and BKChem frontend boundary.

This suite deliberately guards cross-cutting source boundaries rather than
enumerating commands. Transaction behavior belongs to OASA document-authority
tests; command tests remain responsible only for their own public grammar.
"""

# Standard Library
import ast

# local repo modules
import file_utils


_OASA_PREFIX = "packages/oasa/oasa/"
_CLASSIC_PREFIX = "packages/bkchem-app/bkchem/"
_QT_PREFIX = "packages/bkchem-qt.app/bkchem_qt/"
_QT_BRIDGE_PREFIX = f"{_QT_PREFIX}bridge/"
_FRONTEND_PREFIXES = (_CLASSIC_PREFIX, _QT_PREFIX)
_FRONTEND_IMPORT_ROOTS = frozenset({"PySide6", "bkchem", "bkchem_qt", "tkinter"})
_LEGACY_IMPORT_ROOTS = frozenset({"bkchem", "tkinter"})
_PRIVATE_GRAPH_FIELDS = frozenset({"_edges", "_vertices"})
_GRAPH_IMPLEMENTATION_MODULES = (
	"oasa.atom_lib",
	"oasa.bond_lib",
	"oasa.chem_vertex",
	"oasa.graph",
	"oasa.molecule_lib",
	"oasa.query_atom",
)


#============================================
def _is_oasa_source(relative_path: str) -> bool:
	"""Return whether a tracked Python file belongs to the OASA backend."""
	return relative_path.startswith(_OASA_PREFIX)


#============================================
def _is_frontend_source(relative_path: str) -> bool:
	"""Return whether a tracked Python file belongs to either BKChem frontend."""
	return relative_path.startswith(_FRONTEND_PREFIXES)


#============================================
def _is_qt_source(relative_path: str) -> bool:
	"""Return whether a tracked Python file belongs to the Qt frontend."""
	return relative_path.startswith(_QT_PREFIX)


_OASA_FILES = file_utils.discover_files(
	extensions=(".py",), extra_filter=_is_oasa_source,
)
_FRONTEND_FILES = file_utils.discover_files(
	extensions=(".py",), extra_filter=_is_frontend_source,
)
_QT_FILES = file_utils.discover_files(
	extensions=(".py",), extra_filter=_is_qt_source,
)


#============================================
def _tree(path: str) -> ast.Module:
	"""Parse one already tracked Python source file for contract inspection."""
	tree, error = file_utils.parse_source(path)
	if error is not None:
		raise AssertionError(f"Unable to inspect {file_utils.rel_to_root(path)}: {error}")
	return tree


#============================================
def _import_root(module_name: str) -> str:
	"""Return the top-level package named by an absolute import."""
	return module_name.partition(".")[0]


#============================================
def _imported_names(tree: ast.Module) -> dict[str, str]:
	"""Map local import spellings to their absolute OASA-qualified names."""
	bindings = {}
	for node in file_utils.iter_imports(tree):
		if isinstance(node, ast.Import):
			for alias in node.names:
				if not alias.name.startswith("oasa"):
					continue
				local_name = alias.asname or _import_root(alias.name)
				bindings[local_name] = alias.name if alias.asname else local_name
			continue
		if node.module is None or not node.module.startswith("oasa"):
			continue
		for alias in node.names:
			if alias.name == "*":
				continue
			local_name = alias.asname or alias.name
			bindings[local_name] = f"{node.module}.{alias.name}"
	return bindings


#============================================
def _qualified_name(node: ast.AST, bindings: dict[str, str]) -> str | None:
	"""Resolve a Name or Attribute through the file's OASA import bindings."""
	if isinstance(node, ast.Name):
		return bindings.get(node.id, node.id)
	if not isinstance(node, ast.Attribute):
		return None
	prefix = _qualified_name(node.value, bindings)
	if prefix is None:
		return None
	return f"{prefix}.{node.attr}"


#============================================
def _type_names(node: ast.AST, bindings: dict[str, str]) -> tuple[str, ...]:
	"""Resolve every type named in an isinstance/issubclass type expression."""
	if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
		names = []
		for element in node.elts:
			names.extend(_type_names(element, bindings))
		return tuple(names)
	if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
		return _type_names(node.left, bindings) + _type_names(node.right, bindings)
	name = _qualified_name(node, bindings)
	return () if name is None else (name,)


#============================================
def _is_graph_implementation(name: str) -> bool:
	"""Return whether a resolved name belongs to an OASA graph implementation."""
	return any(
		name == module_name or name.startswith(f"{module_name}.")
		for module_name in _GRAPH_IMPLEMENTATION_MODULES
	)


#============================================
def _absolute_imports(tree: ast.Module) -> list[tuple[ast.AST, str]]:
	"""Return absolute imported modules, expanding ``from oasa import x``."""
	imports = []
	for node in file_utils.iter_imports(tree):
		if isinstance(node, ast.Import):
			imports.extend((node, alias.name) for alias in node.names)
		elif node.module is not None and node.level == 0:
			if node.module == "oasa":
				imports.extend((node, f"oasa.{alias.name}") for alias in node.names)
			else:
				imports.append((node, node.module))
	return imports


#============================================
def _issue(path: str, node: ast.AST, message: str) -> str:
	"""Format one stable source-location contract violation."""
	return f"{file_utils.rel_to_root(path)}:{getattr(node, 'lineno', 0)}: {message}"


#============================================
def _forbidden_imports(
		path: str, forbidden_roots: frozenset[str],
		) -> list[str]:
	"""Return forbidden absolute-import violations from one source file."""
	violations = []
	for node, module_name in _absolute_imports(_tree(path)):
		if _import_root(module_name) in forbidden_roots:
			violations.append(_issue(path, node, f"forbidden import {module_name!r}"))
	return violations


#============================================
def _frontend_composition_violations(
		path: str, tree: ast.Module | None = None,
		) -> list[str]:
	"""Return storage, inheritance, graph-test, and registration violations."""
	tree = tree or _tree(path)
	bindings = _imported_names(tree)
	violations = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Attribute) and node.attr in _PRIVATE_GRAPH_FIELDS:
			violations.append(_issue(path, node, f"private graph access .{node.attr}"))
		elif isinstance(node, ast.ClassDef):
			for base in node.bases:
				base_name = _qualified_name(base, bindings)
				if base_name is not None and base_name.startswith("oasa."):
					violations.append(_issue(path, base, f"frontend inherits {base_name}"))
		elif (
			isinstance(node, ast.Call)
			and isinstance(node.func, ast.Name)
			and node.func.id in {"isinstance", "issubclass"}
			and len(node.args) >= 2
		):
			for type_name in _type_names(node.args[1], bindings):
				if _is_graph_implementation(type_name):
					violations.append(
						_issue(path, node, f"frontend tests graph implementation {type_name}"),
					)
		elif (
			isinstance(node, ast.Call)
			and isinstance(node.func, ast.Attribute)
			and node.func.attr == "register"
			):
			for argument in node.args:
				registered_name = _qualified_name(argument, bindings)
				if registered_name is not None and _is_graph_implementation(registered_name):
					violations.append(
						_issue(
							path,
							node,
							f"frontend registers graph implementation {registered_name}",
						),
					)
	return violations


#============================================
def _graph_import_violations(path: str) -> list[str]:
	"""Return Qt graph-implementation imports outside its adapter bridge."""
	if file_utils.rel_to_root(path).startswith(_QT_BRIDGE_PREFIX):
		return []
	return [
		_issue(path, node, f"graph implementation import {module_name!r} outside bridge")
		for node, module_name in _absolute_imports(_tree(path))
		if _is_graph_implementation(module_name)
	]


#============================================
def test_oasa_backend_is_frontend_neutral() -> None:
	"""The backend imports no classic, Qt, or GUI runtime package."""
	violations = []
	for path in _OASA_FILES:
		violations.extend(_forbidden_imports(path, _FRONTEND_IMPORT_ROOTS))
	assert not violations, "\n".join(violations)


#============================================
def test_qt_frontend_is_independent_of_the_classic_runtime() -> None:
	"""The current Qt runtime never imports deprecated classic BKChem or Tk."""
	violations = []
	for path in _QT_FILES:
		violations.extend(_forbidden_imports(path, _LEGACY_IMPORT_ROOTS))
	assert not violations, "\n".join(violations)


#============================================
def test_qt_graph_materialization_stays_inside_the_bridge() -> None:
	"""Only the adapter may construct temporary OASA graph implementations."""
	violations = []
	for path in _QT_FILES:
		violations.extend(_graph_import_violations(path))
	assert not violations, "\n".join(violations)


#============================================
def test_frontends_use_composition_and_public_graph_interfaces() -> None:
	"""Frontends cannot inherit, inspect graph classes, or use private storage."""
	violations = []
	for path in _FRONTEND_FILES:
		violations.extend(_frontend_composition_violations(path))
	assert not violations, "\n".join(violations)


#============================================
def test_composition_law_recognizes_supported_python_type_spellings() -> None:
	"""Aliases and PEP 604 unions cannot silently evade the architecture law."""
	cases = (
		("def inspect(graph):\n\treturn graph._vertices\n", "private graph access"),
		(
			"from oasa.atom_lib import Atom as BackendAtom\n"
			"class FrontendAtom(BackendAtom):\n\tpass\n",
			"frontend inherits oasa.atom_lib.Atom",
		),
		(
			"import oasa.atom_lib as atom_implementation\n"
			"def inspect(value):\n"
			"\treturn isinstance(value, atom_implementation.Atom | str)\n",
			"frontend tests graph implementation oasa.atom_lib.Atom",
		),
		(
			"from oasa.graph import Graph as BackendGraph\n"
			"class ProjectionPort:\n\tpass\n"
			"ProjectionPort.register(BackendGraph)\n",
			"frontend registers graph implementation oasa.graph.Graph",
		),
	)
	for source, expected in cases:
		violations = _frontend_composition_violations(
			"synthetic_frontend.py", ast.parse(source),
		)
		assert any(expected in violation for violation in violations), source

	contract_value_tree = ast.parse(
		"import oasa.cdml_document\n"
		"def inspect(value):\n"
		"\treturn isinstance(value, oasa.cdml_document.CDMLSnapshot)\n"
	)
	assert not _frontend_composition_violations(
		"synthetic_frontend.py", contract_value_tree,
	)
