import { NextResponse } from "next/server"

export function backendUrl(path: string) {
  const baseUrl = process.env.FASTAPI_BACKEND_URL || "http://127.0.0.1:8000"
  return `${baseUrl.replace(/\/$/, "")}${path}`
}

export function authHeader(request: Request): HeadersInit {
  const authorization = request.headers.get("authorization")
  return authorization ? { Authorization: authorization } : {}
}

export async function proxyJson(request: Request, path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)
  const authorization = request.headers.get("authorization")
  if (authorization) {
    headers.set("Authorization", authorization)
  }

  const response = await fetch(backendUrl(path), {
    ...init,
    headers,
    cache: "no-store",
  })

  const contentType = response.headers.get("content-type") || "application/json"
  const body = await response.text()

  return new NextResponse(body, {
    status: response.status,
    headers: {
      "content-type": contentType,
    },
  })
}
