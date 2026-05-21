import { Badge } from "@/components/ui/badge";
import type { Severity } from "@/types";

const severityVariant: Record<
  Severity,
  "secondary" | "default" | "warning" | "destructive"
> = {
  low: "secondary",
  medium: "default",
  high: "warning",
  critical: "destructive",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge variant={severityVariant[severity]} className="capitalize">
      {severity}
    </Badge>
  );
}
