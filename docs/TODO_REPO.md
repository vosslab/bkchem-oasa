# Todo repo

- Publish OASA to PyPI from the monorepo.
- Plan BKChem binary distribution (macOS dmg, Linux Flatpak, Windows installer).
- Reconcile licensing guidance in [docs/REPO_STYLE.md](docs/REPO_STYLE.md) with
  GPLv2 repo policy and LGPLv3/AGPLv3 future plans.
- Make the OASA backend LGPLv3 and the BKChem frontend AGPLv3
- Remove package specific .md files for BKChem and OASA and move to central .md docs/
- reconsider old redundant folder names and prefer unique ones e.g. packages/oasa/oasa/
  could cause a future problem, prefer like packages/bkchem-app/bkchem/; oasa is not an
  app though. packages/oasa/oasa/ -> packages/oasa-backend/oasa/ OR packages/oasa/oasa_lib/
