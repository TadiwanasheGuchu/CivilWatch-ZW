import { describe, expect, it } from "vitest";

import { type BoundaryFeature, boundaryBBox, formatDistance } from "./api";

describe("boundaryBBox", () => {
  it("covers every polygon of a MultiPolygon", () => {
    const feature: BoundaryFeature = {
      type: "Feature",
      id: "x",
      properties: { id: "x", slug: "x", name: "X", is_sample: true },
      geometry: {
        type: "MultiPolygon",
        coordinates: [
          [[[31.0, -17.9], [31.1, -17.9], [31.1, -17.8], [31.0, -17.9]]],
          [[[30.5, -18.2], [30.6, -18.2], [30.6, -18.1], [30.5, -18.2]]],
        ],
      },
    };
    expect(boundaryBBox(feature)).toEqual([30.5, -18.2, 31.1, -17.8]);
  });
});

describe("formatDistance", () => {
  it.each([
    [12.4, "12 m away"],
    [999, "999 m away"],
    [1500, "1.5 km away"],
  ])("formats %s", (metres, expected) => {
    expect(formatDistance(metres)).toBe(expected);
  });
});
