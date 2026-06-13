import type { ChatResponse, HealthResponse, KPIResponse } from "@/lib/types"

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const payload = await response.json()
      detail = payload.detail || payload.message || detail
    } catch {
      // Keep the HTTP status text.
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export function fetchHealth() {
  return requestJson<HealthResponse>("/api/health", { cache: "no-store" })
}

export function fetchKpis(accessToken: string) {
  return requestJson<KPIResponse>("/api/kpis", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    cache: "no-store",
  })
}

export function sendChatMessage(accessToken: string, message: string) {
  return requestJson<ChatResponse>("/api/chat", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, tenant_id: "BANK001" }),
  })
}

export function uploadCsv(accessToken: string, file: File) {
  const formData = new FormData()
  formData.append("file", file)

  return requestJson<{ status: string; filename: string; rows_processed: number }>("/api/upload", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  })
}
