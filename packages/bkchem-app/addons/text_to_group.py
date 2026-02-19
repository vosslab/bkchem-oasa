import builtins

from group import group
from textatom import textatom
from singleton_store import Store

_ = builtins.__dict__.get( '_', lambda m: m)


#============================================
def main(app):
	# if nothing is selected then use all
	selected = app.paper.selected or (
		j for i in [m.vertices for m in app.paper.molecules] for j in i
	)
	textatoms = [a for a in selected if isinstance(a, textatom)]

	count = 0
	for atom in textatoms:
		val = atom.occupied_valency
		group_vertex = atom.molecule.create_vertex(vertex_class=group)
		text = atom.symbol
		if group_vertex.set_name(text, occupied_valency=val):
			count += 1
			atom.copy_settings(group_vertex)
			atom.molecule.replace_vertices(atom, group_vertex)
			atom.delete()
			group_vertex.draw()

	Store.log(_("%d textatoms were converted to groups") % count)

	app.paper.start_new_undo_record()
	app.paper.add_bindings()
