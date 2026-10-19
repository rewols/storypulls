import { connection } from "next/server";

import Extractor from "@/components/Extractor";

export default async function Home() {
  // Render per request so the Maps key comes from the runtime env, not the build.
  await connection();
  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">StoryPulls</h1>
        <p className="mt-1 text-muted">
          Paste an Instagram Reel, TikTok or Xiaohongshu link to get the places it features.
        </p>
      </header>
      <Extractor mapsKey={process.env.GOOGLE_MAPS_BROWSER_KEY ?? ""} mapId={process.env.GOOGLE_MAP_ID ?? "DEMO_MAP_ID"} />
    </main>
  );
}
