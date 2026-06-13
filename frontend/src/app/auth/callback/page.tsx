"use client"

import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Loader2Icon } from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getSupabaseBrowserClient } from "@/lib/supabase-browser"

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<CallbackShell />}>
      <AuthCallbackContent />
    </Suspense>
  )
}

function AuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function exchangeCode() {
      const code = searchParams.get("code")
      if (!code) {
        setError("Missing OAuth code.")
        return
      }

      const supabase = getSupabaseBrowserClient()
      const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      if (exchangeError) {
        setError(exchangeError.message)
        return
      }

      router.replace("/")
    }

    exchangeCode()
  }, [router, searchParams])

  return (
    <CallbackShell error={error} />
  )
}

function CallbackShell({ error }: { error?: string | null }) {
  return (
      <main className="flex min-h-svh items-center justify-center bg-background px-4">
        <Card className="w-full max-w-sm text-center">
          <CardHeader>
            <CardTitle>Completing sign-in</CardTitle>
            <CardDescription>FinChat is verifying your Google session with Supabase.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-3">
            {error ? (
              <p className="text-sm text-destructive">{error}</p>
            ) : (
              <>
                <Loader2Icon className="size-6 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Redirecting to the dashboard...</p>
              </>
            )}
          </CardContent>
        </Card>
      </main>
  )
}
