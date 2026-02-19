import os.path


def main(app):
	crop_svg = app.paper.get_paper_property('crop_svg')
	app.paper.set_paper_properties(crop_svg=0)

	name = app.paper.file_name['name']
	name, ext = os.path.splitext(name)

	n = app.paper.um.get_number_of_records()

	for _i in range(n):
		app.paper.undo()

	for i in range(n):
		app.save_CDML(name="%s-%02d%s" % (name, i, ext))
		app.paper.redo()

	app.paper.set_paper_properties(crop_svg=crop_svg)
