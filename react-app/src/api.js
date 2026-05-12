const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "API request failed" }));
    throw new Error(err.detail || "API request failed");
  }
  return res.json();
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "API request failed" }));
    throw new Error(err.detail || "API request failed");
  }
  return res.json();
}
