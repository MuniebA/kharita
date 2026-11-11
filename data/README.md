# Demo data

## Source

**Sudan Subnational Population and Housing Data Tables with Administrative Boundaries, Based on National Census and Surveys**
U.S. Census Bureau, via the Humanitarian Data Exchange (HDX).
https://data.humdata.org/dataset/sudan-subnational-boundaries-and-tabular-data
Licence: Creative Commons Attribution International (CC BY).

Files to download into `data/raw/`:

- `Sudan.gdb.zip` (boundaries, geodatabase)
- `Sudan_uscb_202101.xlsx` (population tables)

Fallback for boundaries only: OCHA's *Sudan - Subnational Administrative Boundaries* (COD-AB),
https://data.humdata.org/dataset/cod-ab-sdn, licence CC BY-IGO.

Do **not** use `sudan-administative-boundaries-1`: its licence is humanitarian use only.

## Attribution to show with every demo map

> Boundaries and population: U.S. Census Bureau, via HDX (CC BY).

## Layout

- `data/raw/` holds the downloads and is not committed.
- `data/processed/sudan_states.gpkg` is the small cleaned file the demo uses; it is committed.

The figures are census-based estimates for planning and demonstration, not current counts.
