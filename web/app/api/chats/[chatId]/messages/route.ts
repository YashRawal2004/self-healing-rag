import { NextRequest } from "next/server";

const FLASK = "http://127.0.0.1:5000";

/** Pipe the Flask SSE body through so Next's rewrite does not buffer the turn. */
export async function POST(
  request: NextRequest,
  context: { params: Promise<{ chatId: string }> },
) {
  const { chatId } = await context.params;
  const flask = await fetch(`${FLASK}/api/chats/${chatId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      cookie: request.headers.get("cookie") ?? "",
    },
    body: await request.text(),
  });

  return new Response(flask.body, {
    status: flask.status,
    headers: {
      "Content-Type": flask.headers.get("Content-Type") ?? "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
