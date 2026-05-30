"""Deterministic graph routing where the walked path *is* the receipt."""

from __future__ import annotations

from itertools import pairwise

import networkx as nx

from ai_playground.core.errors import CompositionError
from ai_playground.core.node import Signature
from ai_playground.core.proof import ProofObject


class KnowledgeGraph:
    """Directed graph where every edge is attributed to a signing source."""

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    def add_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        *,
        source_node_id: str,
        signing_key: bytes,
    ) -> None:
        self._graph.add_edge(
            subject,
            obj,
            predicate=predicate,
            source_node_id=source_node_id,
            signing_key=signing_key,
        )

    def route(self, start: str, end: str) -> ProofObject:
        try:
            path = nx.shortest_path(self._graph, start, end)
        except nx.NetworkXNoPath:
            raise CompositionError(f"no route from {start!r} to {end!r}") from None
        except nx.NodeNotFound as exc:
            raise CompositionError(str(exc)) from exc

        chain: list[Signature] = []
        for u, v in pairwise(path):
            data = self._graph[u][v]
            sig = Signature.sign(
                node_id=data["source_node_id"],
                signing_key=data["signing_key"],
                payload=(u, data["predicate"]),
                result=v,
            )
            chain.append(sig)
        return ProofObject(output=path[-1], chain=tuple(chain))

    def order(self) -> int:
        return self._graph.number_of_nodes()

    def size(self) -> int:
        return self._graph.number_of_edges()
