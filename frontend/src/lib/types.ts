export type KPIResponse = {
  churn_rate: number
  avg_clv: number
  total_customers: number
  segment_distribution: Record<string, number>
}

export type HealthResponse = {
  status: string
  app: string
  version: string
  database: string
  llm_configured: boolean
}

export type ChartPayload = {
  chart_id: string
  title: string
  figure: {
    data?: Array<Record<string, unknown>>
    layout?: Record<string, unknown>
  }
}

export type ChatResponse = {
  answer: string
  route: string
  tool_used: string
  data: unknown
  charts: ChartPayload[]
  sql?: string | null
  metadata: Record<string, unknown>
}

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  response?: ChatResponse
}
