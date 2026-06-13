import { authHeader, backendUrl } from "@/app/api/_proxy"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
  const formData = await request.formData()
  const response = await fetch(backendUrl("/api/upload"), {
    method: "POST",
    headers: authHeader(request),
    body: formData,
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
