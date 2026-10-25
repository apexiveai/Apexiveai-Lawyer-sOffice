import { useState } from "react";
import { Bot, Send } from "lucide-react";
import { API_BASE_URL, apiFetch } from "../services/api";

type AssistantResponse = {
  answer: string;
  tool_calls?: Array<{ tool: string; arguments?: Record<string, unknown> }>;
};

type Props = { jobId: string | null };

export default function AIAssistant({ jobId }: Props) {
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [toolCalls, setToolCalls] = useState<NonNullable<AssistantResponse["tool_calls"]>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const ask = async (question = message) => {
    const trimmed = question.trim();
    if (!jobId || !trimmed || loading) return;
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch(`${API_BASE_URL}/api/assistant/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, message: trimmed }),
      });
      if (!response.ok) throw new Error(await response.text());
      const data = (await response.json()) as AssistantResponse;
      setAnswer(data.answer);
      setToolCalls(data.tool_calls || []);
      setMessage("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Assistant request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="assistant-section">
      <div className="section-heading">
        <div>
          <div className="section-label">04 / AI ASSISTANT</div>
          <h2>Ask about this analysis</h2>
        </div>
        <div className="secure-badge"><Bot size={15} /> MCP CONNECTED</div>
      </div>
      <div className="assistant-prompts">
        {["Show me the logo conflicts", "Why was this trademark flagged?", "Find SAILUN conflicts"].map((prompt) => (
          <button key={prompt} type="button" onClick={() => void ask(prompt)} disabled={!jobId || loading}>{prompt}</button>
        ))}
      </div>
      <form className="assistant-form" onSubmit={(event) => { event.preventDefault(); void ask(); }}>
        <input value={message} onChange={(event) => setMessage(event.target.value)} placeholder={jobId ? "Ask about logo conflicts, evidence, or matches..." : "Run an analysis first"} disabled={!jobId || loading} />
        <button type="submit" disabled={!jobId || !message.trim() || loading} aria-label="Ask assistant"><Send size={17} /></button>
      </form>
      {error && <div className="assistant-error">{error}</div>}
      {answer && (
        <div className="assistant-answer">
          <div className="assistant-answer-header"><Bot size={17} /><strong>AI Assistant</strong></div>
          <pre>{answer}</pre>
          {toolCalls.length > 0 && <div className="assistant-tools">{toolCalls.map((call, index) => <span key={`${call.tool}-${index}`}>MCP: {call.tool}</span>)}</div>}
        </div>
      )}
    </section>
  );
}
