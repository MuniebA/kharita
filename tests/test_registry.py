"""Every registered utility is documented, has examples, and its examples behave."""

from pathlib import Path

import pytest

import kharita as kh
from kharita.registry import UTILITIES

# Some utilities only make sense next to a data-bound fill
NEEDS_DATA_FILL = {"ramp", "scheme"}
CONTEXT = {
    "ramp-set2": "fill-[x] scheme-cat",
    "scheme-div": "fill-[x] ramp-rdbu",
    "scheme-div-[50]": "fill-[x] ramp-rdbu",
    "extrude-max-5000": "extrude-[x]",
    "size-max-30": "size-[x]",
    "width-max-10": "width-[x]",
}

GOOD = [(u.name, ex) for u in UTILITIES.values() for ex in u.examples]
BAD = [(u.name, ex) for u in UTILITIES.values() for ex in u.bad_examples]


def with_context(name, example):
    if example in CONTEXT:
        return f"{example} {CONTEXT[example]}"
    if name in NEEDS_DATA_FILL:
        return f"{example} fill-[x]"
    return example


def test_every_utility_has_good_and_bad_examples():
    for u in UTILITIES.values():
        assert u.examples, u.name
        assert u.bad_examples, u.name
        assert u.description and u.syntax, u.name


@pytest.mark.parametrize("name, example", GOOD)
def test_good_examples_parse(name, example):
    kh.parse(with_context(name, example))


@pytest.mark.parametrize("name, example", BAD)
def test_bad_examples_raise(name, example):
    with pytest.raises(kh.StyleSyntaxError):
        kh.parse(with_context(name, example))


def test_grammar_doc_mentions_every_utility():
    doc = (Path(__file__).parents[1] / "docs" / "GRAMMAR.md").read_text(encoding="utf-8")
    # Bare utilities such as glow appear without a dash
    missing = [u.name for u in UTILITIES.values()
               if f"`{u.name}-" not in doc and not (u.bare and f"`{u.name}`" in doc)]
    assert not missing, f"Add these utilities to docs/GRAMMAR.md: {missing}"
