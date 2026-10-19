import type { Place } from "./types";

function csvCell(value: string | number | null | undefined): string {
  const s = value == null ? "" : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCsv(places: Place[]): string {
  const header = ["name", "name_local", "category", "city", "country", "address", "lat", "lng", "rating", "note", "maps_url"];
  const rows = places.map((p) => [
    p.name, p.name_local, p.category, p.city, p.country, p.geo?.address ?? p.address_hint,
    p.geo?.lat, p.geo?.lng, p.geo?.rating, p.description, p.maps_url,
  ]);
  return [header, ...rows].map((r) => r.map(csvCell).join(",")).join("\n");
}

function xml(s: string): string {
  return s.replace(/[<>&'"]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", "'": "&apos;", '"': "&quot;" })[c]!);
}

// KML imports into Google My Maps (Import layer), which is the closest thing to "save all to Maps".
export function toKml(places: Place[], title: string): string {
  const marks = places
    .filter((p) => p.geo)
    .map((p) => {
      const name = p.name_local && p.name_local !== p.name ? `${p.name} (${p.name_local})` : p.name;
      const desc = [p.description, p.geo!.address, p.maps_url].filter(Boolean).join("\n");
      return `    <Placemark>
      <name>${xml(name)}</name>
      <description>${xml(desc)}</description>
      <Point><coordinates>${p.geo!.lng},${p.geo!.lat},0</coordinates></Point>
    </Placemark>`;
    })
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>${xml(title)}</name>
${marks}
  </Document>
</kml>
`;
}

export function toText(places: Place[]): string {
  return places
    .map((p, i) => `${i + 1}. ${p.name}${p.name_local && p.name_local !== p.name ? ` (${p.name_local})` : ""}: ${p.description}\n   ${p.maps_url}`)
    .join("\n");
}

export function download(filename: string, body: string, type: string): void {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
