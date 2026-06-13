import { proxyJson } from "@/app/api/_proxy"

export async function GET(request: Request) {
  return proxyJson(request, "/api/kpis")
}
