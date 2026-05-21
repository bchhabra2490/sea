import { ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ClusterConversationList } from "@/components/ClusterConversationList";
import type { ClusterAssignment } from "@/types";
import { cn } from "@/lib/utils";

interface NoiseClusterPanelProps {
  assignments: ClusterAssignment[];
  expanded: boolean;
  onToggle: () => void;
}

export function NoiseClusterPanel({ assignments, expanded, onToggle }: NoiseClusterPanelProps) {
  const noise = assignments.filter((a) => a.cluster_id === -1);
  if (noise.length === 0) return null;

  return (
    <Card className={cn(expanded && "ring-2 ring-slate-400")}>
      <CardHeader
        className="cursor-pointer flex flex-row items-start gap-2 space-y-0"
        onClick={onToggle}
      >
        {expanded ? (
          <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
        )}
        <div>
          <CardTitle className="text-lg">Unclustered (noise)</CardTitle>
          <CardDescription>
            Conversations that did not fit any topic cluster · {noise.length} total
          </CardDescription>
        </div>
      </CardHeader>
      {expanded ? (
        <CardContent className="border-t pt-4">
          <ClusterConversationList conversations={noise} />
        </CardContent>
      ) : null}
    </Card>
  );
}
