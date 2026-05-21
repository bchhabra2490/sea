import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ClusterAssignment } from "@/types";

interface ConversationTableProps {
  assignments: ClusterAssignment[];
  selectedCluster: number | null;
  topicName?: string | null;
}

export function ConversationTable({
  assignments,
  selectedCluster,
  topicName,
}: ConversationTableProps) {
  const filtered =
    selectedCluster === null
      ? assignments
      : assignments.filter((a) => a.cluster_id === selectedCluster);

  const title =
    selectedCluster === null
      ? "All conversations"
      : topicName
        ? `${topicName} (cluster ${selectedCluster})`
        : selectedCluster === -1
          ? "Unclustered conversations"
          : `Cluster ${selectedCluster} conversations`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>
          {filtered.length} row{filtered.length === 1 ? "" : "s"} — preprocessed user text
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="max-h-[420px] overflow-auto rounded-md border">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-muted/80 backdrop-blur">
              <tr className="border-b text-left">
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Cluster</th>
                <th className="px-4 py-3 font-medium">User text</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.conversation_id} className="border-b last:border-0 hover:bg-muted/40">
                  <td className="px-4 py-3 font-mono text-xs">{row.conversation_id}</td>
                  <td className="px-4 py-3">
                    {row.cluster_id === -1 ? (
                      <Badge variant="outline">noise</Badge>
                    ) : (
                      <Badge variant="secondary">{row.cluster_id}</Badge>
                    )}
                  </td>
                  <td className="max-w-md px-4 py-3 text-muted-foreground">{row.text ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
