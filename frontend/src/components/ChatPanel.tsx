import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Bot, User } from "lucide-react";
import { chatAboutCampaigns } from "../services/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  startDate?: string;
  endDate?: string;
}

export default function ChatPanel({ startDate, endDate }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setIsLoading(true);

    try {
      const response = await chatAboutCampaigns(question, startDate, endDate);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Request failed. Please check the API connection.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card chat-panel">
      <h2>
        <Bot size={22} color="#8b5cf6" />
        Ask the AI Advisor
      </h2>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <Bot size={36} color="#444" />
            <p>Ask questions about your campaign data.</p>
            <div className="chat-suggestions">
              {[
                "Which campaign has the best cost-efficiency ratio?",
                "Where am I wasting budget?",
                "How can I improve my CTR?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  className="chat-suggestion"
                  onClick={() => setInput(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message chat-${msg.role}`}>
            <div className="chat-avatar">
              {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className="chat-bubble">
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="chat-message chat-assistant">
            <div className="chat-avatar">
              <Bot size={16} />
            </div>
            <div className="chat-bubble">
              <Loader2 size={16} className="spin" /> Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask a question about your campaigns..."
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading || !input.trim()} className="btn-send">
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
