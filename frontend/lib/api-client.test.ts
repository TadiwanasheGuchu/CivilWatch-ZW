import { describe, expect, it } from "vitest";

import { ApiError, toApiError } from "./api-client";

describe("toApiError", () => {
  it("maps the API error envelope", async () => {
    const response = new Response(
      JSON.stringify({
        error: { code: "not_found", message: "Missing", details: null, request_id: "abc12345" },
      }),
      { status: 404 },
    );
    const error = await toApiError(response);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(404);
    expect(error.code).toBe("not_found");
    expect(error.message).toBe("Missing");
    expect(error.requestId).toBe("abc12345");
  });

  it("falls back safely when the body is not an envelope", async () => {
    const response = new Response("<html>Bad gateway</html>", {
      status: 502,
      headers: { "X-Request-ID": "req-99999999" },
    });
    const error = await toApiError(response);
    expect(error.code).toBe("unexpected_response");
    expect(error.status).toBe(502);
    expect(error.requestId).toBe("req-99999999");
  });
});
