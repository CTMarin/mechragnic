import {useState, type SubmitEvent} from "react";
import "./MessageInput.css"

type MessageInputProps = {
  onSend: (text: string) => void;
}

export function MessageInput(messageInputProps: MessageInputProps) {
  const [text, setText] = useState<string>("");

  function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    messageInputProps.onSend(text);
    setText("");
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <textarea value={text} onChange={(event) => setText(event.target.value)} />
      <button aria-label="Send" type="submit">↑</button>
    </form>
  )
}