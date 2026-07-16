"""Settlement queue: the seam between "trigger a settle" and "do the settle".

Two implementations behind one Protocol:

  - `InlineSettlementQueue` — runs the job synchronously in-process. The dev /
    single-instance / test default; no external infrastructure.
  - `CloudTasksSettlementQueue` — pushes the job onto Google Cloud Tasks, which
    delivers it as an HTTP POST to the worker endpoint. The production path on GCP
    (services-roadmap), so a Cloud Run request returns immediately and the worker
    absorbs the `(k+1)`-generation settle.

Swapping `DEQUORUM_SETTLEMENT_QUEUE` from `inline` to `cloudtasks` is the only
change to move from dev to a real async pipeline.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from dequorum.core.errors import CompositionError
from dequorum.worker.settlement import SettlementJob


class SettlementQueue(Protocol):
    def enqueue(self, job: SettlementJob) -> None: ...


class InlineSettlementQueue:
    """Run settlement synchronously. Blocks the caller for the full settle, so it's
    for dev / single instance / tests — not high request volume."""

    def __init__(self, runner: Callable[[SettlementJob], object]) -> None:
        self._runner = runner

    def enqueue(self, job: SettlementJob) -> None:
        self._runner(job)


@dataclass(frozen=True, slots=True)
class CloudTasksConfig:
    project: str
    location: str
    queue: str
    worker_url: str
    # OIDC service account Cloud Tasks signs the request as (verified by the worker
    # at the infra layer); empty disables OIDC.
    service_account_email: str = ""
    # Shared operator key forwarded as a header so the worker's `require_operator`
    # guard accepts the delivery (until OIDC verification replaces it).
    operator_key: str = ""


class CloudTasksSettlementQueue:
    """Enqueue settlement jobs onto Cloud Tasks → HTTP POST to the worker endpoint.

    Requires `google-cloud-tasks` (the `cloudtasks` extra). Lazily imported so the
    dependency is only needed where this queue is actually selected."""

    def __init__(self, config: CloudTasksConfig) -> None:
        self._cfg = config

    def enqueue(self, job: SettlementJob) -> None:
        try:
            from google.cloud import tasks_v2
        except ImportError as exc:  # pragma: no cover - exercised only without the dep
            raise CompositionError(
                "CloudTasksSettlementQueue requires google-cloud-tasks; install the "
                "'cloudtasks' extra (uv sync --extra cloudtasks)"
            ) from exc

        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(
            self._cfg.project, self._cfg.location, self._cfg.queue
        )
        headers = {"Content-Type": "application/json"}
        if self._cfg.operator_key:
            headers["X-Operator-Key"] = self._cfg.operator_key
        http_request: dict = {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": self._cfg.worker_url,
            "headers": headers,
            "body": json.dumps(job.to_dict()).encode(),
        }
        if self._cfg.service_account_email:
            http_request["oidc_token"] = {
                "service_account_email": self._cfg.service_account_email
            }
        client.create_task(parent=parent, task={"http_request": http_request})
