import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send } from "lucide-react";
import { fetchBotHistory, fetchBotStatus, sendBotChat } from "@/lib/api";
import type { ChatMessage, ClusterMatch } from "@/types";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/SeverityBadge";
import type { Severity } from "@/types";
import { cn } from "@/lib/utils";

interface ChatBotProps {
  pipelineReady: boolean;
}

function historyToMessages(
  items: { conversation_id: string; user_message: string; agent_message: string; timestamp?: string | null }[]
): ChatMessage[] {
  const messages: ChatMessage[] = [];
  for (const item of items) {
    messages.push({
      id: `${item.conversation_id}-user`,
      role: "user",
      content: item.user_message,
      timestamp: item.timestamp ?? undefined,
    });
    messages.push({
      id: `${item.conversation_id}-agent`,
      role: "assistant",
      content: item.agent_message,
      timestamp: item.timestamp ?? undefined,
    });
  }
  return messages;
}

export function ChatBot({ pipelineReady }: ChatBotProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [botReady, setBotReady] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  };

  const loadInitial = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const [status, history] = await Promise.all([fetchBotStatus(), fetchBotHistory()]);
      setBotReady(status.ready);
      setMessages(historyToMessages(history.messages));
    } catch {
      setBotReady(false);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadInitial();
  }, [loadInitial, pipelineReady]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading || !botReady) return;

    const tempUserId = `pending-user-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: tempUserId, role: "user", content: text },
    ]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await sendBotChat(text);
      setMessages((prev) => {
        const withoutPending = prev.filter((m) => m.id !== tempUserId);
        return [
          ...withoutPending,
          { id: `${res.conversation_id}-user`, role: "user", content: res.user_message },
          {
            id: `${res.conversation_id}-agent`,
            role: "assistant",
            content: res.agent_message,
            classification: res.classification,
            cluster_id: res.cluster_id,
            is_noise: res.is_noise,
          },
        ];
      });
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== tempUserId));
      setInput(text);
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-lg border bg-card shadow-sm">
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <div className="rounded-md bg-primary/10 p-1.5 text-primary">
          <Bot className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">Support agent</p>
          <p className="truncate text-xs text-muted-foreground">
            Messages are classified and saved to your conversation dataset
          </p>
        </div>
        {botReady ? (
          <Badge variant="secondary" className="shrink-0">
            Online
          </Badge>
        ) : (
          <Badge variant="outline" className="shrink-0">
            Offline
          </Badge>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {historyLoading ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading chat…
          </div>
        ) : null}

        {!historyLoading && !botReady ? (
          <Alert>
            <AlertTitle>Chat unavailable</AlertTitle>
            <AlertDescription>
              Run analysis on the PM Insights dashboard first to build topic clusters.
            </AlertDescription>
          </Alert>
        ) : null}

        {!historyLoading && botReady && messages.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Send a support message to get a reply. Your query will be classified into a topic
            cluster and appended to the dataset.
          </p>
        ) : null}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm",
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "border bg-muted/50 text-foreground"
              )}
            >
              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              {msg.role === "assistant" && msg.classification ? (
                <AgentMeta classification={msg.classification} isNoise={msg.is_noise} />
              ) : null}
            </div>
          </div>
        ))}

        {loading ? (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl border bg-muted/50 px-4 py-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Classifying and responding…
            </div>
          </div>
        ) : null}
      </div>

      {error ? (
        <div className="border-t px-4 py-2">
          <p className="text-xs text-destructive">{error}</p>
        </div>
      ) : null}

      <div className="border-t p-4">
        <div className="flex gap-2">
          <textarea
            className="min-h-[44px] flex-1 resize-none rounded-xl border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            placeholder="Type your message…"
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!botReady || loading}
          />
          <Button
            className="h-11 w-11 shrink-0 rounded-xl p-0"
            onClick={() => void handleSend()}
            disabled={!botReady || loading || !input.trim()}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

function AgentMeta({
  classification,
  isNoise,
}: {
  classification: ClusterMatch;
  isNoise?: boolean;
}) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-border/50 pt-2">
      <span className="text-xs font-medium opacity-80">
        {classification.topic ?? `Cluster ${classification.cluster_id}`}
      </span>
      <span className="text-xs opacity-60">
        {(classification.similarity * 100).toFixed(0)}% match
      </span>
      {isNoise ? (
        <Badge variant="outline" className="h-5 text-[10px]">
          noise
        </Badge>
      ) : classification.severity ? (
        <SeverityBadge severity={classification.severity as Severity} />
      ) : null}
    </div>
  );
}
