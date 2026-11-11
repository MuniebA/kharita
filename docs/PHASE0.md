# Phase 0 on your laptop

Commands are for Windows PowerShell. macOS and Linux differences are noted where they matter.

Phase 0 is done when `pytest` passes on your laptop, the GitHub Actions run is green, and `data/processed/sudan_states.gpkg` exists.

## 1. Install the tools (15 min)

```powershell
winget install Python.Python.3.12
winget install Git.Git
```

Close and reopen PowerShell, then check:

```powershell
py -3.12 --version
git --version
```

Use Python 3.12. kharita needs 3.11 or newer because Lonboard 0.17 does, and 3.12 has the widest choice of ready-built packages.

Set your Git identity once:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## 2. Check the name (10 min)

- https://pypi.org/project/kharita/ should say "Not Found" (it did on 12 Nov 2026).
- https://github.com/kharita: if taken, that only matters for an organisation name; your repo can still be `your-username/kharita`.
- Search "kharita" in the WIPO Global Brand Database (https://branddb.wipo.int) for software trademarks.

## 3. Create the GitHub repo (5 min)

On GitHub: New repository, name `kharita`, public, and **do not** add a README, licence or .gitignore (the zip already has them).

## 4. Unpack and install (10 min)

Unzip `kharita-phase0.zip` to a short path such as `C:\code\kharita` (long paths can break some Windows installs).

```powershell
cd C:\code\kharita
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If `Activate.ps1` is blocked, run this once and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

macOS or Linux: `python3.12 -m venv .venv` then `source .venv/bin/activate`.

## 5. Run the checks (2 min)

```powershell
ruff check .
pytest
```

Expected: `All checks passed!` and `9 passed`. A few warnings are fine.

## 6. First commit and CI (10 min)

```powershell
git init -b main
git add .
git commit -m "Phase 0: project skeleton, palette data, fixtures, CI"
git remote add origin https://github.com/YOUR-USERNAME/kharita.git
git push -u origin main
```

Open the repo's **Actions** tab. The CI workflow runs 6 jobs (Ubuntu and Windows, Python 3.11 to 3.13). All six should go green in a few minutes. If one fails, open it and read the last red step.

## 7. Get the demo data (30 to 60 min)

Download both files from https://data.humdata.org/dataset/sudan-subnational-boundaries-and-tabular-data into `data\raw\`:

- `Sudan.gdb.zip`
- `Sudan_uscb_202101.xlsx`

Check the licence shown on that page still says Creative Commons Attribution, then unzip:

```powershell
Expand-Archive data\raw\Sudan.gdb.zip -DestinationPath data\raw
```

You should now have a folder ending in `.gdb` inside `data\raw\`.

Open the notebook:

```powershell
jupyter lab
```

Run `notebooks/00_sudan_data.ipynb` cell by cell. Five values are marked `CHANGE_ME`; each is set from what the cell above it prints:

1. `STATE_LAYER`: the admin 1 (state) layer name from the layer list
2. `SHEET`: the sheet with population by state
3. `HEADER_ROW`: the row number holding the column names in that sheet
4. `KEY_IN_STATES` and `KEY_IN_POP`: the state code or name used in each table to join them
5. `POP_COLUMN`: the total population column

The join cell prints any states that failed to match. Fix those (usually spelling or code differences) before saving. The last cell shows the map with plain Lonboard; use JupyterLab rather than VS Code notebooks if the map does not appear.

Commit the processed file (the raw folder is ignored by Git):

```powershell
git add data\processed\sudan_states.gpkg notebooks\00_sudan_data.ipynb
git commit -m "Add Sudan states demo data (U.S. Census Bureau via HDX, CC BY)"
git push
```

## 8. Review the grammar (30 min)

Read `docs/GRAMMAR.md`. It is the contract Phase 2 builds against. Change anything you disagree with now; changing it after the parser exists costs much more.

## What the zip already contains

| Path | What it is |
| --- | --- |
| `pyproject.toml` | Package metadata; core dependencies numpy, geopandas, `lonboard[geopandas]` (pinned to 0.17) |
| `kharita/` | Package with `errors.py`, `palette.py` and empty modules for later phases |
| `kharita/data/` | Tailwind palette (22 x 11), 24 data ramps, licence notices |
| `tests/conftest.py` | Synthetic fixtures: ties, nulls, constant and all-null columns, zero area, text categories, mixed and null geometries, missing CRS |
| `tests/test_setup.py` | 9 checks that the package, data and fixtures are sound, and that Lonboard can draw the fixture |
| `.github/workflows/ci.yml` | Lint and tests on every push |
| `docs/GRAMMAR.md` | Every v0.1 utility with an example |
| `notebooks/00_sudan_data.ipynb` | Turns the HDX download into the demo file |
| `data/README.md` | Data source, licence and the attribution line to show on demo maps |
