"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { SessionData } from "@/features/authentication/types";
import { errorMessage } from "@/lib/api-client";

import { removePhoto, reportKeys, uploadPhoto } from "./api";
import { MAX_PHOTOS } from "./draft";
import { PhotoPreparationError, preparePhoto } from "./image";
import type { IssueDetail } from "./types";

interface ReportPhotosProps {
  issue: IssueDetail;
  /** Present when the reporter may still add or remove photos. */
  editableBy: SessionData | null;
}

export function ReportPhotos({ issue, editableBy }: ReportPhotosProps) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: reportKeys.detail(issue.id) });
    void queryClient.invalidateQueries({ queryKey: reportKeys.mineRoot });
  };

  const add = useMutation({
    mutationFn: async (file: File) => {
      const blob = await preparePhoto(file);
      setProgress(0);
      return uploadPhoto(issue.id, blob, editableBy!.csrf_token, setProgress);
    },
    onSettled: () => setProgress(null),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (photoId: string) => removePhoto(issue.id, photoId, editableBy!.csrf_token),
    onSettled: () => setConfirming(null),
    onSuccess: refresh,
  });

  const error = add.error ?? remove.error;
  if (!issue.photos.length && !editableBy) return null;

  return (
    <section aria-labelledby="photos-heading" className="space-y-3">
      <h2 id="photos-heading" className="text-lg font-semibold">
        Photos
      </h2>
      {issue.photos.length ? (
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {issue.photos.map((photo, index) => (
            <li key={photo.id} className="relative overflow-hidden rounded-md border border-line bg-mist">
              <a href={photo.url} target="_blank" rel="noopener noreferrer" aria-label={`Open photo ${index + 1} full size`}>
                {/* Signed, expiring storage URL. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photo.thumbnail_url} alt={`Photo ${index + 1} of the problem`} loading="lazy" className="aspect-[4/3] w-full object-cover" />
              </a>
              {editableBy ? (
                confirming === photo.id ? (
                  <div className="absolute inset-x-0 bottom-0 flex gap-1 bg-surface/95 p-1">
                    <Button className="flex-1 bg-red-text text-white hover:bg-red-text/90" onClick={() => remove.mutate(photo.id)} disabled={remove.isPending}>
                      Remove
                    </Button>
                    <Button variant="ghost" onClick={() => setConfirming(null)}>
                      Keep
                    </Button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirming(photo.id)}
                    className="absolute top-1 right-1 grid size-11 place-items-center rounded-md bg-surface/90 text-red-text"
                    aria-label={`Remove photo ${index + 1}`}
                  >
                    <Trash2 aria-hidden="true" className="size-5" />
                  </button>
                )
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate">No photos yet.</p>
      )}

      {editableBy && issue.photos.length < MAX_PHOTOS ? (
        <>
          <Button variant="secondary" onClick={() => input.current?.click()} disabled={add.isPending}>
            <ImagePlus aria-hidden="true" />
            {add.isPending ? (progress === null ? "Preparing photo…" : `Uploading ${Math.round(progress * 100)}%`) : "Add a photo"}
          </Button>
          <input
            ref={input}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            aria-label="Add a photo to this report"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) add.mutate(file);
              event.target.value = "";
            }}
          />
        </>
      ) : null}
      {error ? (
        <Alert tone="error">
          {error instanceof PhotoPreparationError ? error.message : errorMessage(error)}
        </Alert>
      ) : null}
    </section>
  );
}
