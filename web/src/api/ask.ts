import type {ChatMessage, AskResponse} from "../types.ts";

export async function askAgent(messages: ChatMessage[]): Promise<AskResponse> {
  const history = messages.map((message: ChatMessage) => {
    return {role: message.role, content: message.content};
  })

  const response: Response = await fetch("http://localhost:8000/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: history })
  })

  if (!response.ok) throw new Error(`API error ${response.status}`)

  return response.json()
}