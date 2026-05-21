import { useCallback, useEffect, useState } from "react";
import { Bot, Loader2, Send } from "lucide-react";
import { classifyMessage, fetchBotStatus } from "@/lib/api";
import type { BotClassifyResponse, BotStatusResponse } from "@/types";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/SeverityBadge";
import type { Severity } from "@/types";

interface BotPanelProps {
  pipelineReady: boolean;
}

export function BotPanel({ pipelineReady }: BotPanelProps) {
  const [status, setStatus] = useState<BotStatusResponse | null>(null);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<BotClassifyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const s = await fetchBotStatus();
      setStatus(s);
    } catch {
      setStatus({ ready: false, cluster_count: 0, message: "Could not reach bot API" });
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus, pipelineReady]);

  const botReady = status?.ready ?? false;

  const handleClassify = async () => {
    const text = message.trim();
    if (!text) return;

    setLoading(true);
    setError(null);
    try {
      const res = await classifyMessage(text);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Classification failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleClassify();
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Topic bot</CardTitle>
              <CardDescription>
                Type a support message to classify it against your topic clusters in real time
                (embedding + nearest centroid).
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {!botReady ? (
            <Alert>
              <AlertTitle>Bot unavailable</AlertTitle>
              <AlertDescription>
                {status?.message ?? "Run analysis first to build clusters and topic labels."}
              </AlertDescription>
            </Alert>
          ) : (
            <p className="text-xs text-muted-foreground">
              {status?.cluster_count} topic cluster{status?.cluster_count === 1 ? "" : "s"} loaded
            </p>
          )}

          <textarea
            className="min-h-[100px] w-full resize-y rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            placeholder="e.g. My refund still hasn't arrived after two weeks..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!botReady || loading}
          />

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void handleClassify()} disabled={!botReady || loading || !message.trim()}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {loading ? "Classifying…" : "Classify"}
            </Button>
          </div>

          {error ? (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      {result ? (
        <Card className={result.is_noise ? "border-amber-500/40" : "border-primary/30"}>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <CardTitle className="text-lg">
                  {result.nearest.topic ?? `Cluster ${result.nearest.cluster_id}`}
                </CardTitle>
                <CardDescription className="mt-1">
                  Cluster {result.nearest.cluster_id}
                  {result.is_noise ? " · low confidence match" : ""}
                  {" · "}
                  similarity {(result.nearest.similarity * 100).toFixed(1)}%
                </CardDescription>
              </div>
              {result.nearest.severity ? (
                <SeverityBadge severity={result.nearest.severity as Severity} />
              ) : (
                <Badge variant="outline">noise</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {result.nearest.summary ? (
              <p className="text-sm text-muted-foreground">{result.nearest.summary}</p>
            ) : null}
            <p className="text-xs text-muted-foreground">
              Processed: <span className="text-foreground">{result.processed_text}</span>
            </p>

            {result.alternatives.length > 0 ? (
              <div>
                <h4 className="mb-2 text-sm font-semibold">Other nearby topics</h4>
                <ul className="space-y-2">
                  {result.alternatives.map((alt) => (
                    <li
                      key={`${alt.cluster_id}-${alt.similarity}`}
                      className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                    >
                      <span>
                        {alt.topic ?? `Cluster ${alt.cluster_id}`}
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({(alt.similarity * 100).toFixed(1)}%)
                        </span>
                      </span>
                      {alt.severity ? (
                        <SeverityBadge severity={alt.severity as Severity} />
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
