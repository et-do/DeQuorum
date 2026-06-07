# Distillation PoC

Base: `Qwen/Qwen2.5-0.5B-Instruct` · epochs 2 · seeded queries 5

## Corpus → weights (retrieval-suppressed gold recall)

- mean recall, base model: 0.367
- mean recall, LoRA on full corpus: 0.300
- **learned gain: -0.067**

## Attribution survives distillation

Target: 'What protocol does HTTP/3 run on?' · contributor `dq:bbf30bdd6764ad37`

- recall, base: 0.000
- recall, LoRA-all: 0.500
- recall, LoRA-without-contributor: 0.000
- **attributable fraction: 1.000** — share of the learned fact traceable to this contributor's examples via leave-one-contributor-out.
