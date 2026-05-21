export type Severity = "low" | "medium" | "high" | "critical";

export type PipelineStage =
  | "idle"
  | "queued"
  | "ingesting"
  | "preprocessing"
  | "embedding"
  | "clustering"
  | "labeling"
  | "completed"
  | "failed";

export interface TopicLabel {
  cluster_id: number;
  topic: string;
  summary: string;
  severity: Severity;
}

export interface ClusterAssignment {
  conversation_id: string;
  cluster_id: number;
  text: string | null;
}

export interface InsightsSummary {
  conversations_processed: number;
  clusters_found: number;
  noise_points: number;
  topics_labeled: number;
  status: string | null;
}

export interface ResetDataResponse {
  message: string;
  deleted: Record<string, number>;
}

export interface InsightsResponse {
  ready: boolean;
  summary: InsightsSummary | null;
  topics: TopicLabel[];
  assignments: ClusterAssignment[];
  cluster_counts: Record<string, number>;
}

export interface AnalyzeResponse {
  status: string;
  conversations_processed: number;
  clusters_found: number;
  noise_points: number;
  topics_labeled: number;
  storage: string;
}

export interface PipelineStep {
  key: string;
  label: string;
  status: "pending" | "active" | "complete";
}

export interface PipelineStatusResponse {
  job_id: string | null;
  stage: PipelineStage;
  stage_label: string;
  message: string;
  progress_percent: number;
  is_running: boolean;
  input_path: string | null;
  started_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  error: string | null;
  result: AnalyzeResponse | null;
  steps: PipelineStep[];
}

export interface JobStartResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ClusterMatch {
  cluster_id: number;
  similarity: number;
  topic: string | null;
  summary: string | null;
  severity: Severity | null;
}

export interface BotClassifyResponse {
  conversation_id: string;
  message: string;
  processed_text: string;
  nearest: ClusterMatch;
  alternatives: ClusterMatch[];
  is_noise: boolean;
  min_similarity: number;
  cluster_id: number;
  stored: boolean;
  appended_to: string;
}

export interface BotStatusResponse {
  ready: boolean;
  cluster_count: number;
  message: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  classification?: ClusterMatch;
  cluster_id?: number;
  is_noise?: boolean;
  timestamp?: string;
}

export interface BotChatResponse {
  conversation_id: string;
  user_message: string;
  agent_message: string;
  processed_text: string;
  classification: ClusterMatch;
  alternatives: ClusterMatch[];
  is_noise: boolean;
  cluster_id: number;
  appended_to: string;
}

export interface BotHistoryItem {
  conversation_id: string;
  timestamp: string | null;
  user_message: string;
  agent_message: string;
}

export interface BotHistoryResponse {
  messages: BotHistoryItem[];
}

export interface BotDocsEndpoint {
  method: string;
  path: string;
  description: string;
  auth?: string | null;
  request_body?: Record<string, string> | null;
  query_params?: Record<string, string>;
  response_fields?: string[];
}

export interface BotDocsExample {
  title: string;
  curl?: string;
  note?: string;
  json?: Record<string, unknown>;
}

export interface BotDocsFlowStep {
  step: number;
  title: string;
  detail: string;
}

export interface BotDocsResponse {
  title: string;
  version: string;
  description: string;
  integration_guide_url: string;
  prerequisites: string[];
  realtime_flow: BotDocsFlowStep[];
  classification: {
    threshold: {
      min_cluster_similarity: number;
      description: string;
    };
    endpoints: BotDocsEndpoint[];
    examples: BotDocsExample[];
  };
  errors: Array<{ status: number; meaning: string }>;
}
