/**
 * Thin fetch wrapper around the FastAPI JSON API.
 *
 * All requests go through `/api/v1/*`; Caddy strips the `/api` prefix and
 * forwards to the FastAPI app, which serves under `/v1/*`. In dev outside
 * compose, Vite's proxy handles the same forwarding.
 *
 * Errors throw `ApiError` so callers can branch on status code; the body
 * is parsed once and surfaced via `.detail`.
 */

import type {
	AgreementInfo,
	AppMeta,
	Category,
	Contribution,
	ContributionsQuery,
	ContributionWithVotes,
	Contributor,
	ContributorDetail,
	Expert,
	LineageDetail,
	NewContributorResponse,
	QueryResponse,
	SubmitContributionResponse,
	VoteOutcome,
} from "./types";

const API_BASE = "/api/v1";

export class ApiError extends Error {
	status: number;
	detail: unknown;
	constructor(status: number, detail: unknown, message: string) {
		super(message);
		this.status = status;
		this.detail = detail;
	}
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, {
		...init,
		headers: {
			"Content-Type": "application/json",
			...(init.headers || {}),
		},
	});
	if (!res.ok) {
		let detail: unknown = res.statusText;
		try {
			const body = await res.json();
			detail = body.detail ?? body;
		} catch {
			// non-JSON error body — leave detail as statusText
		}
		throw new ApiError(
			res.status,
			detail,
			typeof detail === "string" ? detail : `HTTP ${res.status}`,
		);
	}
	if (res.status === 204) return undefined as T;
	return res.json() as Promise<T>;
}

function qs(params: object): string {
	const search = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v === undefined || v === null || v === "") continue;
		search.append(k, String(v));
	}
	const s = search.toString();
	return s ? `?${s}` : "";
}

// ---- meta ----
export const getHealthz = () => request<{ status: "ok" }>("/healthz");
export const getMeta = () => request<AppMeta>("/meta");
export const getAgreement = () => request<AgreementInfo>("/agreement");

// ---- experts ----
export const listExperts = () => request<Expert[]>("/experts");

// ---- contributions ----
export const listContributions = (params: ContributionsQuery = {}) =>
	request<Contribution[]>(`/contributions${qs(params)}`);

export const getContribution = (id: string) =>
	request<ContributionWithVotes>(`/contributions/${encodeURIComponent(id)}`);

export const submitContribution = (payload: {
	expert_id: string;
	text: string;
	citations?: string[];
	primary_category_id?: string;
}) =>
	request<SubmitContributionResponse>("/contributions", {
		method: "POST",
		body: JSON.stringify(payload),
	});

export const castVote = (
	contributionId: string,
	payload: { voter_id: string; score: -1 | 0 | 1 },
) =>
	request<VoteOutcome>(`/contributions/${encodeURIComponent(contributionId)}/votes`, {
		method: "POST",
		body: JSON.stringify(payload),
	});

// ---- review ----
export const getReviewQueue = () => request<ContributionWithVotes[]>("/review");

/** SSE URL — pass to `new EventSource(REVIEW_STREAM_URL)`. */
export const REVIEW_STREAM_URL = `${API_BASE}/review/stream`;

// ---- contributors ----
export const listContributors = () => request<Contributor[]>("/contributors");

export const getContributor = (id: string) =>
	request<ContributorDetail>(`/contributors/${encodeURIComponent(id)}`);

export const createContributor = (payload: { display_name: string; email?: string }) =>
	request<NewContributorResponse>("/contributors", {
		method: "POST",
		body: JSON.stringify(payload),
	});

// ---- categories ----
export const listCategories = () => request<Category[]>("/categories");

// ---- lineages ----
export const getLineage = (id: string) =>
	request<LineageDetail>(`/lineages/${encodeURIComponent(id)}`);

// ---- queries ----
export const runQuery = (text: string) =>
	request<QueryResponse>("/queries", {
		method: "POST",
		body: JSON.stringify({ text }),
	});
