import {MessageInput} from "./MessageInput.tsx";
import {MessageList} from "./MessageList.tsx";
import {useChat} from "../hooks/useChat.ts";

import "./Chat.css"

export function Chat() {
  const {messages, isLoading, error, send} = useChat();
  const isEmpty = messages.length === 0;
  async function handleSend(text: string) {
    await send(text);
  }

  return (
    <div className={isEmpty ? "chat chat-empty" : "chat"}>
      <div className="chat-body">
        {
        messages.length === 0
          ? <p className="sample-text">Ask about any problem with your car, motorbike or engine</p>
          : <MessageList messages={messages} />
        }
      </div>
      {isLoading && <p>Thinking...</p>}
      <MessageInput onSend={handleSend} />
      {error && <p className="error">{error}</p>}
    </div>
  )
}