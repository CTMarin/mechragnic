import {useState} from "react";
import type {AskResponse, ChatMessage} from "../types.ts";
import {askAgent} from "../api/ask.ts";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  async function send(text: string) {
    const newMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text
    }
    const conversation: ChatMessage[] = [...messages, newMessage];
    setMessages(conversation);
    setIsLoading(true);
    setError(null);

    try {
      const response: AskResponse = await askAgent(conversation)
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        trace: response.trace
      }
      setMessages((previous: ChatMessage[]): ChatMessage[] => [...previous, assistantMessage]);
    } catch (error) {
      setError(error instanceof Error ? error.message : "unknown error");
    } finally {
      setIsLoading(false);
    }
  }

  return {messages, isLoading, error, send};
}