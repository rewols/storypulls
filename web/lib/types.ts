// Mirrors worker/app/models.py.

export type Stage = "queued" | "fetching" | "transcribing" | "analysing" | "geocoding" | "done" | "error";

export type Evidence = {
  source: "caption" | "audio" | "frame" | "image";
  detail: string;
  timestamp: string | null;
};

export type Geo = {
  place_id: string;
  lat: number;
  lng: number;
  address: string | null;
  rating: number | null;
  rating_count: number | null;
  matched_name: string | null;
};

export type Place = {
  name: string;
  name_local: string | null;
  category: string;
  address_hint: string | null;
  city: string | null;
  country: string | null;
  description: string;
  evidence: Evidence[];
  confidence: "high" | "medium" | "low";
  geo: Geo | null;
  maps_url: string;
};

export type Result = {
  source: {
    platform: "tiktok" | "instagram" | "xiaohongshu" | "upload";
    url: string | null;
    author: string | null;
    caption: string;
    kind: "video" | "images" | "text";
  };
  transcript_language: string | null;
  places: Place[];
  notes: string | null;
};

export type Job = {
  id: string;
  stage: Stage;
  error: string | null;
  failed_stage: Stage | null;
  result: Result | null;
  cached: boolean;
};
