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

function errorMessage(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map(item => typeof item?.msg === "string" ? item.msg : null)
      .filter(Boolean)
      .join("; ") || `HTTP ${status}`;
  }
  return `HTTP ${status}`;
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

  const useBackendProxy = typeof window !== "undefined" && !!token;
  if (token && !useBackendProxy) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const baseUrl = useBackendProxy ? "/api/backend" : API_URL;
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new ApiError(errorMessage(error.detail, response.status), response.status);
  }

  return response.json() as Promise<T>;
}
