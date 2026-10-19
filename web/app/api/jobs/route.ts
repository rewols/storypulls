import { callWorker } from "@/lib/worker";

// JSON {url, refresh?} -> worker POST /jobs; multipart (files[], caption) -> POST /jobs/upload.
export async function POST(request: Request) {
  const type = request.headers.get("content-type") ?? "";
  if (type.startsWith("multipart/form-data")) {
    return callWorker("/jobs/upload", { method: "POST", body: await request.formData() });
  }
  return callWorker("/jobs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}
