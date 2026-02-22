"""Chemistry I/O mixin methods for BKChem main application."""

import sys

import tkinter.messagebox

import oasa
from bkchem.bk_dialogs import BkPromptDialog, BkTextDialog
from bkchem import bkchem_config
from bkchem import interactors
from bkchem import oasa_bridge
from bkchem.singleton_store import Store

import builtins
# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


class MainChemistryIOMixin:
  """SMILES / InChI / peptide read and generate helpers extracted from main.py."""

  def read_smiles( self, smiles=None):
    if not oasa_bridge.oasa_available:
      return
    lt = _("Enter a SMILES or IsoSMILES string:")
    if not smiles:
      dial = BkPromptDialog( self,
                               title='SMILES',
                               label_text=lt,
                               entryfield_labelpos = 'n',
                               buttons=(_('OK'),_('Cancel')))
      res = dial.activate()
      if res == _('OK'):
        text = dial.get()
      else:
        return
    else:
      text = smiles

    if text:
      # route through CDML: SMILES -> OASA -> CDML element -> BKChem import
      self.paper.onread_id_sandbox_activate()
      elements = oasa_bridge.smiles_to_cdml_elements( text, self.paper)
      imported = []
      for element in elements:
        mol = self.paper.add_object_from_package( element)
        imported.append( mol)
        mol.draw()
      self.paper.onread_id_sandbox_finish( apply_to=imported)
      self.paper.add_bindings()
      self.paper.start_new_undo_record()
      if len( imported) == 1:
        return imported[0]
      return imported


  def read_inchi( self, inchi=None):
    if not oasa_bridge.oasa_available:
      return
    lt = _("""Before you use his tool, be warned that not all features of InChI are currently supported.
There is no support for stereo-related information, isotopes and a few more things.
The InChI should be entered in the plain text form, e.g.- 1/C7H8/1-7-5-3-2-4-6-7/1H3,2-6H

Enter InChI:""")
    text = None
    if not inchi:
      dial = BkPromptDialog( self,
                               title='InChI',
                               label_text=lt,
                               entryfield_labelpos = 'n',
                               buttons=(_('OK'),_('Cancel')))
      res = dial.activate()
      if res == _('OK'):
        text = dial.get()
    else:
      text = inchi

    if text:
      if bkchem_config.devel:
        # in development mode we do not want to catch the exceptions
        mol = oasa_bridge.read_inchi( text, self.paper)
      else:
        try:
          mol = oasa_bridge.read_inchi( text, self.paper)
        except oasa.oasa_exceptions.oasa_not_implemented_error as error:
          if not inchi:
            tkinter.messagebox.showerror(_("Error processing %s") % 'InChI',
                                   _("Some feature of the submitted InChI is not supported.\n\nYou have most probaly submitted a multicomponent structure (having a . in the sumary layer"))
            return
          else:
            raise ValueError("the processing of inchi failed with following error %s" % error)
        except oasa.oasa_exceptions.oasa_inchi_error as error:
          if not inchi:
            tkinter.messagebox.showerror(_("Error processing %s") % 'InChI',
                                   _("There was an error reading the submitted InChI.\n\nIf you are sure it is a valid InChI, please send me a bug report."))
            return
          else:
            raise ValueError("the processing of inchi failed with following error %s" % error)
        except oasa.oasa_exceptions.oasa_unsupported_inchi_version_error as e:
          if not inchi:
            tkinter.messagebox.showerror(_("Error processing %s") % 'InChI',
                                   _("The submitted InChI has unsupported version '%s'.\n\nYou migth try resubmitting with the version string (the first part of InChI) changed to '1'.") % e.version)
            return
          else:
            raise ValueError("the processing of inchi failed with following error %s" % sys.exc_info()[1])
        except:

          if not inchi:
            tkinter.messagebox.showerror(_("Error processing %s") % 'InChI',
                                   _("The reading of InChI failed with following error:\n\n'%s'\n\nIf you are sure you have submitted a valid InChI, please send me a bug report.") % sys.exc_info()[1])
            return
          else:
            raise ValueError("the processing of inchi failed with following error %s" % sys.exc_info()[1])

      self.paper.stack.append( mol)
      mol.draw()
      self.paper.add_bindings()
      self.paper.start_new_undo_record()


  def read_peptide_sequence( self):
    if not oasa_bridge.oasa_available:
      return
    # get supported amino acid letters from OASA for the dialog prompt
    from oasa.peptide_utils import AMINO_ACID_SMILES
    supported = sorted(AMINO_ACID_SMILES.keys())
    supported_str = ', '.join(supported)
    lt = _("Enter a single-letter amino acid sequence (e.g. ANKLE):\n"
           "Supported: %s") % supported_str
    dial = BkPromptDialog( self,
                             title=_('Peptide Sequence'),
                             label_text=lt,
                             entryfield_labelpos = 'n',
                             buttons=(_('OK'),_('Cancel')))
    res = dial.activate()
    if res != _('OK'):
      return
    text = dial.get()
    if not text or not text.strip():
      return
    # validate input letters before sending to OASA
    sequence = text.strip().upper()
    bad_letters = [aa for aa in sequence if aa not in AMINO_ACID_SMILES]
    if bad_letters:
      tkinter.messagebox.showerror(
        _("Peptide Sequence Error"),
        _("Unrecognized amino acid code(s): %s\n"
          "Supported: %s") % (', '.join(sorted(set(bad_letters))), supported_str))
      return
    # delegate to OASA via bridge: peptide -> SMILES -> CDML
    try:
      elements = oasa_bridge.peptide_to_cdml_elements( sequence, self.paper)
    except ValueError as err:
      tkinter.messagebox.showerror(
        _("Peptide Sequence Error"), str(err))
      return
    # import the CDML elements onto the canvas
    self.paper.onread_id_sandbox_activate()
    imported = []
    for element in elements:
      mol = self.paper.add_object_from_package( element)
      imported.append( mol)
      mol.draw()
    self.paper.onread_id_sandbox_finish( apply_to=imported)
    self.paper.add_bindings()
    self.paper.start_new_undo_record()
    if len( imported) == 1:
      return imported[0]
    return imported


  def gen_smiles(self):
    if not oasa_bridge.oasa_available:
      return
    u, i = self.paper.selected_to_unique_top_levels()
    if not interactors.check_validity(u):
      return
    sms = []
    for m in u:
      if m.object_type == 'molecule':
        sms.append(oasa_bridge.mol_to_smiles(m))
    text = '\n\n'.join(sms)
    dial = BkTextDialog(self,
                          title=_('Generated SMILES'),
                          buttons=(_('OK'),))
    dial.insert('end', text)
    dial.activate()


  def gen_inchi( self):
    program = Store.pm.get_preference( "inchi_program_path")
    self.paper.swap_sides_of_selected("horizontal")
    if not oasa_bridge.oasa_available:
      return
    u, i = self.paper.selected_to_unique_top_levels()
    sms = []
    if not interactors.check_validity( u):
      return

    try:
      for m in u:
        if m.object_type == 'molecule':
            inchi, key, warning = oasa_bridge.mol_to_inchi( m, program)
            sms = sms + warning
            sms.append(inchi)
            sms.append("InChIKey="+key)
            sms.append("")
    except oasa.oasa_exceptions.oasa_inchi_error as e:
      sms = [_("InChI generation failed,"),_("make sure the path to the InChI program is correct in 'Options/InChI program path'"), "", str( e)]
    except:
      sms = [_("Unknown error occured during InChI generation, sorry."), _("Please, try to make sure the path to the InChI program is correct in 'Options/InChI program path'")]
    self.paper.swap_sides_of_selected("horizontal")
    text = '\n'.join( sms)
    dial = BkTextDialog( self,
                           title=_('Generated InChIs'),
                           buttons=(_('OK'),))
    dial.insert( 'end', text)
    dial.activate()
