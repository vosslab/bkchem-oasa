"""Behavior coverage for the public legacy text-layout value."""

# local repo modules
import oasa.render_ops


#============================================
def test_text_layout_runs_preserve_supported_script_semantics() -> None:
	"""Subscripts and superscripts retain their backend baseline meaning."""
	runs = oasa.render_ops.text_layout_runs("H<sub>2</sub>O<sup>+</sup>")
	assert [(run.text, run.baseline) for run in runs] == [
		("H", "base"), ("2", "sub"), ("O", "base"), ("+", "sup"),
	]
	assert runs[1].font_scale < runs[0].font_scale and runs[3].font_scale < runs[0].font_scale
	assert runs[1].baseline_offset_em > 0 and runs[3].baseline_offset_em < 0


#============================================
def test_text_layout_runs_keep_plain_text_on_the_base_baseline() -> None:
	"""Unmarked legacy text stays one unscaled base-baseline run."""
	assert oasa.render_ops.text_layout_runs("H2O") == (
		oasa.render_ops.TextLayoutRun("H2O", "base", 1.0, 0.0),
	)


#============================================
def test_text_layout_runs_prioritize_nested_subscript() -> None:
	"""Combined legacy markup keeps the historical subscript precedence."""
	runs = oasa.render_ops.text_layout_runs("A<sup>x<sub>2</sub></sup>B")
	assert [run.baseline for run in runs] == ["base", "sup", "sub", "base"]


#============================================
def test_text_layout_runs_keep_malformed_markup_literal() -> None:
	"""Malformed legacy markup remains visible as one base text run."""
	text = "A<sub>broken</sup>B"
	assert oasa.render_ops.text_layout_runs(text) == (
		oasa.render_ops.TextLayoutRun(text, "base", 1.0, 0.0),
	)
