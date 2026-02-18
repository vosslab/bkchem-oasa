# local repo modules
import oasa_cli


#============================================
def test_oasa_haworth_cli_svg(tmp_path):
	output_path = tmp_path / "haworth_cli.svg"
	argv = ["haworth", "-s", "C1CCOCC1", "-o", str(output_path)]
	oasa_cli.main(argv)
	assert output_path.is_file()
	assert output_path.stat().st_size > 0
	with open(output_path, "r", encoding="utf-8") as handle:
		svg_text = handle.read()
	assert "<svg" in svg_text
