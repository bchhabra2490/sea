import { Badge } from "@/components/ui/badge";
import type { ClusterAssignment } from "@/types";

interface ClusterConversationListProps {
  conversations: ClusterAssignment[];
  compact?: boolean;
  maxItems?: number;
}

export function ClusterConversationList({
  conversations,
  compact = false,
  maxItems,
}: ClusterConversationListProps) {
  const shown = maxItems ? conversations.slice(0, maxItems) : conversations;
  const remaining = maxItems ? Math.max(0, conversations.length - maxItems) : 0;

  if (conversations.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No conversations in this cluster.</p>
    );
  }

  return (
    <ul className={compact ? "space-y-2" : "space-y-3"}>
      {shown.map((row) => (
        <li
          key={row.conversation_id}
          className={
            compact
              ? "rounded-md border bg-muted/30 px-3 py-2"
              : "rounded-lg border bg-muted/20 px-4 py-3"
          }
        >
          <div className="mb-1 flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">{row.conversation_id}</span>
            {row.cluster_id === -1 ? (
              <Badge variant="outline" className="text-[10px]">
                noise
              </Badge>
            ) : null}
          </div>
          <p className={`leading-relaxed text-foreground ${compact ? "text-sm" : "text-sm"}`}>
            {row.text ?? "—"}
          </p>
        </li>
      ))}
      {remaining > 0 ? (
        <li className="text-xs text-muted-foreground">+ {remaining} more conversation{remaining === 1 ? "" : "s"}</li>
      ) : null}
    </ul>
  );
}
