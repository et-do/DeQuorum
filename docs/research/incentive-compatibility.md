# Incentive-compatibility: what reliance-grounded payment does and does not guarantee

A faithful *attribution* score is not automatically a well-behaved *payment*. This
note states precisely which incentive properties DeQuorum's payout has, which it does
not, and what a fuller mechanism-design treatment would require — so the paper claims
neither too much nor too little. Companion to [methodology.md](methodology.md) §
Limitations and [WHITEPAPER.md](../WHITEPAPER.md) §8.6.

## Two different questions people mean by "incentive-compatible"

1. **Strategy-proofness over reported types** (mechanism design). Agents report
   private values/costs; the mechanism is incentive-compatible if truthful reporting
   is a dominant strategy (Myerson 1981; VCG). Han et al. 2025 (*Do Data Valuations
   Make Good Data Prices?*, arXiv:2504.05563) show that using a valuation score
   (Leave-One-Out, Data Shapley) *directly as a price* violates this — it fails to
   elicit truthful cost reports — and that the Myerson payment is the minimal truthful
   fix.
2. **Manipulation-resistance of the value measure.** Given a fixed measurement rule,
   can an agent profit by gaming *what they submit* (duplicates, padding, paraphrase,
   sybils/collusion) rather than by misreporting a type?

These are distinct, and conflating them is a common error. DeQuorum's exposure is
mostly (2), not (1).

## DeQuorum elicits no reports — so the pricing critique does not transfer directly

The Han et al. critique targets markets where a seller **reports a private cost/value**
and the mechanism must be strategy-proof in that report. DeQuorum has no such report:
contributors submit content; the network **measures ex post** how much each
contribution causally improved answers (reliance-grounded credit) and splits realized
revenue by that measure. There is no cost/value message to misstate, so
"LOO/Shapley are not truthful prices" — a statement about report-based pricing — does
not apply as stated. Claiming we "inherit the Myerson problem" would be imprecise.

## What we *do* claim (manipulation-resistance, partially proven)

Because credit is marginal, several submit-side manipulations are unprofitable **by
construction**, each encoded as a deterministic test (§8.6, `attribution/`):

- **Duplication** — a near-duplicate carries ~0 marginal value, so it does not raise a
  contributor's share (unlike per-citation credit).
- **Padding** — an off-topic contribution earns negligible marginal credit.
- **Paraphrase / collusion** — a reworded copy, including under a second account,
  cannot raise the combined Shapley share, because coalition value saturates once the
  underlying fact is present.

These are the incentive properties the paper is entitled to assert, and only these.

## What remains open (stated, not hidden)

- **Untested manipulations.** Strategic *content-splitting* (spreading one fact across
  many contributions to farm marginal credit), timing/ordering games, and collusion
  patterns beyond the pairwise case tested are not yet evaluated. We do not claim
  robustness to them.
- **Payment strategy-proofness, if we ever elicit reports.** If DeQuorum later lets
  contributors set asks/reserve prices, or hosts bid, the mechanism becomes
  report-based and the Han et al. result *does* bite: the payment rule would then need
  a Myerson/VCG-style construction over reliance credit to stay truthful. Designing
  that — a strategy-proof payment whose allocation is the reliance-grounded value — is
  the concrete open mechanism-design problem, and a natural EC-venue contribution.
- **Budget balance vs. truthfulness tension.** DeQuorum's split is exactly
  budget-balanced (conserves realized revenue). VCG is generally *not* budget-balanced;
  a truthful, budget-balanced payment over reliance credit would have to navigate the
  Green–Laffont impossibility, i.e. accept an approximation. This trade-off is
  unresolved and we flag it rather than paper over it.

## Bottom line for the paper

Lead with the **measurement** claim (reliance-grounded credit is faithful where
resemblance/coverage are not) and the **manipulation-resistance** it buys. Treat
report-based strategy-proofness as explicitly out of scope for the current mechanism
and as the sharpest open problem — cited to Han et al. 2025 and the VCG/Myerson
line — not as a solved property.
