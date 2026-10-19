"use client";

import { AdvancedMarker, APIProvider, Map, Pin, useMap } from "@vis.gl/react-google-maps";
import { useEffect } from "react";

import type { Place } from "@/lib/types";

function FitBounds({ places }: { places: Place[] }) {
  const map = useMap();
  useEffect(() => {
    const located = places.filter((p) => p.geo);
    if (!map || !located.length) return;
    if (located.length === 1) {
      map.setCenter({ lat: located[0].geo!.lat, lng: located[0].geo!.lng });
      map.setZoom(15);
      return;
    }
    const bounds = new google.maps.LatLngBounds();
    located.forEach((p) => bounds.extend({ lat: p.geo!.lat, lng: p.geo!.lng }));
    map.fitBounds(bounds, 48);
  }, [map, places]);
  return null;
}

export default function PlaceMap({
  places,
  hovered,
  onHover,
  apiKey,
  mapId,
}: {
  places: Place[];
  hovered: number | null;
  onHover: (i: number | null) => void;
  apiKey: string;
  mapId: string;
}) {
  if (!apiKey) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-line p-6 text-center text-sm text-muted">
        Set GOOGLE_MAPS_BROWSER_KEY to show the map.
      </div>
    );
  }
  if (!places.some((p) => p.geo)) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-line p-6 text-center text-sm text-muted">
        None of these places could be matched on Google Maps.
      </div>
    );
  }

  return (
    <APIProvider apiKey={apiKey}>
      <div className="h-80 overflow-hidden rounded-xl border border-line lg:h-full">
        <Map mapId={mapId} defaultCenter={{ lat: 0, lng: 0 }} defaultZoom={2} gestureHandling="greedy" disableDefaultUI>
          <FitBounds places={places} />
          {places.map((p, i) =>
            p.geo ? (
              <AdvancedMarker
                key={`${p.geo.place_id}-${i}`}
                position={{ lat: p.geo.lat, lng: p.geo.lng }}
                title={p.name}
                zIndex={hovered === i ? 10 : 1}
                onMouseEnter={() => onHover(i)}
                onMouseLeave={() => onHover(null)}
                onClick={() => document.getElementById(`place-${i}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}
              >
                <Pin
                  background={hovered === i ? "#1c1917" : "#e8590c"}
                  borderColor="#ffffff"
                  glyphColor="#ffffff"
                  glyphText={String(i + 1)}
                  scale={hovered === i ? 1.25 : 1}
                />
              </AdvancedMarker>
            ) : null,
          )}
        </Map>
      </div>
    </APIProvider>
  );
}
