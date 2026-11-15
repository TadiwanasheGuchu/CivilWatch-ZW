"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { EmptyState, LoadingRows } from "@/components/ui/page-states";
import { Panel } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { CouncilShell } from "@/features/council/council-shell";
import { type BoundaryResult, clearBoundary, fetchBoundaries, setBoundary } from "@/features/maps/api";
import { errorMessage, fieldErrorsFrom } from "@/lib/api-client";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

export function BoundaryView({ councilId }: { councilId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="boundary">
      {(workspace, session) =>
        session.user.is_platform_admin ? (
          <Boundary councilId={councilId} councilName={workspace.council.name} csrfToken={session.csrf_token} />
        ) : (
          <EmptyState title="Platform administrators only">Council boundaries are managed by platform administrators.</EmptyState>
        )
      }
    </CouncilShell>
  );
}

function Boundary({ councilId, councilName, csrfToken }: { councilId: string; councilName: string; csrfToken: string }) {
  const queryClient = useQueryClient();
  const fileId = useId();
  const [geometry, setGeometry] = useState<unknown>(null);
  const [fileProblem, setFileProblem] = useState<string | null>(null);
  const [source, setSource] = useState<"official" | "sample">("official");
  const [confirmRemove, setConfirmRemove] = useState(false);
  const boundaries = useQuery({
    queryKey: ["maps", "boundaries", "fresh"],
    queryFn: ({ signal }) => fetchBoundaries(signal, { fresh: true }),
  });
  const current = boundaries.data?.features.find((f) => f.properties.id === councilId);
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["maps", "boundaries"] });

  const upload = useMutation({ mutationFn: () => setBoundary(councilId, geometry, source, csrfToken), onSuccess: refresh });
  const remove = useMutation({
    mutationFn: () => clearBoundary(councilId, csrfToken),
    onSuccess: refresh,
    onSettled: () => setConfirmRemove(false),
  });
  const serverProblem = fieldErrorsFrom(upload.error).geometry;

  async function readFile(file: File | undefined) {
    setGeometry(null);
    setFileProblem(null);
    upload.reset();
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      setFileProblem("The file is larger than 5 MB. Simplify the boundary and try again.");
      return;
    }
    try {
      setGeometry(JSON.parse(await file.text()));
    } catch {
      setFileProblem("This file is not valid JSON. Export the boundary as GeoJSON.");
    }
  }

  return (
    <div className="space-y-6">
      <Panel title="Current boundary">
        {boundaries.isPending ? (
          <LoadingRows label="Loading boundary" rows={1} />
        ) : current ? (
          <p>
            {councilName} has {current.properties.is_sample ? <strong>a sample boundary</strong> : "an official boundary"}.
            {current.properties.is_sample ? " Sample boundaries are for demonstration only; upload the official one below." : null}
          </p>
        ) : (
          <p>{councilName} has no boundary. Reports can be placed anywhere in the service area.</p>
        )}
        {current ? (
          <div className="mt-3">
            {confirmRemove ? (
              <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Confirm removing the boundary">
                <span className="text-sm font-medium">Remove the boundary?</span>
                <Button className="bg-red-text text-white hover:bg-red-text/90" onClick={() => remove.mutate()} disabled={remove.isPending}>
                  Remove
                </Button>
                <Button variant="ghost" onClick={() => setConfirmRemove(false)}>Keep</Button>
              </div>
            ) : (
              <Button variant="ghost" className="text-red-text" onClick={() => setConfirmRemove(true)}>
                Remove boundary
              </Button>
            )}
            {remove.isError ? <Alert tone="error" className="mt-2">{errorMessage(remove.error)}</Alert> : null}
          </div>
        ) : null}
      </Panel>

      <Panel
        title="Upload a boundary"
        description="A GeoJSON Polygon, MultiPolygon, Feature or one-feature FeatureCollection, in WGS 84 with [longitude, latitude] coordinates."
      >
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            upload.mutate();
          }}
        >
          <div className="space-y-1.5">
            <label htmlFor={fileId} className="block text-sm font-medium">GeoJSON file</label>
            <input
              id={fileId}
              type="file"
              accept=".geojson,.json,application/geo+json,application/json"
              onChange={(event) => void readFile(event.target.files?.[0])}
              className="block w-full text-sm file:mr-3 file:min-h-11 file:rounded-[var(--radius-control)] file:border file:border-line file:bg-surface file:px-4 file:font-medium"
            />
          </div>
          <Field label="Source" hint="Use sample only for demonstrations. Sample boundaries are labelled as such everywhere.">
            <Select value={source} onChange={(e) => setSource(e.target.value as "official" | "sample")}>
              <option value="official">Official boundary from the council</option>
              <option value="sample">Sample (demonstration only)</option>
            </Select>
          </Field>
          {fileProblem ? <Alert tone="error">{fileProblem}</Alert> : null}
          {serverProblem ? <Alert tone="error" title="The boundary was not saved">{serverProblem}</Alert> : null}
          {upload.isError && !serverProblem ? <Alert tone="error">{errorMessage(upload.error)}</Alert> : null}
          {upload.isSuccess ? <UploadResult result={upload.data} /> : null}
          <Button type="submit" disabled={!geometry || upload.isPending}>
            {upload.isPending ? "Checking and saving…" : "Save boundary"}
          </Button>
        </form>
      </Panel>
    </div>
  );
}

function UploadResult({ result }: { result: BoundaryResult }) {
  return (
    <Alert tone="success" title="Boundary saved">
      {result.area_km2.toLocaleString("en-GB")} km², {result.vertex_count.toLocaleString("en-GB")} points
      {result.source === "sample" ? ", labelled as a sample" : ""}.
      {result.overlaps.length ? (
        <span className="mt-1 block text-amber-text">
          It overlaps {result.overlaps.join(", ")}. Check the boundaries are correct.
        </span>
      ) : null}
    </Alert>
  );
}
