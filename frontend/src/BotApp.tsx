import { useCallback, useEffect, useState } from "react";
import { Bot, ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { fetchBotStatus, fetchPipelineStatus } from "@/lib/api";
import type { BotStatusResponse, PipelineStatusResponse } from "@/types";
import { ChatBot } from "@/components/ChatBot";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export default function BotApp() {
  const [botStatus, setBotStatus] = useState<BotStatusResponse | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [chatKey, setChatKey] = useState(0);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [bot, pipeline] = await Promise.all([
        fetchBotStatus(),
        fetchPipelineStatus().catch(() => null),
      ]);
      setBotStatus(bot);
      setPipelineStatus(pipeline);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const pipelineRunning = pipelineStatus?.is_running ?? false;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="shrink-0 border-b bg-card">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <Bot className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Support Chat</h1>
              <p className="text-sm text-muted-foreground">
                Agent replies with live topic classification · persisted to Supabase
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                void refresh();
                setChatKey((k) => k + 1);
              }}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" asChild>
              <a href="/">
                <ExternalLink className="h-4 w-4" />
                PM Insights
              </a>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-4">
        {pipelineRunning ? (
          <Alert className="mb-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            <AlertTitle>Pipeline running</AlertTitle>
            <AlertDescription>
              {pipelineStatus?.message ?? "Analysis in progress"} — chat uses clusters from the
              last completed run.
            </AlertDescription>
          </Alert>
        ) : null}

        {!loading && botStatus && !botStatus.ready ? (
          <Alert className="mb-4">
            <AlertTitle>Chat unavailable</AlertTitle>
            <AlertDescription>
              {botStatus.message}. Open{" "}
              <a href="/" className="font-medium text-primary underline-offset-4 hover:underline">
                PM Insights
              </a>{" "}
              and run analysis first.
            </AlertDescription>
          </Alert>
        ) : null}

        <ChatBot key={chatKey} pipelineReady={botStatus?.ready ?? false} />
      </main>
    </div>
  );
}
