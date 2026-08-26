export class RequestBodyError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function readJsonBody<T>(request: Request, maxBytes = 65_536): Promise<T> {
  const declared = request.headers.get("content-length");
  if (declared) {
    const bytes = Number(declared);
    if (!Number.isSafeInteger(bytes) || bytes < 0) {
      throw new RequestBodyError("Invalid Content-Length", 400);
    }
    if (bytes > maxBytes) throw new RequestBodyError("Request body too large", 413);
  }
  const raw = await request.text();
  if (new TextEncoder().encode(raw).byteLength > maxBytes) {
    throw new RequestBodyError("Request body too large", 413);
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    throw new RequestBodyError("Request body must be valid JSON", 400);
  }
}
