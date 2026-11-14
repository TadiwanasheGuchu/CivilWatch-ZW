"use client";

import { Camera, ImagePlus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

import { MAX_PHOTOS } from "../draft";
import { PhotoPreparationError, preparePhoto } from "../image";
import type { StepProps } from "./step-props";

export function PhotosStep({ draft, update }: StepProps) {
  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);
  const [preparing, setPreparing] = useState(0);
  const [problem, setProblem] = useState<string | null>(null);
  const room = MAX_PHOTOS - draft.photos.length;

  const previews = useMemo(
    () => draft.photos.map((photo) => ({ id: photo.id, url: URL.createObjectURL(photo.blob) })),
    [draft.photos],
  );
  useEffect(() => () => previews.forEach((preview) => URL.revokeObjectURL(preview.url)), [previews]);

  async function addFiles(files: FileList | null) {
    if (!files?.length) return;
    setProblem(null);
    const chosen = Array.from(files).slice(0, room);
    if (files.length > room) setProblem(`You can add up to ${MAX_PHOTOS} photos.`);
    setPreparing(chosen.length);
    const added = [];
    for (const file of chosen) {
      try {
        added.push({ id: crypto.randomUUID(), blob: await preparePhoto(file), uploadedPhotoId: null });
      } catch (error) {
        setProblem(error instanceof PhotoPreparationError ? error.message : "That photo could not be added.");
      } finally {
        setPreparing((count) => count - 1);
      }
    }
    if (added.length) update({ photos: [...draft.photos, ...added] });
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-navy-soft">
        Photos help the council find and judge the problem. They are optional, and we remove location
        details stored inside them.
      </p>

      {room > 0 ? (
        <div className="grid gap-2 sm:grid-cols-2">
          <Button variant="secondary" size="lg" onClick={() => cameraInput.current?.click()}>
            <Camera aria-hidden="true" />
            Take a photo
          </Button>
          <Button variant="secondary" size="lg" onClick={() => galleryInput.current?.click()}>
            <ImagePlus aria-hidden="true" />
            Choose from gallery
          </Button>
        </div>
      ) : (
        <Alert tone="info">You have added the maximum of {MAX_PHOTOS} photos.</Alert>
      )}
      <input
        ref={cameraInput}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(event) => {
          void addFiles(event.target.files);
          event.target.value = "";
        }}
      />
      <input
        ref={galleryInput}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="sr-only"
        aria-label="Choose photos from your gallery"
        data-testid="gallery-input"
        onChange={(event) => {
          void addFiles(event.target.files);
          event.target.value = "";
        }}
      />

      {preparing > 0 ? (
        <p role="status" className="text-sm text-slate">
          Preparing {preparing} photo{preparing === 1 ? "" : "s"}…
        </p>
      ) : null}
      {problem ? <Alert tone="error">{problem}</Alert> : null}

      {previews.length ? (
        <ul aria-label="Photos to send" className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {previews.map((preview, index) => (
            <li key={preview.id} className="relative overflow-hidden rounded-md border border-line bg-mist">
              {/* Local preview from the device: never uploaded until the report is sent. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview.url} alt={`Photo ${index + 1}`} className="aspect-[4/3] w-full object-cover" />
              <button
                type="button"
                onClick={() => update({ photos: draft.photos.filter((photo) => photo.id !== preview.id) })}
                className="absolute top-1 right-1 grid size-11 place-items-center rounded-md bg-surface/90 text-red-text"
                aria-label={`Remove photo ${index + 1}`}
              >
                <Trash2 aria-hidden="true" className="size-5" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
