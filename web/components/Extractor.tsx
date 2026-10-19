"use client";

import { useEffect, useRef, useState } from "react";

import PlaceList from "@/components/PlaceList";
import PlaceMap from "@/components/PlaceMap";
import { download, toCsv, toKml, toText } from "@/lib/export";
import type { Job, Stage } from "@/lib/types";

const STAGES: { key: Stage; label: string }[] = [
  { key: "fetching", label: "Fetching post" },
  { key: "transcribing", label: "Listening & watching" },
  { key: "analysing", label: "Finding places" },
  { key: "geocoding", label: "Checking Google Maps" },
];

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    return `Request failed (${res.status})`;
  }
}

export default function Extractor({ mapsKey, mapId }: { mapsKey: string; mapId: string }) {
  const [url, setUrl] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [caption, setCaption] = useState("");
  const [hovered, setHovered] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const busy = job !== null && job.stage !== "done" && job.stage !== "error";

  useEffect(() => () => {
    if (pollRef.current) clearTimeout(pollRef.current);
  }, []);

  function poll(id: string) {
    pollRef.current = setTimeout(async () => {
      const res = await fetch(`/api/jobs/${id}`).catch(() => null);
      if (!res) {
        poll(id); // transient network blip; keep waiting
        return;
      }
      if (!res.ok) {
        setError(await readError(res));
        setJob(null);
        return;
      }
      const next: Job = await res.json();
      setJob(next);
      if (next.stage === "error") {
        setError(next.error);
        if (next.failed_stage === "fetching") setShowUpload(true);
      } else if (next.stage !== "done") {
        poll(id);
      }
    }, 1500);
  }

  async function start(request: Promise<Response>) {
    setError(null);
    setJob({ id: "", stage: "queued", error: null, failed_stage: null, result: null, cached: false });
    const res = await request.catch(() => null);
    if (!res || !res.ok) {
      setError(res ? await readError(res) : "Network error.");
      setJob(null);
      return;
    }
    const created: Job = await res.json();
    setJob(created);
    poll(created.id);
  }

  function submitUrl(e: React.FormEvent, refresh = false) {
    e.preventDefault();
    if (!url.trim()) return;
    start(fetch("/api/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url, refresh }),
    }));
  }

  function submitUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!files.length) return;
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("caption", caption);
    start(fetch("/api/jobs", { method: "POST", body: form }));
  }

  const result = job?.stage === "done" ? job.result : null;
  const title = result?.source.author ? `Places from ${result.source.author}` : "StoryPulls places";

  return (
    <div className="space-y-8">
      <form onSubmit={submitUrl} className="flex flex-col gap-2 sm:flex-row">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a link or share text…"
          className="min-w-0 flex-1 rounded-xl border border-line bg-transparent px-4 py-3 outline-none focus:border-accent"
        />
        <button
          disabled={busy || !url.trim()}
          className="rounded-xl bg-accent px-5 py-3 font-medium text-white disabled:opacity-50"
        >
          Find places
        </button>
      </form>

      <div>
        <button
          type="button"
          onClick={() => setShowUpload((v) => !v)}
          className="text-sm text-muted underline underline-offset-4"
        >
          {showUpload ? "Hide upload" : "Link not working? Upload the video or screenshots instead"}
        </button>
        {showUpload && (
          <form onSubmit={submitUpload} className="mt-3 space-y-3 rounded-xl border border-dashed border-line p-4">
            <input
              type="file"
              multiple
              accept="video/*,image/*"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
              className="block w-full text-sm"
            />
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Optional: paste the post's caption"
              rows={3}
              className="w-full rounded-lg border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-accent"
            />
            <button
              disabled={busy || !files.length}
              className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-paper disabled:opacity-50"
            >
              Analyse {files.length ? `${files.length} file${files.length > 1 ? "s" : ""}` : "upload"}
            </button>
          </form>
        )}
      </div>

      {busy && <Progress stage={job!.stage} />}

      {error && (
        <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
      )}

      {result && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">
                {result.places.length} place{result.places.length === 1 ? "" : "s"}
                {result.source.author && <span className="font-normal text-muted"> · {result.source.author}</span>}
              </h2>
              {job?.cached && (
                <button onClick={(e) => submitUrl(e, true)} className="text-xs text-muted underline">
                  Cached result. Re-run?
                </button>
              )}
            </div>
            {result.places.length > 0 && (
              <div className="flex gap-2 text-sm">
                <button
                  onClick={async () => {
                    await navigator.clipboard.writeText(toText(result.places));
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1500);
                  }}
                  className="rounded-lg border border-line px-3 py-1.5"
                >
                  {copied ? "Copied" : "Copy list"}
                </button>
                <button
                  onClick={() => download("places.csv", toCsv(result.places), "text/csv")}
                  className="rounded-lg border border-line px-3 py-1.5"
                >
                  CSV
                </button>
                <button
                  onClick={() => download("places.kml", toKml(result.places, title), "application/vnd.google-earth.kml+xml")}
                  className="rounded-lg border border-line px-3 py-1.5"
                  title="Import into Google My Maps"
                >
                  KML
                </button>
              </div>
            )}
          </div>
          {result.notes && <p className="text-sm text-muted">{result.notes}</p>}
          {result.places.length > 0 && (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
              <PlaceList places={result.places} hovered={hovered} onHover={setHovered} />
              <div className="lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]">
                <PlaceMap places={result.places} hovered={hovered} onHover={setHovered} apiKey={mapsKey} mapId={mapId} />
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function Progress({ stage }: { stage: Stage }) {
  const current = STAGES.findIndex((s) => s.key === stage);
  return (
    <ol className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
      {STAGES.map((s, i) => (
        <li
          key={s.key}
          className={i < current ? "text-muted line-through" : i === current ? "font-medium text-accent" : "text-muted"}
        >
          {i === current && <span className="mr-1 inline-block animate-pulse">●</span>}
          {s.label}
        </li>
      ))}
    </ol>
  );
}
