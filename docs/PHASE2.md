# Phase 2: Style language

**Status:** done, 12 Nov 2026. 412 tests passing at the end of the phase.

## Goal

Turn a style string into a typed `StyleSpec`, with no data and no map involved, so every piece is unit-testable.

## What was built

| File | Does |
| --- | --- |
| `kharita/errors.py` | `KharitaError`, `StyleSyntaxError` (token, position, caret pointer), `BindingError`, `KharitaWarning` |
| `kharita/tokenizer.py` | Bracket- and quote-aware splitting; rejects nested or unclosed brackets |
| `kharita/palette.py` | Tailwind colours to RGBA with `/opacity`; ramp lookup with `-r`; did-you-mean on typos |
| `kharita/expr.py` | Bracket expressions: `[col]`, `[col/col]`, `[col*n]`, quoted names. No `eval` |
| `kharita/spec.py` | `StyleSpec` and `Scheme` dataclasses, defaults |
| `kharita/registry.py` | One handler per utility, each with a good and a bad example; built-in presets |
| `kharita/parser.py` | `parse`, `define`, `explain`, `validate`, `utilities`, `help`; conflict and cross-rule checks |
| `kharita/data/` | `colors.json` (Tailwind 3.4.17), `ramps.json` (24 ramps), licence notices |
| `docs/GRAMMAR.md` | Every utility with an example |
| `notebooks/02_style_language.ipynb` | Tour of the language and its errors |

## Decisions

- Explicit utilities override a preset's values wherever they appear in the string.
- `define()` checks syntax but skips the rule that a scheme needs a data-bound fill, since a preset's fill arrives when it is used.
- Two utilities setting the same property raise rather than last-wins, so typos never pass silently.
- Text such as titles and labels goes in keyword arguments, not the style string.

## Tests

`test_tokenizer`, `test_palette`, `test_expr`, `test_registry`, `test_parser`. Every registered utility must carry a passing and a failing example, and both are run; a drift test fails if a utility is missing from `docs/GRAMMAR.md`; typos must produce the right suggestion.

## How to verify

```
pytest -q tests/test_tokenizer.py tests/test_palette.py tests/test_expr.py tests/test_registry.py tests/test_parser.py
```

Then run `notebooks/02_style_language.ipynb`; each error cell should print a caret under the bad token.

## Known issues

None open.
