import type {ChatMessage} from "../types.ts";
import {Message} from "./Message";
import "./MessageList.css";

type MessageListProps = {
  messages: ChatMessage[]
}

export function MessageList(messageListProps: MessageListProps) {
  return (
    <div className="message-list">
      {messageListProps.messages.map((message: ChatMessage) => (
        <Message key={message.id} role={message.role} content={message.content}></Message>
      ))}
    </div>
  )
}