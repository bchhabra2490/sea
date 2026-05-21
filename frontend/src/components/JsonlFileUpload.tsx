import { useRef, useState } from "react";
import { Loader2, Upload, X } from "lucide-react";
import { startUploadAnalysis } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ACCEPTED_EXTENSIONS = [".jsonl", ".csv"];

function isAcceptedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

interface ConversationFileUploadProps {
  disabled?: boolean;
  compact?: boolean;
  onStarted: () => void;
  onError: (message: string) => void;
}

export function JsonlFileUpload({
  disabled,
  compact = false,
  onStarted,
  onError,
}: ConversationFileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const handlePick = () => {
    inputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (file && !isAcceptedFile(file)) {
      onError("Please choose a .jsonl or .csv file");
      event.target.value = "";
      return;
    }
    setSelectedFile(file);
    event.target.value = "";
  };

  const clearFile = () => setSelectedFile(null);

  const handleUpload = async () => {
    if (!selectedFile) {
      handlePick();
      return;
    }

    setUploading(true);

    try {
      await startUploadAnalysis(selectedFile, true);
      onStarted();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const busy = disabled || uploading;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept=".jsonl,.csv,text/csv,application/jsonl,text/plain"
        className="hidden"
        onChange={handleFileChange}
      />

      <Button
        type="button"
        variant="outline"
        size={compact ? "sm" : "default"}
        disabled={busy}
        onClick={handlePick}
        className={cn(selectedFile && "border-primary/50")}
      >
        <Upload className="h-4 w-4" />
        {selectedFile
          ? compact
            ? "Change"
            : "Change file"
          : compact
            ? "Choose file"
            : "Choose JSONL / CSV"}
      </Button>

      {selectedFile ? (
        <span
          className={cn(
            "inline-flex items-center gap-1 truncate rounded-md border bg-muted/50 px-2 py-1 text-xs",
            compact ? "max-w-[140px] sm:max-w-[200px]" : "max-w-[220px]"
          )}
        >
          <span className="truncate" title={selectedFile.name}>
            {selectedFile.name}
          </span>
          <button
            type="button"
            className="shrink-0 rounded p-0.5 hover:bg-muted"
            onClick={clearFile}
            disabled={busy}
            aria-label="Clear selected file"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ) : null}

      <Button
        type="button"
        size={compact ? "sm" : "default"}
        disabled={busy || !selectedFile}
        onClick={() => void handleUpload()}
      >
        {uploading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Upload className="h-4 w-4" />
        )}
        {uploading ? "Starting…" : compact ? "Analyze" : "Upload & analyze"}
      </Button>
    </div>
  );
}
