import builtins
import os
import time
import tkinter.filedialog

import logger
import dialogs

from singleton_store import Store

_ = getattr( builtins, "_", None)
if not _:
	def _( text):
		return text
	builtins._ = _


def process_directory(app, fragment, directory):
	files = 0
	matching = 0

	dialog = dialogs.progress_dialog(app, title=_("Search progress"))

	files_to_go = []
	for filename in os.listdir(directory):
		path = os.path.join(directory, filename)
		if os.path.isfile(path) and os.path.splitext(path)[1] in (".svg", ".cdml"):
			files_to_go.append(path)

	for f in files_to_go:
		#print f
		dialog.update(
			files / len(files_to_go),
			top_text=os.path.split(f)[1],
			bottom_text=_("Found: %d matching") % matching,
		)
		files += 1
		app.in_batch_mode = True
		if app.add_new_paper(name=f):
			if app._load_CDML_file(f, draw=False):
				found = False
				for mol in app.paper.molecules:
					gen = mol.select_matching_substructures(
						fragment,
						implicit_freesites=True,
					)
					try:
						next(gen)
					except StopIteration:
						pass
					else:
						found = True
						matching += 1
						mol.clean_after_search(fragment)
						break
				if not found:
					app.close_current_paper()
				else:
					app.in_batch_mode = False
					[o.draw() for o in app.paper.stack]
					app.paper.set_bindings()
					app.paper.add_bindings()
			else:
				app.close_current_paper()

	app.in_batch_mode = False
	dialog.close()
	return files


def main(app):
	t = time.time()
	selected_mols = [
		o for o in app.paper.selected_to_unique_top_levels()[0]
		if o.object_type == 'molecule'
	]
	if not selected_mols and len(app.paper.molecules) == 1:
		selected_mols = app.paper.molecules

	if len(selected_mols) > 1:
		Store.log(_("Select only one molecule"), message_type="error")
	elif len(selected_mols) == 0:
		Store.log(
			_("Draw a molecule that you want to use as the fragment for search"),
			message_type="error",
		)
	else:
		# we may proceed
		fragment = selected_mols[0]

		directory = tkinter.filedialog.askdirectory(
			parent=app,
			initialdir=app.save_dir or "./",
		)

		if directory:
			Store.logger.handling = logger.ignorant
			files = process_directory(app, fragment, directory)

			t = time.time() - t
			#print "%d files, %.2fs, %.2fms per file" % (files, t, 1000*(t/files))

			Store.logger.handling = logger.normal
			if files:
				Store.log(
					_("Searched %d files, %.2fs, %.2fms per file") %
					(files, t, 1000 * (t / files)),
				)
			else:
				Store.log(_("No files to search in were found"))
