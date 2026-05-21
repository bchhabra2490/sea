import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  Loader2,
  MessageSquare,
  Play,
  XCircle,
} from "lucide-react";
import { classifyMessage, fetchBotDocs, fetchBotStatus } from "@/lib/api";
import type { BotClassifyResponse, BotDocsResponse, BotStatusResponse } from "@/types";
import { CodeBlock } from "@/components/CodeBlock";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function methodVariant(method: string): "default" | "secondary" | "outline" {
  if (method === "GET") return "secondary";
  if (method === "POST") return "default";
  return "outline";
}

export default function BotDocsApp() {
  const [docs, setDocs] = useState<BotDocsResponse | null>(null);
  const [botStatus, setBotStatus] = useState<BotStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [tryMessage, setTryMessage] = useState("I was charged twice on my last invoice");
  const [tryLoading, setTryLoading] = useState(false);
  const [tryResult, setTryResult] = useState<BotClassifyResponse | null>(null);
  const [tryError, setTryError] = useState<string | null>(null);

  const baseUrl = useMemo(
    () => (typeof window !== "undefined" ? window.location.origin : ""),
    []
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [catalog, status] = await Promise.all([
        fetchBotDocs(),
        fetchBotStatus().catch(() => null),
      ]);
      setDocs(catalog);
      setBotStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documentation");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleTryClassify = async () => {
    const msg = tryMessage.trim();
    if (!msg) return;
    setTryLoading(true);
    setTryError(null);
    setTryResult(null);
    try {
      setTryResult(await classifyMessage(msg, 3));
    } catch (err) {
      setTryError(err instanceof Error ? err.message : "Classification failed");
    } finally {
      setTryLoading(false);
    }
  };

  const thresholdPct = docs
    ? Math.round(docs.classification.threshold.min_cluster_similarity * 100)
    : 55;

  const localizedExamples = useMemo(() => {
    if (!docs) return [];
    return docs.classification.examples.map((ex) => {
      if (!ex.curl) return ex;
      return {
        ...ex,
        curl: ex.curl.replace(/https:\/\/your-deployment\.example\.com/g, baseUrl),
      };
    });
  }, [docs, baseUrl]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-3xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <BookOpen className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Bot Integration</h1>
              <p className="text-sm text-muted-foreground">
                Real-time APIs for your bot to send messages to this platform
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" asChild>
              <a href="/bot">
                <MessageSquare className="h-4 w-4" />
                Try chat
              </a>
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

      <main className="mx-auto max-w-3xl space-y-8 px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading…
          </div>
        ) : null}

        {error ? (
          <Alert variant="destructive">
            <AlertTitle>Could not load documentation</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {!loading && docs ? (
          <>
            <section className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">v{docs.version}</Badge>
                {botStatus ? (
                  <Badge variant={botStatus.ready ? "default" : "secondary"}>
                    {botStatus.ready ? (
                      <>
                        <CheckCircle2 className="mr-1 h-3 w-3" />
                        Live · {botStatus.cluster_count} topics
                      </>
                    ) : (
                      <>
                        <XCircle className="mr-1 h-3 w-3" />
                        Not ready
                      </>
                    )}
                  </Badge>
                ) : null}
              </div>
              <p className="text-muted-foreground">{docs.description}</p>
              <p className="text-sm">
                Base URL: <code className="rounded bg-muted px-1.5 py-0.5">{baseUrl}</code>
              </p>
            </section>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Prerequisites</CardTitle>
                <CardDescription>Before your bot calls these endpoints</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="list-inside list-disc space-y-1.5 text-sm text-muted-foreground">
                  {docs.prerequisites.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Real-time integration flow</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-4">
                  {docs.realtime_flow.map((step) => (
                    <li key={step.step} className="flex gap-3 text-sm">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                        {step.step}
                      </span>
                      <div>
                        <p className="font-medium">{step.title}</p>
                        <p className="text-muted-foreground">{step.detail}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>

            <Card className="border-primary/20 bg-primary/5">
              <CardHeader>
                <CardTitle className="text-lg">Which endpoint should I use?</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex gap-2">
                  <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <p>
                    <code className="font-semibold">POST /bot/classify</code> — Your bot sends each
                    user message; the platform classifies it, stores the message and assignment, and
                    returns topic + similarity. No agent reply. Use for routing, tags, or escalation.
                  </p>
                </div>
                <div className="flex gap-2">
                  <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <p>
                    <code className="font-semibold">POST /bot/chat</code> — Same classification,
                    plus a GPT agent reply and full persistence to the platform. Use when this
                    service is your support backend.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Similarity threshold</CardTitle>
                <CardDescription>
                  {docs.classification.threshold.description}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm">
                  Minimum match:{" "}
                  <span className="font-mono font-semibold">
                    {docs.classification.threshold.min_cluster_similarity}
                  </span>{" "}
                  <span className="text-muted-foreground">({thresholdPct}%)</span>
                </p>
              </CardContent>
            </Card>

            <section className="space-y-4">
              <h2 className="text-lg font-semibold">Endpoints</h2>
              {docs.classification.endpoints.map((ep) => (
                <Card key={ep.path}>
                  <CardHeader className="pb-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={methodVariant(ep.method)}>{ep.method}</Badge>
                      <code className="text-sm font-semibold">{ep.path}</code>
                    </div>
                    <CardDescription className="pt-1">{ep.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    {ep.auth ? (
                      <p>
                        <span className="font-medium">Auth: </span>
                        <span className="text-muted-foreground">{ep.auth}</span>
                      </p>
                    ) : null}
                    {ep.request_body ? (
                      <ul className="space-y-1 rounded-md border bg-muted/30 p-3 font-mono text-xs">
                        {Object.entries(ep.request_body).map(([key, desc]) => (
                          <li key={key}>
                            <span className="text-primary">{key}</span>: {desc}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {ep.query_params ? (
                      <ul className="space-y-1 rounded-md border bg-muted/30 p-3 font-mono text-xs">
                        {Object.entries(ep.query_params).map(([key, desc]) => (
                          <li key={key}>
                            <span className="text-primary">{key}</span>: {desc}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {ep.response_fields?.length ? (
                      <p className="text-muted-foreground">
                        <span className="font-medium text-foreground">Response: </span>
                        {ep.response_fields.join(", ")}
                      </p>
                    ) : null}
                  </CardContent>
                </Card>
              ))}
            </section>

            <section className="space-y-4">
              <h2 className="text-lg font-semibold">Examples</h2>
              {localizedExamples.map((ex) => (
                <div key={ex.title} className="space-y-2">
                  <h3 className="text-sm font-medium">{ex.title}</h3>
                  {ex.note ? <p className="text-sm text-muted-foreground">{ex.note}</p> : null}
                  {ex.curl ? <CodeBlock code={ex.curl} /> : null}
                  {ex.json ? (
                    <CodeBlock
                      language="json"
                      code={JSON.stringify(ex.json, null, 2)}
                    />
                  ) : null}
                </div>
              ))}
            </section>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Try classify</CardTitle>
                <CardDescription>
                  Live <code>POST /bot/classify</code> from this browser
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {!botStatus?.ready ? (
                  <Alert>
                    <AlertTitle>Classifier not ready</AlertTitle>
                    <AlertDescription>
                      Run analysis on{" "}
                      <a
                        href="/"
                        className="font-medium text-primary underline-offset-4 hover:underline"
                      >
                        PM Insights
                      </a>{" "}
                      (Sample data) first.
                    </AlertDescription>
                  </Alert>
                ) : null}
                <textarea
                  className="min-h-[80px] w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={tryMessage}
                  onChange={(e) => setTryMessage(e.target.value)}
                  maxLength={8000}
                />
                <Button
                  onClick={() => void handleTryClassify()}
                  disabled={tryLoading || !botStatus?.ready || !tryMessage.trim()}
                >
                  {tryLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  Classify
                </Button>
                {tryError ? (
                  <Alert variant="destructive">
                    <AlertDescription>{tryError}</AlertDescription>
                  </Alert>
                ) : null}
                {tryResult ? (
                  <CodeBlock language="json" code={JSON.stringify(tryResult, null, 2)} />
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Errors</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {docs.errors.map((e) => (
                    <li key={e.status} className="flex gap-3">
                      <Badge variant="outline" className="shrink-0 font-mono">
                        {e.status}
                      </Badge>
                      <span className="text-muted-foreground">{e.meaning}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <p className="pb-8 text-center text-xs text-muted-foreground">
              JSON catalog:{" "}
              <a href="/bot/docs" className="text-primary underline-offset-4 hover:underline">
                GET /bot/docs
              </a>
            </p>
          </>
        ) : null}
      </main>
    </div>
  );
}
