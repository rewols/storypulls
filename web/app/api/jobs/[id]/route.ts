import { callWorker } from "@/lib/worker";

export async function GET(_request: Request, ctx: RouteContext<"/api/jobs/[id]">) {
  const { id } = await ctx.params;
  return callWorker(`/jobs/${encodeURIComponent(id)}`);
}
