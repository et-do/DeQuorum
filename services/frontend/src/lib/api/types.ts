/**
 * TypeScript shapes mirroring the FastAPI JSON responses at /v1/*.
 *
 * Hand-typed for now (one place, easy to keep in sync). When the API
 * stabilizes, switch to `openapi-typescript` against /openapi.json.
 */

export type Status = "pending" | "approved" | "rejected" | "superseded";

export interface Signature {
	node_id: string;
	input_hash: string;
	output_hash: string;
	digest: string;
}

export interface Expert {
	expert_id: string;
	display_name: string;
	specialty_tags: string[];
	prompt_digest: string;
	example_questions: string[];
}

export interface Vote {
	vote_id: string;
	contribution_id: string;
	voter_id: string;
	score: -1 | 0 | 1;
	signature: Signature;
}

export interface Contribution {
	contribution_id: string;
	lineage_id: string;
	version_number: number;
	parent_version: number | null;
	expert_id: string;
	contributor_id: string;
	primary_category_id: string;
	text: string;
	citations: string[];
	signature: Signature;
	status: Status | null;
	tally: number;
}

export interface ContributionWithVotes extends Contribution {
	votes: Vote[];
}

export interface DuplicateCandidate {
	contribution_id: string;
	lineage_id: string;
	score: number;
	text_preview: string;
}

export interface DuplicateCheck {
	band: string;
	suggested_action: string;
	top_candidates: DuplicateCandidate[];
}

export interface SubmitContributionResponse extends Contribution {
	duplicate_check: DuplicateCheck;
}

export interface Contributor {
	contributor_id: string;
	display_name: string;
	public_key_hex: string;
	tier: number;
	tier_name: string;
	agreement_version: string;
	vote_weight: number;
	daily_submission_cap: number;
	has_email: boolean;
	created_at: number;
}

export interface ContributorDetail extends Contributor {
	contributions: Contribution[];
}

export interface NewContributorResponse extends Contributor {
	private_key_hex: string;
	warning: string;
}

export interface Category {
	category_id: string;
	parent_id: string | null;
	display_name: string;
	depth: number;
	description: string;
}

export interface LineageDetail {
	lineage_id: string;
	current_contribution_id: string | null;
	versions: Contribution[];
}

export interface VoteOutcome {
	outcome: Record<string, unknown>;
	tally: number;
	status: Status;
}

export interface AppMeta {
	database_url: string;
	ollama_host: string;
	use_mock: boolean;
	approval_threshold: number;
	rejection_threshold: number;
	valid_statuses: Status[];
}

export interface AgreementInfo {
	version: string;
	text: string;
	effective_at: number;
	tiers: { value: number; name: string }[];
}

export interface QueryResponse {
	query: string;
	routing: {
		method: string;
		matched_tags: string[];
		fallback_used: boolean;
		threshold: number;
		selected: { expert_id: string; score: number }[];
	};
	experts: {
		expert_id: string;
		routing_score: number;
		answer: string;
		signature: Signature;
		retrieved: {
			contribution_id: string;
			contributor_id: string;
			score: number;
			text: string;
			citations: string[];
		}[];
	}[];
	composition: { strategy: string; chosen: string[] };
	final_answer: string;
	ledger: Record<string, number>;
}

export interface ContributionsQuery {
	expert?: string;
	status?: Status;
	contributor?: string;
	category?: string;
	q?: string;
}
