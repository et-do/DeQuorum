from __future__ import annotations

import pytest

from dequorum.base_model import MockBaseModel
from dequorum.contribution_store import STATUS_APPROVED, ContributionStore
from dequorum.contributions import Contribution
from dequorum.core.errors import CompositionError
from dequorum.experts import Expert, ExpertRegistry
from dequorum.pipeline import Pipeline
from dequorum.retrieval import Retriever
from dequorum.router import KeywordRouter


def _expert(eid: str, tags: tuple[str, ...]) -> Expert:
    return Expert(
        expert_id=eid,
        display_name=eid.title(),
        specialty_tags=tags,
        system_prompt=f"You are {eid}.",
        signing_key=eid.encode(),
    )


def _pipeline(*experts: Expert, top_k: int = 3) -> Pipeline:
    reg = ExpertRegistry()
    for e in experts:
        reg.register(e)
    return Pipeline(
        router=KeywordRouter(reg),
        model=MockBaseModel(),
        top_k=top_k,
    )


def test_single_expert_query_returns_proof() -> None:
    p = _pipeline(_expert("py", ("python",)))
    response = p.query("python typing question")
    assert len(response.expert_answers) == 1
    assert response.expert_answers[0].expert.expert_id == "py"
    assert response.proof.chain[0].node_id == "py"
    assert response.final_answer == response.expert_answers[0].answer


def test_multi_expert_concat_strategy() -> None:
    from dequorum.composition import ConcatStrategy

    reg = ExpertRegistry()
    reg.register(_expert("py", ("python",)))
    reg.register(_expert("rs", ("rust",)))
    p = Pipeline(
        router=KeywordRouter(reg),
        model=MockBaseModel(),
        composition=ConcatStrategy(),
        top_k=3,
    )
    response = p.query("python vs rust ownership")
    expert_ids = {a.expert.expert_id for a in response.expert_answers}
    assert expert_ids == {"py", "rs"}
    assert "Py" in response.final_answer
    assert "Rs" in response.final_answer
    assert "---" in response.final_answer
    assert response.composition.strategy == "concat"


def test_pick_best_strategy_returns_single_answer() -> None:
    reg = ExpertRegistry()
    reg.register(_expert("py", ("python",)))
    reg.register(_expert("rs", ("rust",)))
    p = Pipeline(
        router=KeywordRouter(reg),
        model=MockBaseModel(),
        top_k=3,
    )  # default is PickBest
    response = p.query("python vs rust ownership")
    # Both experts were consulted (two routing matches, equal score)
    assert len(response.expert_answers) == 2
    # But only one answer wins
    assert len(response.composition.chosen) == 1
    chosen_id = response.composition.chosen[0]
    chosen_answer = next(
        a for a in response.expert_answers if a.expert.expert_id == chosen_id
    )
    assert response.final_answer == chosen_answer.answer


def test_ledger_credits_each_consulted_expert() -> None:
    p = _pipeline(
        _expert("py", ("python",)),
        _expert("rs", ("rust",)),
    )
    p.query("python rust")
    totals = p.ledger.totals()
    assert totals == {"py": 1, "rs": 1}


def test_ledger_accumulates_across_queries() -> None:
    p = _pipeline(_expert("py", ("python",)))
    p.query("python question one")
    p.query("python question two")
    assert p.ledger.totals() == {"py": 2}


def test_empty_query_raises() -> None:
    p = _pipeline(_expert("py", ("python",)))
    with pytest.raises(CompositionError):
        p.query("   ")


def test_no_experts_raises_composition_error() -> None:
    p = Pipeline(
        router=KeywordRouter(ExpertRegistry(), fallback_to_all=False),
        model=MockBaseModel(),
    )
    with pytest.raises(CompositionError, match="no qualified expert"):
        p.query("anything")


def test_proof_chain_is_signed_per_expert() -> None:
    p = _pipeline(
        _expert("py", ("python",)),
        _expert("rs", ("rust",)),
    )
    response = p.query("python rust")
    digests = {sig.digest for sig in response.proof.chain}
    assert len(digests) == 2  # distinct signatures
    for sig, answer in zip(response.proof.chain, response.expert_answers, strict=True):
        assert sig.node_id == answer.expert.expert_id


def test_seed_registry_smoke() -> None:
    from dequorum.seed_experts import build_seed_registry

    reg = build_seed_registry()
    assert len(reg) >= 5
    assert "python-typing" in reg


# --- Retrieval-augmented pipeline -----------------------------------------


def _contribution(expert_id: str, text: str) -> Contribution:
    return Contribution.create(
        expert_id=expert_id,
        contributor_id=expert_id,
        text=text,
        citations=("https://example.com",),
        signing_key=expert_id.encode(),
    )


def _pipeline_with_retrieval(*experts: Expert, store: ContributionStore) -> Pipeline:
    reg = ExpertRegistry()
    for e in experts:
        reg.register(e)
    return Pipeline(
        router=KeywordRouter(reg),
        model=MockBaseModel(),
        retriever=Retriever(store),
        top_k=3,
        retrieve_top_k=3,
    )


def test_retrieval_appends_contribution_signatures_to_chain() -> None:
    store = ContributionStore()
    store.add(
        _contribution("py", "Typing a generator uses Generator[Y, S, R]"),
        status=STATUS_APPROVED,
    )
    p = _pipeline_with_retrieval(_expert("py", ("python",)), store=store)
    response = p.query("python typing generator")
    assert len(response.proof.chain) == 2  # 1 contribution sig + 1 expert sig
    # Order: contributions before expert sig
    answer = response.expert_answers[0]
    assert response.proof.chain[0] == answer.retrieved[0].contribution.signature
    assert response.proof.chain[1] == answer.signature


def test_ledger_credits_contributors_in_addition_to_experts() -> None:
    store = ContributionStore()
    store.add(_contribution("py", "fact A about typing"), status=STATUS_APPROVED)
    store.add(_contribution("py", "fact B about typing"), status=STATUS_APPROVED)
    p = _pipeline_with_retrieval(_expert("py", ("python",)), store=store)
    p.query("python typing")
    totals = p.ledger.totals()
    # 2 contributions + 1 expert sig = py gets credited 3 times (all share id "py")
    assert totals["py"] == 3


def test_retrieval_with_no_matching_contributions_is_graceful() -> None:
    store = ContributionStore()
    store.add(_contribution("py", "completely unrelated text"), status=STATUS_APPROVED)
    p = _pipeline_with_retrieval(_expert("py", ("python",)), store=store)
    # query has no token overlap with contribution → no retrieval, no augmentation
    response = p.query("python")
    # chain has just the expert sig
    assert len(response.proof.chain) == 1


def test_retrieved_attached_to_expert_answer() -> None:
    store = ContributionStore()
    c = _contribution("py", "typing fact one")
    store.add(c, status=STATUS_APPROVED)
    p = _pipeline_with_retrieval(_expert("py", ("python",)), store=store)
    response = p.query("python typing")
    assert len(response.expert_answers) == 1
    assert len(response.expert_answers[0].retrieved) == 1
    assert response.expert_answers[0].retrieved[0].contribution == c
