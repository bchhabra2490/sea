import type { ReactNode } from "react";
import {
  BookOpen,
  Loader2,
  MessageSquare,
  Play,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";
import type { InsightsResponse, PipelineStatusResponse } from "@/types";
import { JsonlFileUpload } from "@/components/JsonlFileUpload";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface InsightsHeaderProps {
  data: InsightsResponse | null;
  pipelineStatus: PipelineStatusResponse | null;
  loading: boolean;
  starting: boolean;
  resetting: boolean;
  actionsDisabled: boolean;
  onRefresh: () => void;
  onStartAnalysis: () => void;
  onResetData: () => void;
  onUploadStarted: () => void;
  onError: (message: string) => void;
}

function ToolbarLabel({ children }: { children: ReactNode }) {
  return (
    <span className="hidden w-14 shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground sm:block">
      {children}
    </span>
  );
}

function ToolbarDivider() {
  return <div className="hidden h-8 w-px shrink-0 bg-border sm:block" aria-hidden />;
}

export function InsightsHeader({
  data,
  pipelineStatus,
  loading,
  starting,
  resetting,
  actionsDisabled,
  onRefresh,
  onStartAnalysis,
  onResetData,
  onUploadStarted,
  onError,
}: InsightsHeaderProps) {
  const pipelineBusy = pipelineStatus?.is_running ?? false;
  const ready = data?.ready ?? false;
  const summary = data?.summary;

  return (
    <header className="sticky top-0 z-20 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="mx-auto max-w-7xl">
        {/* Brand + status + nav */}
        <div className="flex items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-lg font-bold tracking-tight sm:text-xl">
                  PM Insights
                </h1>
                {pipelineBusy ? (
                  <Badge variant="warning" className="gap-1 font-normal">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {pipelineStatus?.stage_label ?? "Running"}
                  </Badge>
                ) : ready && summary ? (
                  <Badge variant="success" className="font-normal">
                    {summary.topics_labeled} topics · {summary.conversations_processed} threads
                  </Badge>
                ) : (
                  <Badge variant="outline" className="font-normal text-muted-foreground">
                    No analysis yet
                  </Badge>
                )}
              </div>
              <p className="truncate text-xs text-muted-foreground sm:text-sm">
                Conversational intelligence from support threads
              </p>
            </div>
          </div>

          <nav
            className="flex shrink-0 items-center gap-0.5 sm:gap-1"
            aria-label="App navigation"
          >
            <Button variant="ghost" size="sm" className="hidden px-2 sm:inline-flex" asChild>
              <a href="/bot" title="Support chat">
                <MessageSquare className="h-4 w-4" />
                Chat
              </a>
            </Button>
            <Button variant="ghost" size="sm" className="h-9 w-9 p-0 sm:hidden" asChild>
              <a href="/bot" title="Support chat">
                <MessageSquare className="h-4 w-4" />
              </a>
            </Button>
            <Button variant="ghost" size="sm" className="hidden px-2 sm:inline-flex" asChild>
              <a href="/integrate" title="Bot integration API">
                <BookOpen className="h-4 w-4" />
                Integrate
              </a>
            </Button>
            <Button variant="ghost" size="sm" className="h-9 w-9 p-0 sm:hidden" asChild>
              <a href="/integrate" title="Bot integration API">
                <BookOpen className="h-4 w-4" />
              </a>
            </Button>
          </nav>
        </div>

        {/* Data + actions toolbar */}
        <div className="border-t bg-muted/40 px-4 py-2.5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 sm:gap-3">
              <ToolbarLabel>Import</ToolbarLabel>
              <JsonlFileUpload
                compact
                disabled={actionsDisabled}
                onStarted={onUploadStarted}
                onError={onError}
              />
            </div>

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <ToolbarLabel>Run</ToolbarLabel>
              <Button
                size="sm"
                onClick={onStartAnalysis}
                disabled={actionsDisabled}
                className="shrink-0"
                title="Load data/sample_conversations.jsonl into Supabase and run analysis"
              >
                {starting || pipelineBusy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">
                  {pipelineBusy ? "Running…" : starting ? "Starting…" : "Sample data"}
                </span>
                <span className="sm:hidden">
                  {pipelineBusy ? "…" : starting ? "…" : "Sample"}
                </span>
              </Button>

              <ToolbarDivider />

              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                disabled={actionsDisabled}
                title="Refresh insights and pipeline status"
              >
                <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                <span className="hidden sm:inline">Refresh</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                className="border-destructive/40 text-destructive hover:bg-destructive/10"
                onClick={onResetData}
                disabled={actionsDisabled}
                title="Delete all data from Supabase"
              >
                {resetting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">
                  {resetting ? "Resetting…" : "Reset"}
                </span>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
