import { describe, expect, it, vi } from "vitest";

import { emptyDraft, hasContent, type ReportDraft } from "./draft";
import { submitDraft, toNewReport } from "./submit-draft";
import type { OwnIssue, Photo } from "./types";

function completeDraft(photoCount = 2): ReportDraft {
  return {
    ...emptyDraft(),
    categoryId: "cat",
    title: "  Pothole on Main Road ",
    description: "Deep pothole in the left lane.",
    councilId: "council",
    latitude: -17.83,
    longitude: 31.05,
    locationDescription: "  ",
    visibility: "PUBLIC",
    photos: Array.from({ length: photoCount }, (_, i) => ({
      id: `local-${i}`,
      blob: new Blob([`photo ${i}`], { type: "image/jpeg" }),
      uploadedPhotoId: null,
    })),
  };
}

const issue = { id: "issue-1" } as OwnIssue;
const photo = (id: string) => ({ id }) as Photo;

describe("toNewReport", () => {
  it("trims text and turns an empty location description into null", () => {
    expect(toNewReport(completeDraft())).toMatchObject({
      title: "Pothole on Main Road",
      location_description: null,
      visibility: "PUBLIC",
    });
  });

  it("refuses an incomplete draft", () => {
    expect(() => toNewReport({ ...completeDraft(), latitude: null })).toThrow();
  });
});

describe("submitDraft", () => {
  it("creates the report once, uploads every photo and saves progress", async () => {
    const saveDraft = vi.fn().mockResolvedValue(undefined);
    const submitReport = vi.fn().mockResolvedValue(issue);
    const uploadPhoto = vi.fn().mockImplementation(async (_id, _blob, progress) => {
      progress(1);
      return photo(`server-${uploadPhoto.mock.calls.length}`);
    });
    const onPhotoProgress = vi.fn();
    const result = await submitDraft(completeDraft(), { submitReport, uploadPhoto, saveDraft, onPhotoProgress });
    expect(result.failedPhotoIds).toEqual([]);
    expect(submitReport).toHaveBeenCalledTimes(1);
    expect(uploadPhoto).toHaveBeenCalledTimes(2);
    expect(result.draft.submittedIssueId).toBe("issue-1");
    expect(result.draft.photos.every((p) => p.uploadedPhotoId)).toBe(true);
    expect(saveDraft).toHaveBeenCalledTimes(3);
    expect(onPhotoProgress).toHaveBeenCalledWith("local-0", 1);
  });

  it("leaves the draft untouched when the report cannot be created", async () => {
    const draft = completeDraft();
    const saveDraft = vi.fn();
    await expect(
      submitDraft(draft, {
        submitReport: vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
        uploadPhoto: vi.fn(),
        saveDraft,
      }),
    ).rejects.toThrow("Failed to fetch");
    expect(saveDraft).not.toHaveBeenCalled();
    expect(draft.submittedIssueId).toBeNull();
  });

  it("reports failed photos and retries only those, never creating a second report", async () => {
    const saveDraft = vi.fn().mockResolvedValue(undefined);
    const submitReport = vi.fn().mockResolvedValue(issue);
    const failing = vi
      .fn()
      .mockResolvedValueOnce(photo("server-a"))
      .mockRejectedValueOnce(new TypeError("Network request failed"));
    const first = await submitDraft(completeDraft(), { submitReport, uploadPhoto: failing, saveDraft });
    expect(first.failedPhotoIds).toEqual(["local-1"]);
    expect(first.lastError).toBeInstanceOf(TypeError);

    const retryUpload = vi.fn().mockResolvedValue(photo("server-b"));
    const second = await submitDraft(first.draft, { submitReport, uploadPhoto: retryUpload, saveDraft });
    expect(submitReport).toHaveBeenCalledTimes(1);
    expect(retryUpload).toHaveBeenCalledTimes(1);
    expect(retryUpload.mock.calls[0]?.[0]).toBe("issue-1");
    expect(second.failedPhotoIds).toEqual([]);
  });
});

describe("hasContent", () => {
  it("is false for a fresh draft and true once anything is entered", () => {
    expect(hasContent(emptyDraft())).toBe(false);
    expect(hasContent({ ...emptyDraft(), title: "x" })).toBe(true);
  });
});
