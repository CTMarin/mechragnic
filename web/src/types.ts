export type MessageRole = "user" | "assistant"

type TraceStep = {
  iteration: number;
  tool: string;
  arguments: Record<string, unknown>;
  case_ids: number[];
  error: string | null;
}

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  trace?: TraceStep[]
}

export type AskResponse = {
  answer: string;
  trace: TraceStep[];
}