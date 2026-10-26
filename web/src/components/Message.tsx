import type {MessageRole} from "../types.ts";
import Markdown from "react-markdown";
import "./Message.css"

type MessageProps = {
  role: MessageRole,
  content: string
}

export function Message(messageProps: MessageProps) {
  return (
    <div className={`message message--${messageProps.role}`}>
      <Markdown>{messageProps.content}</Markdown>
    </div>
  )
}