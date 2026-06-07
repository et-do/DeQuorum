# Novelty grounding benchmark

Model: `qwen2.5-coder:7b` · invented facts: 8

Each fact is fictional, so the base condition controls for memorization (it should score near zero). The grounded condition supplies the fact as a reference note. The gap is the grounding lift on knowledge the model cannot have pretrained on.

- mean gold-fact recall, **base model**: 0.229
- mean gold-fact recall, **grounded**: 0.917
- **grounding lift: +0.688**

| Query | base | grounded |
| --- | ---: | ---: |
| How large are frame headers in the Halberd transport protocol, and ... | 0.33 | 1.00 |
| In Pyrolib, what does pyro.bind retry on and what is its initial ba... | 0.00 | 0.67 |
| What Byzantine fault threshold does the Marrow-Quist bound assume? | 0.50 | 1.00 |
| What happens when vault.seal_threshold exceeds 0.8 in Cindervault? | 0.00 | 1.00 |
| What do zelanocytes secrete, and in which gland are they found? | 0.00 | 1.00 |
| Where does the GX-9 imaging standard store its provenance tag? | 0.00 | 0.67 |
| What is the default value of merge.fanout in the Drelb planner? | 0.50 | 1.00 |
| Per Quenby's law, how deep can the store buffer be relative to asso... | 0.50 | 1.00 |
