"use client"

import { useState } from "react"
import { BarChart3Icon, Loader2Icon, LockKeyholeIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { getSupabaseBrowserClient } from "@/lib/supabase-browser"

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function signInWithGoogle() {
    setLoading(true)
    setError(null)

    const origin = process.env.NEXT_PUBLIC_APP_URL || window.location.origin
    const supabase = getSupabaseBrowserClient()
    const { error: signInError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${origin}/auth/callback`,
      },
    })

    if (signInError) {
      setError(signInError.message)
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-background px-4 py-10">
      <Card className="w-full max-w-md shadow-sm">
        <CardHeader className="space-y-5 text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <BarChart3Icon className="size-6" />
          </div>
          <div className="space-y-2">
            <Badge variant="secondary" className="mx-auto w-fit">
              Tenant scope BANK001
            </Badge>
            <CardTitle className="text-2xl">FinChat Analytics</CardTitle>
            <CardDescription>
              Sign in with Google to access customer health, churn, CLV, and campaign analytics.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button className="h-11 w-full" onClick={signInWithGoogle} disabled={loading}>
            {loading ? <Loader2Icon className="size-4 animate-spin" /> : <LockKeyholeIcon className="size-4" />}
            Continue with Google
          </Button>
          {error ? <p className="text-center text-sm text-destructive">{error}</p> : null}
          <p className="text-center text-xs text-muted-foreground">
            Access is authenticated by Supabase. Data requests are proxied through the Next.js app.
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
