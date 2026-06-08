"""Small-scale LoRA distillation PoC + leave-one-contributor-out attribution.

Pure helpers (dataset construction, contributor exclusion, attribution
delta) are import-light and unit-tested. The training/generation functions
lazy-import transformers/peft/torch and are exercised by the
`dequorum distill-poc` command, which runs the actual (compute-heavy)
experiment.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from dequorum.retrieval import ScoredContribution


@dataclass(frozen=True, slots=True)
class TrainingExample:
    """One (instruction, target) pair distilled from a contribution, tagged
    with the contributor so we can trace which examples taught the model."""

    prompt: str
    completion: str
    contributor_id: str
    contribution_id: str


def build_examples(
    query: str, retrieved: Sequence[ScoredContribution]
) -> list[TrainingExample]:
    """Distill (query → contribution text) examples from what retrieval would
    have surfaced. Training on these moves the retrieved knowledge into the
    weights; each example carries its contributor for attribution."""
    return [
        TrainingExample(
            prompt=query,
            completion=sc.contribution.text,
            contributor_id=sc.contribution.contributor_id,
            contribution_id=sc.contribution.contribution_id,
        )
        for sc in retrieved
    ]


def exclude_contributor(
    examples: Sequence[TrainingExample], contributor_id: str
) -> list[TrainingExample]:
    """Training set with one contributor's examples removed — the
    leave-one-contributor-out condition for training-data attribution."""
    return [e for e in examples if e.contributor_id != contributor_id]


def attribution_delta(
    *,
    recall_with: float,
    recall_without: float,
    recall_base: float,
) -> dict[str, float]:
    """Quantify how much a contributor's training examples are responsible
    for a fact being in the weights.

    learned_gain     = recall_with - recall_base   (corpus → weights at all)
    contributor_gain = recall_with - recall_without (this contributor's share)
    attributable     = contributor_gain / learned_gain when there was a gain.
    """
    learned_gain = recall_with - recall_base
    contributor_gain = recall_with - recall_without
    attributable = contributor_gain / learned_gain if learned_gain > 1e-9 else 0.0
    return {
        "learned_gain": learned_gain,
        "contributor_gain": contributor_gain,
        "attributable_fraction": max(0.0, min(1.0, attributable)),
    }


# --- compute-heavy training/generation (lazy ML imports) ----------------


def train_lora(
    examples: Sequence[TrainingExample],
    *,
    base_id: str,
    rank: int = 8,
    epochs: int = 3,
    lr: float = 1e-3,
    max_len: int = 256,
):
    """Train a tiny LoRA adapter on the examples. Returns (model, tokenizer).
    CPU-friendly hand-rolled loop (no datasets/Trainer dependency)."""
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(base_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.float32)
    model = get_peft_model(
        model,
        LoraConfig(
            r=rank,
            lora_alpha=rank * 2,
            target_modules=["q_proj", "v_proj"],
            task_type="CAUSAL_LM",
        ),
    )
    model.to(device)
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    for _ in range(epochs):
        for ex in examples:
            text = tok.apply_chat_template(
                [
                    {"role": "user", "content": ex.prompt},
                    {"role": "assistant", "content": ex.completion},
                ],
                tokenize=False,
            )
            enc = tok(
                text, return_tensors="pt", truncation=True, max_length=max_len
            ).to(device)
            loss = model(**enc, labels=enc["input_ids"]).loss
            loss.backward()
            opt.step()
            opt.zero_grad()
    return model, tok


def generate(model, tok, prompt: str, *, max_new_tokens: int = 64) -> str:
    import torch

    model.eval()
    text = tok.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False,
        add_generation_prompt=True,
    )
    enc = tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False)
    return tok.decode(out[0][enc["input_ids"].shape[1] :], skip_special_tokens=True)


def base_generator(base_id: str) -> Callable[[str], str]:
    """A no-adapter generator from the base model, for the baseline recall."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(base_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.float32)
    model.to(device)

    def gen(prompt: str) -> str:
        return generate(model, tok, prompt)

    return gen
