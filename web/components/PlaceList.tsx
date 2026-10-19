import type { Evidence, Place } from "@/lib/types";

const SOURCE_LABEL: Record<Evidence["source"], string> = {
  caption: "caption",
  audio: "said",
  frame: "on screen",
  image: "in photo",
};

function evidenceLabel(e: Evidence): string {
  return e.timestamp ? `${SOURCE_LABEL[e.source]} at ${e.timestamp}` : SOURCE_LABEL[e.source];
}

export default function PlaceList({
  places,
  hovered,
  onHover,
}: {
  places: Place[];
  hovered: number | null;
  onHover: (i: number | null) => void;
}) {
  return (
    <ol className="space-y-3">
      {places.map((p, i) => (
        <li
          key={`${p.name}-${i}`}
          id={`place-${i}`}
          onMouseEnter={() => onHover(i)}
          onMouseLeave={() => onHover(null)}
          className={`rounded-xl border p-4 transition-colors ${
            hovered === i ? "border-accent bg-accent-soft" : "border-line"
          }`}
        >
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-white">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <h3 className="font-semibold">{p.name}</h3>
                {p.name_local && p.name_local !== p.name && <span className="text-muted">{p.name_local}</span>}
              </div>
              <p className="mt-0.5 text-xs uppercase tracking-wide text-muted">
                {p.category}
                {(p.city || p.country) && ` · ${[p.city, p.country].filter(Boolean).join(", ")}`}
                {p.geo?.rating != null && ` · ★ ${p.geo.rating} (${p.geo.rating_count ?? 0})`}
              </p>
              <p className="mt-2 text-sm">{p.description}</p>
              {p.geo?.address && <p className="mt-1 text-sm text-muted">{p.geo.address}</p>}
              {!p.geo && (
                <p className="mt-1 text-sm text-amber-700 dark:text-amber-400">
                  Not verified on Google Maps. Check the match before going.
                </p>
              )}
              {p.geo?.matched_name && p.geo.matched_name !== p.name && p.geo.matched_name !== p.name_local && (
                <p className="mt-1 text-xs text-muted">Matched as “{p.geo.matched_name}”</p>
              )}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <a
                  href={p.maps_url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg bg-ink px-3 py-1 text-xs font-medium text-paper"
                >
                  Open in Maps
                </a>
                {p.evidence.map((e, j) => (
                  <span
                    key={j}
                    title={e.detail}
                    className="max-w-[16rem] truncate rounded-full border border-line px-2 py-0.5 text-xs text-muted"
                  >
                    {evidenceLabel(e)}: {e.detail}
                  </span>
                ))}
                {p.confidence !== "high" && (
                  <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent">{p.confidence} confidence</span>
                )}
              </div>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
