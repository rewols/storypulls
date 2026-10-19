const WORKER_URL = process.env.WORKER_URL ?? "http://localhost:8000";

// Forward a worker response as-is (status + JSON body), mapping network failures to 502.
export async function callWorker(path: string, init?: RequestInit): Promise<Response> {
  try {
    const res = await fetch(`${WORKER_URL}${path}`, { ...init, cache: "no-store" });
    return new Response(await res.text(), {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ detail: "The worker isn't reachable. Is it running?" }, { status: 502 });
  }
}
