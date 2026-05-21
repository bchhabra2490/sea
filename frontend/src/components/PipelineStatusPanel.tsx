import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PipelineStatusResponse } from "@/types";
import { cn } from "@/lib/utils";

interface PipelineStatusPanelProps {
  status: PipelineStatusResponse | null;
}

function StepIcon({ stepStatus }: { stepStatus: string }) {
  if (stepStatus === "complete") {
    return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  }
  if (stepStatus === "active") {
    return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
  }
  return <Circle className="h-4 w-4 text-muted-foreground/50" />;
}

function stageBadgeVariant(stage: string): "default" | "secondary" | "destructive" | "outline" {
  if (stage === "completed") return "default";
  if (stage === "failed") return "destructive";
  if (stage === "idle") return "outline";
  return "secondary";
}

export function PipelineStatusPanel({ status }: PipelineStatusPanelProps) {
  if (!status) return null;

  const showPanel =
    status.is_running || status.stage === "completed" || status.stage === "failed";

  if (!showPanel && status.stage === "idle") {
    return null;
  }

  const inputName = status.input_path
    ? status.input_path.split("/").pop() ?? status.input_path
    : null;

  return (
    <Card
      className={cn(
        "border-2",
        status.is_running && "border-primary/40 bg-primary/5",
        status.stage === "failed" && "border-destructive/40 bg-destructive/5",
        status.stage === "completed" && "border-emerald-500/30 bg-emerald-500/5"
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">Pipeline status</CardTitle>
            <CardDescription className="mt-1">
              {status.is_running
                ? "Analysis is running in the background"
                : status.stage === "completed"
                  ? "Last run finished successfully"
                  : status.stage === "failed"
                    ? "Last run failed"
                    : status.message}
            </CardDescription>
          </div>
          <Badge variant={stageBadgeVariant(status.stage)} className="capitalize">
            {status.stage_label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{status.message}</span>
            <span>{status.progress_percent}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                status.stage === "failed" ? "bg-destructive" : "bg-primary"
              )}
              style={{ width: `${status.progress_percent}%` }}
            />
          </div>
        </div>

        {inputName ? (
          <p className="text-xs text-muted-foreground">
            Input: <span className="font-mono text-foreground">{inputName}</span>
            {status.job_id ? (
              <span className="ml-2 font-mono text-muted-foreground">
                · job {status.job_id.slice(0, 8)}
              </span>
            ) : null}
          </p>
        ) : null}

        {status.steps.length > 0 ? (
          <ol className="grid gap-2 sm:grid-cols-2">
            {status.steps.map((step) => (
              <li
                key={step.key}
                className={cn(
                  "flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
                  step.status === "active" && "border-primary/50 bg-background",
                  step.status === "complete" && "border-emerald-500/20 bg-background/80",
                  step.status === "pending" && "border-transparent bg-muted/30 text-muted-foreground"
                )}
              >
                <StepIcon stepStatus={step.status} />
                <span>{step.label}</span>
              </li>
            ))}
          </ol>
        ) : null}

        {status.stage === "failed" && status.error ? (
          <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{status.error}</span>
          </div>
        ) : null}

        {status.stage === "completed" && status.result ? (
          <div className="grid grid-cols-2 gap-3 rounded-md border bg-background/80 p-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-muted-foreground">Conversations</p>
              <p className="font-semibold">{status.result.conversations_processed}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Clusters</p>
              <p className="font-semibold">{status.result.clusters_found}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Topics</p>
              <p className="font-semibold">{status.result.topics_labeled}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Noise</p>
              <p className="font-semibold">{status.result.noise_points}</p>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
