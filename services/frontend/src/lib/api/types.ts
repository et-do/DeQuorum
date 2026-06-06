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

export interface Category {
	category_id: string;
	parent_id: string | null;
	display_name: string;
	depth: number;
	description: string;
	is_routable: boolean;
	specialty_tags: string[];
	example_questions: string[];
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

/**
 * Minimal envelope persisted alongside each chat response. The backend
 * records which category grounded the answer and which contributions
 * (if any) were retrieved, for the attribution ledger. The user-facing
 * UI does not surface this — see /docs/architecture/whitepaper.md.
 */
export interface ChatResponseEnvelope {
	query: string;
	category_id: string | null;
	retrieved_contribution_ids: string[];
	final_answer: string;
}

export interface ContributionsQuery {
	status?: Status;
	contributor?: string;
	category?: string;
	q?: string;
}

// --- chat sessions ---

export type ChatRole = "user" | "network";

export interface ChatSession {
	session_id: string;
	contributor_id: string;
	title: string;
	created_at: number;
	updated_at: number;
}

export interface ChatMessage {
	message_id: string;
	session_id: string;
	role: ChatRole;
	content: string;
	response: ChatResponseEnvelope | null;
	created_at: number;
	sequence_number: number;
}

export interface ChatSessionDetail extends ChatSession {
	messages: ChatMessage[];
}

// --- comments on contributions ---

export interface LineAnchor {
	start_line: number;
	end_line: number;
}

export interface Comment {
	comment_id: string;
	contribution_id: string;
	parent_comment_id: string | null;
	author_id: string;
	body: string;
	line_anchor: LineAnchor | null;
	created_at: number;
	redacted_at: number | null;
	redacted_by: string | null;
	replaces_comment_id: string | null;
	signature: Signature;
}

export interface CreateCommentPayload {
	body: string;
	parent_comment_id?: string | null;
	line_anchor?: LineAnchor | null;
	replaces_comment_id?: string | null;
}

export type ChatStreamEvent =
	| { stage: string }
	| { chunk: string }
	| { done: ChatResponseEnvelope }
	| { title: string }
	| { error: string };
