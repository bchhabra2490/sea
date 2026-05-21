import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Loader2, Play, RefreshCw, Sparkles, Trash2 } from "lucide-react";
import {
  fetchInsights,
  fetchPipelineStatus,
  resetAllData,
  startAnalysis,
} from "@/lib/api";
import type { InsightsResponse, PipelineStatusResponse } from "@/types";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatCard } from "@/components/StatCard";
import { TopicCards } from "@/components/TopicCards";
import { ClusterDistribution } from "@/components/ClusterDistribution";
import { ConversationTable } from "@/components/ConversationTable";
import { JsonlFileUpload } from "@/components/JsonlFileUpload";
import { NoiseClusterPanel } from "@/components/NoiseClusterPanel";
import { PipelineStatusPanel } from "@/components/PipelineStatusPanel";

const POLL_INTERVAL_MS = 2000;

export function InsightsDashboard() {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);

  const loadInsights = useCallback(async () => {
    try {
      const insights = await fetchInsights();
      setData(insights);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load insights");
    }
  }, []);

  const loadPipelineStatus = useCallback(async () => {
    try {
      const status = await fetchPipelineStatus();
      setPipelineStatus(status);
      return status;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pipeline status");
      return null;
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    await Promise.all([loadInsights(), loadPipelineStatus()]);
    setLoading(false);
  }, [loadInsights, loadPipelineStatus]);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll pipeline status while running; refresh insights when done.
  useEffect(() => {
    if (!pipelineStatus?.is_running) return;

    const interval = setInterval(() => {
      void (async () => {
        const status = await loadPipelineStatus();
        if (!status) return;
        if (status.stage === "completed" || status.stage === "failed") {
          await loadInsights();
        }
      })();
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [pipelineStatus?.is_running, loadPipelineStatus, loadInsights]);

  const handleStartAnalysis = async () => {
    setStarting(true);
    setError(null);
    try {
      await startAnalysis(true);
      await loadPipelineStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
    } finally {
      setStarting(false);
    }
  };

  const handleJobStarted = async () => {
    setError(null);
    await loadPipelineStatus();
  };

  const handleResetData = async () => {
    const confirmed = window.confirm(
      "Delete ALL conversations, messages, clusters, and analysis runs from Supabase?\n\nThis cannot be undone."
    );
    if (!confirmed) return;

    setResetting(true);
    setError(null);
    try {
      const result = await resetAllData();
      setData(null);
      setSelectedCluster(null);
      setPipelineStatus(null);
      await load();
      window.alert(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset data");
    } finally {
      setResetting(false);
    }
  };

  const pipelineBusy = pipelineStatus?.is_running ?? false;
  const ready = data?.ready ?? false;
  const summary = data?.summary;

  const selectedTopicName =
    selectedCluster !== null && selectedCluster >= 0
      ? data?.topics.find((t) => t.cluster_id === selectedCluster)?.topic ?? null
      : selectedCluster === -1
        ? "Unclustered (noise)"
        : null;

  return (
    <div className="min-h-screen">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">PM Insights</h1>
              <p className="text-sm text-muted-foreground">
                Conversational intelligence from support threads
              </p>
            </div>
          </div>
          <div className="flex flex-col items-stretch gap-3 sm:items-end">
            <JsonlFileUpload
              disabled={loading || starting || pipelineBusy || resetting}
              onStarted={() => void handleJobStarted()}
              onError={setError}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() => void load()}
                disabled={loading || starting || pipelineBusy || resetting}
              >
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
              <Button
                variant="outline"
                className="border-destructive/50 text-destructive hover:bg-destructive/10"
                onClick={() => void handleResetData()}
                disabled={loading || starting || pipelineBusy || resetting}
              >
                {resetting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                {resetting ? "Resetting…" : "Reset data"}
              </Button>
              <Button
                onClick={() => void handleStartAnalysis()}
                disabled={starting || pipelineBusy || resetting}
              >
                {starting || pipelineBusy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {pipelineBusy ? "Pipeline running…" : starting ? "Starting…" : "Sample data"}
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6 lg:px-8">
        {error ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <section aria-label="Pipeline progress">
          <PipelineStatusPanel status={pipelineStatus} />
        </section>

        {loading && !data ? (
          <div className="flex items-center justify-center py-24 text-muted-foreground">
            <Loader2 className="mr-2 h-6 w-6 animate-spin" />
            Loading insights…
          </div>
        ) : null}

        {!loading && !ready && !pipelineBusy ? (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>No analysis yet</AlertTitle>
            <AlertDescription>
              Upload a <code className="rounded bg-muted px-1">.jsonl</code> or{" "}
              <code className="rounded bg-muted px-1">.csv</code> file, or click Run analysis to
              process all conversations already in Supabase. Ensure{" "}
              <code className="rounded bg-muted px-1">OPENAI_API_KEY</code> and Supabase env vars
              are set.
            </AlertDescription>
          </Alert>
        ) : null}

        {pipelineBusy && !ready ? (
          <Alert>
            <Loader2 className="h-4 w-4 animate-spin" />
            <AlertTitle>Analysis in progress</AlertTitle>
            <AlertDescription>
              Insights will appear here when the pipeline completes. You can leave this page open —
              status updates automatically.
            </AlertDescription>
          </Alert>
        ) : null}

        {ready && summary ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard title="Conversations" value={summary.conversations_processed} />
              <StatCard title="Topics" value={summary.topics_labeled} hint="Labeled clusters" />
              <StatCard title="Clusters" value={summary.clusters_found} />
              <StatCard
                title="Noise"
                value={summary.noise_points}
                hint="Unclustered outliers"
              />
            </section>

            <Tabs defaultValue="topics" className="w-full">
              <TabsList>
                <TabsTrigger value="topics">Topics</TabsTrigger>
                <TabsTrigger value="distribution">Distribution</TabsTrigger>
                <TabsTrigger value="conversations">Conversations</TabsTrigger>
              </TabsList>

              <TabsContent value="topics" className="mt-6 space-y-6">
                <TopicCards
                  topics={data!.topics}
                  assignments={data!.assignments}
                  selectedCluster={
                    selectedCluster !== null && selectedCluster >= 0 ? selectedCluster : null
                  }
                  onSelectCluster={(id) => setSelectedCluster(id)}
                />
                <NoiseClusterPanel
                  assignments={data!.assignments}
                  expanded={selectedCluster === -1}
                  onToggle={() => setSelectedCluster(selectedCluster === -1 ? null : -1)}
                />
              </TabsContent>

              <TabsContent value="distribution" className="mt-6">
                <ClusterDistribution
                  clusterCounts={data!.cluster_counts}
                  topics={data!.topics}
                />
              </TabsContent>

              <TabsContent value="conversations" className="mt-6 space-y-4">
                {data!.topics.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedCluster(null)}
                      className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                        selectedCluster === null
                          ? "border-primary bg-primary text-primary-foreground"
                          : "hover:bg-muted"
                      }`}
                    >
                      All ({data!.assignments.length})
                    </button>
                    {data!.topics.map((topic) => (
                      <button
                        key={topic.cluster_id}
                        type="button"
                        onClick={() => setSelectedCluster(topic.cluster_id)}
                        className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                          selectedCluster === topic.cluster_id
                            ? "border-primary bg-primary text-primary-foreground"
                            : "hover:bg-muted"
                        }`}
                      >
                        {topic.topic} ({data!.cluster_counts[String(topic.cluster_id)] ?? 0})
                      </button>
                    ))}
                    {(data!.cluster_counts["-1"] ?? 0) > 0 ? (
                      <button
                        type="button"
                        onClick={() => setSelectedCluster(-1)}
                        className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                          selectedCluster === -1
                            ? "border-primary bg-primary text-primary-foreground"
                            : "hover:bg-muted"
                        }`}
                      >
                        Noise ({data!.cluster_counts["-1"]})
                      </button>
                    ) : null}
                  </div>
                ) : null}
                <ConversationTable
                  assignments={data!.assignments}
                  selectedCluster={selectedCluster}
                  topicName={selectedTopicName}
                />
              </TabsContent>
            </Tabs>
          </>
        ) : null}
      </main>
    </div>
  );
}
