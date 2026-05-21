import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { TopicLabel } from "@/types";

interface ClusterDistributionProps {
  clusterCounts: Record<string, number>;
  topics: TopicLabel[];
}

export function ClusterDistribution({ clusterCounts, topics }: ClusterDistributionProps) {
  const topicById = Object.fromEntries(topics.map((t) => [t.cluster_id, t]));
  const entries = Object.entries(clusterCounts)
    .map(([id, count]) => ({
      id,
      count,
      label: id === "-1" ? "Noise (unclustered)" : topicById[Number(id)]?.topic ?? `Cluster ${id}`,
      isNoise: id === "-1",
    }))
    .sort((a, b) => b.count - a.count);

  const max = Math.max(...entries.map((e) => e.count), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Cluster distribution</CardTitle>
        <CardDescription>Conversation volume per topic cluster</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {entries.map((entry) => (
          <div key={entry.id} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className={entry.isNoise ? "text-muted-foreground" : "font-medium"}>
                {entry.label}
              </span>
              <span className="tabular-nums text-muted-foreground">{entry.count}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full ${entry.isNoise ? "bg-slate-400" : "bg-primary"}`}
                style={{ width: `${(entry.count / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
