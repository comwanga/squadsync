const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface FetchOptions {
  method?: string;
  body?: unknown;
  token?: string;
  headers?: Record<string, string>;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function fetchAPI<T = unknown>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { method = "GET", body, token, headers: extraHeaders = {} } = options;

  const headers: Record<string, string> = {
    ...extraHeaders,
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new ApiError(error.detail ?? `HTTP ${response.status}`, response.status);
  }

  return response.json() as Promise<T>;
}
