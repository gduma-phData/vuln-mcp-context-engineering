const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function chatWithAgent(question: string): Promise<any> {
  const res = await fetch(`${API_URL}/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function searchKB(query: string, limit: number = 5): Promise<any> {
  const res = await fetch(`${API_URL}/search-kb`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getSVSummary(): Promise<any> {
  const res = await fetch(`${API_URL}/semantic-view/summary`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getSVYaml(): Promise<any> {
  const res = await fetch(`${API_URL}/semantic-view/yaml`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
