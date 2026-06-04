import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getHealthz, REVIEW_STREAM_URL, runQuery } from "./client";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => {
	fetchMock.mockReset();
});

function jsonResponse(body: unknown, status = 200) {
	return new Response(JSON.stringify(body), {
		status,
		headers: { "Content-Type": "application/json" },
	});
}

describe("api client", () => {
	it("getHealthz hits /api/v1/healthz and returns parsed JSON", async () => {
		fetchMock.mockResolvedValueOnce(jsonResponse({ status: "ok" }));
		const r = await getHealthz();
		expect(r).toEqual({ status: "ok" });
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/healthz",
			expect.objectContaining({
				headers: expect.objectContaining({
					"Content-Type": "application/json",
				}),
			}),
		);
	});

	it("runQuery posts JSON body with the text payload", async () => {
		fetchMock.mockResolvedValueOnce(
			jsonResponse({
				query: "x",
				routing: {
					method: "keyword",
					matched_tags: [],
					fallback_used: false,
					threshold: 1,
					selected: [],
				},
				experts: [],
				composition: { strategy: "pick_best", chosen: [] },
				final_answer: "ok",
				ledger: {},
			}),
		);
		const r = await runQuery("hello world");
		expect(r.final_answer).toBe("ok");
		const [, init] = fetchMock.mock.calls[0]!;
		expect(init.method).toBe("POST");
		expect(JSON.parse(init.body as string)).toEqual({ text: "hello world" });
	});

	it("throws ApiError on non-2xx with detail surfaced", async () => {
		fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "invalid status" }, 400));
		await expect(getHealthz()).rejects.toMatchObject({
			status: 400,
			detail: "invalid status",
		});
		// Also verify it is the ApiError type.
		await fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "x" }, 500));
		try {
			await getHealthz();
		} catch (e) {
			expect(e).toBeInstanceOf(ApiError);
		}
	});

	it("REVIEW_STREAM_URL points at the SSE endpoint", () => {
		expect(REVIEW_STREAM_URL).toBe("/api/v1/review/stream");
	});
});
