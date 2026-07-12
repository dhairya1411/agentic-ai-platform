const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function api<T>(path: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { credentials: "include", cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load workspace data.");
  return response.json() as Promise<T>;
}
