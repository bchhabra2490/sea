import { ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SeverityBadge } from "@/components/SeverityBadge";
import { ClusterConversationList } from "@/components/ClusterConversationList";
import type { ClusterAssignment, TopicLabel } from "@/types";
import { cn } from "@/lib/utils";

interface TopicCardsProps {
  topics: TopicLabel[];
  assignments: ClusterAssignment[];
  selectedCluster: number | null;
  onSelectCluster: (id: number | null) => void;
}

const severityOrder: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function conversationsForCluster(
  assignments: ClusterAssignment[],
  clusterId: number
): ClusterAssignment[] {
  return assignments.filter((a) => a.cluster_id === clusterId);
}

export function TopicCards({
  topics,
  assignments,
  selectedCluster,
  onSelectCluster,
}: TopicCardsProps) {
  const sorted = [...topics].sort(
    (a, b) => (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9)
  );

  const countByCluster = assignments.reduce<Record<number, number>>((acc, row) => {
    if (row.cluster_id >= 0) {
      acc[row.cluster_id] = (acc[row.cluster_id] ?? 0) + 1;
    }
    return acc;
  }, {});

  const handleToggle = (clusterId: number) => {
    onSelectCluster(selectedCluster === clusterId ? null : clusterId);
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Click a topic to expand and view conversations in that cluster.
      </p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sorted.map((topic) => {
          const expanded = selectedCluster === topic.cluster_id;
          const count = countByCluster[topic.cluster_id] ?? 0;
          const clusterConversations = conversationsForCluster(assignments, topic.cluster_id);

          return (
            <Card
              key={topic.cluster_id}
              className={cn(
                "transition-shadow",
                expanded && "ring-2 ring-primary md:col-span-2 xl:col-span-3"
              )}
            >
              <CardHeader
                className="cursor-pointer flex flex-row items-start justify-between gap-2 space-y-0"
                onClick={() => handleToggle(topic.cluster_id)}
              >
                <div className="flex min-w-0 flex-1 items-start gap-2">
                  {expanded ? (
                    <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <div className="min-w-0">
                    <CardTitle className="text-lg">{topic.topic}</CardTitle>
                    <CardDescription className="mt-1">
                      Cluster {topic.cluster_id} · {count} conversation{count === 1 ? "" : "s"}
                    </CardDescription>
                  </div>
                </div>
                <SeverityBadge severity={topic.severity} />
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm leading-relaxed text-muted-foreground">{topic.summary}</p>

                {expanded ? (
                  <div className="border-t pt-4">
                    <h4 className="mb-3 text-sm font-semibold">Conversations in this cluster</h4>
                    <ClusterConversationList conversations={clusterConversations} />
                  </div>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
