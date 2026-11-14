"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import { useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { PhotoPreparationError, preparePhoto } from "@/features/reporting/image";
import type { Photo } from "@/features/reporting/types";
import { errorMessage } from "@/lib/api-client";

import { opsKeys, uploadRepairPhoto } from "./api";

export function PhotoGrid({ photos, label }: { photos: Photo[]; label: string }) {
  return (
    <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {photos.map((photo, index) => (
        <li key={photo.id} className="overflow-hidden rounded-md border border-line bg-mist">
          <a href={photo.url} target="_blank" rel="noopener noreferrer" aria-label={`Open ${label} ${index + 1} full size`}>
            {/* Signed, expiring storage URL. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={photo.thumbnail_url} alt={`${label} ${index + 1}`} loading="lazy" className="aspect-[4/3] w-full object-cover" />
          </a>
        </li>
      ))}
    </ul>
  );
}

/** Repair evidence: the camera is the primary path for officers in the field. */
export function RepairPhotoUpload({ councilId, issueId, csrfToken }: { councilId: string; issueId: string; csrfToken: string }) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const blob = await preparePhoto(file);
      setProgress(0);
      return uploadRepairPhoto(councilId, issueId, blob, csrfToken, setProgress);
    },
    onSettled: () => setProgress(null),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: opsKeys.issue(councilId, issueId) }),
  });

  return (
    <div className="space-y-2">
      <Button variant="secondary" size="lg" onClick={() => input.current?.click()} disabled={upload.isPending}>
        <Camera aria-hidden="true" />
        {upload.isPending
          ? progress === null
            ? "Preparing photo…"
            : `Uploading ${Math.round(progress * 100)}%`
          : "Add repair photo"}
      </Button>
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        className="sr-only"
        aria-label="Add a repair photo"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) upload.mutate(file);
          event.target.value = "";
        }}
      />
      {upload.isError ? (
        <Alert tone="error">
          {upload.error instanceof PhotoPreparationError ? upload.error.message : errorMessage(upload.error)}
        </Alert>
      ) : null}
    </div>
  );
}
