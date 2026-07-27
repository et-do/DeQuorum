# Datasheet: the Contested-Facts corpus (natural regime)

A short datasheet (after Gebru et al., *Datasheets for Datasets*, 2021) for the
real-misconception corpus used in the attribution head-to-head
([methodology.md](methodology.md), [paper](../paper/reliance-grounded-credit.md)).
Source: [`benchmark/real_contested.py`](../../services/app/src/dequorum/benchmark/real_contested.py).

## Motivation

To evaluate attribution/credit *objectives* in a **natural contested regime** — where a
true contribution competes with a real, plausible misconception — as a complement to
the synthetic near-duplicate (adversarial) regime. The synthetic corpus buys exact
ground truth with invented tokens; this corpus restores realism, at the cost of scale.

## Composition

- **Instances:** ~44 items, each a `(query, true fact, gold phrase, false twin,
  misconception phrase, paraphrase)` tuple. The true fact and its false twin share a
  sentence frame and differ only in the answer, so a grounded model can be swayed
  either way.
- **Domains:** geography (capitals, extent), astronomy & physics, biology & the human
  body, language, and everyday reasoning — grouped in the source file.
- **Ground truth:** each item has one verifiable correct answer and one *documented
  common misconception* as the distractor (e.g. tallest mountain base-to-peak =
  Mauna Kea, not Everest; largest desert = Antarctica, not the Sahara; camel humps
  store fat, not water).
- **Labels:** `gold` / `false_gold` are short distinctive phrases. An automated
  validation test (`tests/benchmark/test_real_contested.py`) asserts every pair is
  **separable**: the true note recalls the gold and not the misconception, and the
  false twin recalls the misconception and not the gold. This guards against curation
  errors that would make an item meaningless.

## Collection & provenance

Single-author curation from well-documented common-misconception sources (e.g. the
Wikipedia "List of common misconceptions" and standard reference facts). Each item is
individually verifiable against public references. No crowd-sourcing, no model
generation of the facts themselves.

## Uses

Intended for the `attribution-truth --corpus real --distractors hard` benchmark, which
scores how well each credit *objective* (resemblance / coverage / reliance) places
credit on the true contribution over its misconception twin. Not intended as a
knowledge benchmark or a misconception-detection benchmark.

## Limitations (stated in the paper)

- **Scale.** Small (~44); Wilson intervals report the resulting uncertainty. A larger
  set is open work.
- **Not independently annotated.** Single-author curation; each item is verifiable but
  the set has not been third-party labelled. Independent annotation is open work.
- **English, general-knowledge, largely Western-centric** common misconceptions;
  domain coverage is not balanced or exhaustive.
- **Selection.** Items were chosen partly for having a *clean, separable* gold vs.
  misconception phrasing (required by the keyword grader), which may bias toward
  crisp-answer questions and away from nuanced ones.

## Maintenance

Versioned with the repository; changes go through the validation test. To grow it,
add items to the domain tuples in `real_contested.py`; the test enforces separability.
