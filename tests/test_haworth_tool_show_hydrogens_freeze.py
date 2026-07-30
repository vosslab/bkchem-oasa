"""Guardrail: tool-side Haworth render calls must pin show_hydrogens=False."""

# Standard Library
import ast
import pathlib


#============================================
def _dotted_name(node: object) -> object:
	"""Return dotted name for one AST node when possible."""
	if isinstance(node, ast.Name):
		return node.id
	if isinstance(node, ast.Attribute):
		parent = _dotted_name(node.value)
		if parent is None:
			return None
		return f"{parent}.{node.attr}"
	return None


#============================================
def _haworth_render_call_kind(call: object, imported_function_aliases: object) -> object:
	"""Return canonical haworth render kind for one call node, or None."""
	func_name = _dotted_name(call.func)
	if func_name in (
			"haworth_renderer.render",
			"oasa.haworth_renderer.render",
	):
		return "render"
	if func_name in (
			"haworth_renderer.render_from_code",
			"oasa.haworth_renderer.render_from_code",
	):
		return "render_from_code"
	if isinstance(call.func, ast.Name):
		return imported_function_aliases.get(call.func.id)
	return None


#============================================
def _has_explicit_show_h_false(call: object) -> object:
	"""Return True when call has explicit show_hydrogens=False keyword."""
	for keyword in call.keywords:
		if keyword.arg != "show_hydrogens":
			continue
		return isinstance(keyword.value, ast.Constant) and (keyword.value.value is False)
	return False


#============================================
def test_tool_haworth_calls_pin_show_hydrogens_false() -> None:
	"""Fail if any tools/ Haworth render call omits explicit show_hydrogens=False."""
	repo_root = pathlib.Path(__file__).resolve().parents[1]
	tools_dir = repo_root / "tools"
	failures = []
	call_count = 0
	for path in sorted(tools_dir.glob("*.py")):
		source = path.read_text(encoding="utf-8")
		tree = ast.parse(source, filename=str(path))
		imported_function_aliases = {}
		for node in ast.walk(tree):
			if not isinstance(node, ast.ImportFrom):
				continue
			if node.module != "oasa.haworth_renderer":
				continue
			for alias in node.names:
				local_name = alias.asname or alias.name
				if alias.name in ("render", "render_from_code"):
					imported_function_aliases[local_name] = alias.name
		for node in ast.walk(tree):
			if not isinstance(node, ast.Call):
				continue
			call_kind = _haworth_render_call_kind(node, imported_function_aliases)
			if call_kind is None:
				continue
			call_count += 1
			if _has_explicit_show_h_false(node):
				continue
			failures.append(
				f"{path}:{node.lineno} haworth_renderer.{call_kind} must set show_hydrogens=False explicitly"
			)
	assert call_count > 0, "No Haworth tool render callsites found under tools/"
	assert not failures, "\n".join(failures)
