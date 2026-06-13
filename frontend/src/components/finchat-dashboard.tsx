"use client"

import { FormEvent, useEffect, useMemo, useRef, useState } from "react"
import type { ReactNode } from "react"
import { useRouter } from "next/navigation"
import {
  ActivityIcon,
  BotIcon,
  CheckCircle2Icon,
  CircleAlertIcon,
  Loader2Icon,
  SendIcon,
  UploadCloudIcon,
  UsersIcon,
  WalletCardsIcon,
} from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from "recharts"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { fetchHealth, fetchKpis, sendChatMessage, uploadCsv } from "@/lib/api"
import { getSupabaseBrowserClient } from "@/lib/supabase-browser"
import type { ChartPayload, ChatMessage, HealthResponse, KPIResponse } from "@/lib/types"

const prompts = [
  "Show me the top 5 customers with the highest CLV for upselling",
  "Which customers have the highest churn probability?",
  "What are the main causal drivers of churn?",
  "How many customers have positive uplift?",
]

const chartConfig = {
  value: {
    label: "Value",
    color: "var(--chart-2)",
  },
  count: {
    label: "Customers",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig

export function FinChatDashboard() {
  const router = useRouter()
  const [loadingSession, setLoadingSession] = useState(true)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [email, setEmail] = useState<string | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [kpis, setKpis] = useState<KPIResponse | null>(null)
  const [loadingKpis, setLoadingKpis] = useState(true)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [message, setMessage] = useState("")
  const [sending, setSending] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    const supabase = getSupabaseBrowserClient()

    supabase.auth.getSession().then(({ data }) => {
      const session = data.session
      if (!session) {
        router.replace("/login")
        return
      }
      setAccessToken(session.access_token)
      setEmail(session.user.email ?? null)
      setLoadingSession(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        router.replace("/login")
        return
      }
      setAccessToken(session.access_token)
      setEmail(session.user.email ?? null)
      setLoadingSession(false)
    })

    return () => {
      listener.subscription.unsubscribe()
    }
  }, [router])

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null))
  }, [])

  useEffect(() => {
    if (!accessToken) {
      return
    }

    async function loadKpis() {
      setLoadingKpis(true)
      try {
        setKpis(await fetchKpis(accessToken as string))
      } catch (error) {
        toast.error(`Unable to load KPIs: ${error instanceof Error ? error.message : "Unknown error"}`)
      } finally {
        setLoadingKpis(false)
      }
    }

    loadKpis()
  }, [accessToken])

  const segmentData = useMemo(
    () =>
      Object.entries(kpis?.segment_distribution ?? {}).map(([segment, count]) => ({
        segment,
        count,
      })),
    [kpis]
  )

  async function logout() {
    await getSupabaseBrowserClient().auth.signOut()
    router.replace("/login")
  }

  async function submitMessage(nextMessage?: string) {
    const content = (nextMessage ?? message).trim()
    if (!content || !accessToken || sending) {
      return
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
    }
    setMessages((current) => [...current, userMessage])
    setMessage("")
    setSending(true)

    try {
      const response = await sendChatMessage(accessToken, content)
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          response,
        },
      ])
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Chat request failed."
      toast.error(detail)
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `I could not complete that request. ${detail}`,
        },
      ])
    } finally {
      setSending(false)
    }
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (!file || !accessToken) {
      toast.error("Choose a CSV file first.")
      return
    }

    setUploading(true)
    try {
      const result = await uploadCsv(accessToken, file)
      toast.success(`Processed ${result.rows_processed.toLocaleString()} rows from ${result.filename}.`)
      if (accessToken) {
        fetchKpis(accessToken).then(setKpis).catch(() => null)
      }
      event.currentTarget.reset()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed.")
    } finally {
      setUploading(false)
    }
  }

  if (loadingSession) {
    return (
      <main className="flex min-h-svh items-center justify-center bg-background">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Loader2Icon className="size-5 animate-spin text-primary" />
          Preparing your FinChat workspace...
        </div>
      </main>
    )
  }

  return (
    <SidebarProvider>
      <AppSidebar email={email} onLogout={logout} variant="inset" />
      <SidebarInset>
        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur md:px-6">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-5" />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-muted-foreground">Customer Retention Workspace</p>
            <h1 className="truncate text-lg font-semibold">FinChat Analytics</h1>
          </div>
          <StatusBadge health={health} />
        </header>

        <main className="flex flex-1 flex-col gap-5 p-4 md:p-6">
          <section id="overview" className="grid gap-4 md:grid-cols-3">
            <MetricCard
              title="Total customers"
              value={loadingKpis ? null : kpis?.total_customers.toLocaleString() ?? "0"}
              description="Customers in BANK001"
              icon={<UsersIcon className="size-5" />}
            />
            <MetricCard
              title="Churn rate"
              value={loadingKpis ? null : `${(((kpis?.churn_rate ?? 0) * 100)).toFixed(1)}%`}
              description="Observed churn label average"
              icon={<ActivityIcon className="size-5" />}
            />
            <MetricCard
              title="Average CLV"
              value={loadingKpis ? null : formatCurrency(kpis?.avg_clv ?? 0)}
              description="From scored customer features"
              icon={<WalletCardsIcon className="size-5" />}
            />
          </section>

          <section className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
            <Card id="customer-health" className="overflow-hidden">
              <CardHeader>
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div>
                    <CardTitle>Segment Distribution</CardTitle>
                    <CardDescription>Current customer base split by initial segment.</CardDescription>
                  </div>
                  <Badge variant="secondary">{segmentData.length || 0} segments</Badge>
                </div>
              </CardHeader>
              <CardContent>
                {loadingKpis ? (
                  <Skeleton className="h-[280px] w-full" />
                ) : segmentData.length ? (
                  <ChartContainer config={chartConfig} className="h-[280px] w-full">
                    <BarChart data={segmentData} margin={{ left: 8, right: 8 }}>
                      <CartesianGrid vertical={false} />
                      <XAxis dataKey="segment" tickLine={false} axisLine={false} />
                      <YAxis tickLine={false} axisLine={false} width={44} />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Bar dataKey="count" fill="var(--color-count)" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ChartContainer>
                ) : (
                  <EmptyState title="No segment data yet" description="Seed Supabase or upload customers to populate the dashboard." />
                )}
              </CardContent>
            </Card>

            <Card id="uploads">
              <CardHeader>
                <CardTitle>Data Upload</CardTitle>
                <CardDescription>Append customer or transaction CSV files through FastAPI.</CardDescription>
              </CardHeader>
              <CardContent>
                <form className="space-y-4" onSubmit={submitUpload}>
                  <Input ref={fileInputRef} type="file" accept=".csv,text/csv" />
                  <Button className="w-full" type="submit" disabled={uploading}>
                    {uploading ? <Loader2Icon className="size-4 animate-spin" /> : <UploadCloudIcon className="size-4" />}
                    Process CSV
                  </Button>
                </form>
                <p className="mt-4 text-xs text-muted-foreground">
                  Customer files need <span className="font-mono">customer_id</span> and <span className="font-mono">signup_date</span>.
                  Transaction files need <span className="font-mono">transaction_id</span>, <span className="font-mono">customer_id</span>, <span className="font-mono">transaction_date</span>, and <span className="font-mono">amount</span>.
                </p>
              </CardContent>
            </Card>
          </section>

          <Card id="assistant" className="min-h-[520px]">
            <CardHeader>
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle>Analytics Assistant</CardTitle>
                  <CardDescription>Ask about CLV, churn, survival timing, uplift, causal drivers, or SQL-backed metrics.</CardDescription>
                </div>
                <Badge variant="outline">Supabase Auth secured</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="chat">
                <TabsList>
                  <TabsTrigger value="chat">Chat</TabsTrigger>
                  <TabsTrigger value="prompts">Prompt ideas</TabsTrigger>
                </TabsList>
                <TabsContent value="chat" className="mt-4 space-y-4">
                  <div className="min-h-[280px] rounded-lg border bg-muted/20 p-3">
                    {messages.length ? (
                      <div className="space-y-4">
                        {messages.map((item) => (
                          <MessageBubble key={item.id} message={item} />
                        ))}
                        {sending ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2Icon className="size-4 animate-spin" />
                            FinChat is analyzing...
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <EmptyState
                        title="Start with a business question"
                        description="Try asking for high-risk churn customers, top CLV customers, or positive uplift counts."
                      />
                    )}
                  </div>
                  <form
                    className="flex flex-col gap-3 md:flex-row"
                    onSubmit={(event) => {
                      event.preventDefault()
                      submitMessage()
                    }}
                  >
                    <Textarea
                      className="min-h-12 flex-1 resize-none"
                      value={message}
                      onChange={(event) => setMessage(event.target.value)}
                      placeholder="Ask a business or ML analytics question..."
                    />
                    <Button className="md:w-32" type="submit" disabled={sending || !message.trim()}>
                      {sending ? <Loader2Icon className="size-4 animate-spin" /> : <SendIcon className="size-4" />}
                      Send
                    </Button>
                  </form>
                </TabsContent>
                <TabsContent value="prompts" className="mt-4 grid gap-3 md:grid-cols-2">
                  {prompts.map((prompt) => (
                    <Button key={prompt} variant="outline" className="h-auto justify-start whitespace-normal p-4 text-left" onClick={() => submitMessage(prompt)}>
                      <BotIcon className="size-4 shrink-0" />
                      {prompt}
                    </Button>
                  ))}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

function MetricCard({
  title,
  value,
  description,
  icon,
}: {
  title: string
  value: string | null
  description: string
  icon: ReactNode
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        {value === null ? <Skeleton className="h-8 w-28" /> : <div className="text-2xl font-semibold">{value}</div>}
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

function StatusBadge({ health }: { health: HealthResponse | null }) {
  if (!health) {
    return (
      <Badge variant="outline" className="gap-1">
        <CircleAlertIcon className="size-3.5" />
        Backend unknown
      </Badge>
    )
  }

  const healthy = health.status === "ok"
  return (
    <Badge variant={healthy ? "secondary" : "destructive"} className="gap-1">
      {healthy ? <CheckCircle2Icon className="size-3.5" /> : <CircleAlertIcon className="size-3.5" />}
      {healthy ? "Backend online" : "Backend degraded"}
    </Badge>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[920px] rounded-lg border p-3 text-sm ${isUser ? "bg-primary text-primary-foreground" : "bg-card"}`}>
        <p className="whitespace-pre-wrap leading-6">{message.content}</p>
        {!isUser && message.response?.charts?.length ? (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {message.response.charts.map((chart) => (
              <BackendChart key={chart.chart_id} chart={chart} />
            ))}
          </div>
        ) : null}
        {!isUser && Array.isArray(message.response?.data) ? <DataPreview data={message.response.data} /> : null}
      </div>
    </div>
  )
}

function BackendChart({ chart }: { chart: ChartPayload }) {
  const series = chart.figure.data?.[0]
  const chartType = String(series?.type || "")
  const labels = toStringArray(series?.x ?? series?.labels)
  const values = toNumberArray(series?.y ?? series?.values)
  const data = labels.map((label, index) => ({ label, value: values[index] ?? 0 }))

  if (!data.length) {
    return null
  }

  return (
    <Card className="bg-background/60">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{chart.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[220px] w-full">
          {chartType === "pie" ? (
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent nameKey="label" />} />
              <Pie data={data} dataKey="value" nameKey="label" innerRadius={52}>
                {data.map((entry, index) => (
                  <Cell key={entry.label} fill={`var(--chart-${(index % 5) + 1})`} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} hide={data.length > 8} />
              <YAxis tickLine={false} axisLine={false} width={36} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="value" fill="var(--color-value)" radius={[4, 4, 0, 0]} />
            </BarChart>
          )}
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

function DataPreview({ data }: { data: unknown[] }) {
  const rows = data.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null).slice(0, 5)
  if (!rows.length) {
    return null
  }

  return (
    <div className="mt-4 overflow-hidden rounded-lg border bg-background/60">
      <div className="grid gap-0">
        {rows.map((row, index) => (
          <div key={index} className="grid grid-cols-2 gap-3 border-b p-2 text-xs last:border-b-0 md:grid-cols-4">
            {Object.entries(row)
              .slice(0, 4)
              .map(([key, value]) => (
                <div key={key} className="min-w-0">
                  <p className="truncate text-muted-foreground">{key}</p>
                  <p className="truncate font-mono">{String(value)}</p>
                </div>
              ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center rounded-lg border border-dashed p-6 text-center">
      <p className="font-medium">{title}</p>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
    </div>
  )
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value)
}

function toStringArray(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item)) : []
}

function toNumberArray(value: unknown) {
  return Array.isArray(value) ? value.map((item) => Number(item) || 0) : []
}
