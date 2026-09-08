import React, { useEffect, useRef, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import {
  FileText,
  Clock,
  Fingerprint,
  Download,
  Copy,
  Check,
  ExternalLink,
  Sparkles,
  Eye,
  EyeOff,
  Send,
  ShieldCheck,
} from "lucide-react";
import RiskBadge from "../components/RiskBadge";
import TimelinePanel from "../components/TimelinePanel";
import EntityPanel from "../components/EntityPanel";
import client from "../api/client";
import useComplaintStore from "../store/complaintStore";
import useStore from "../store/useStore";

export default function Chat() {
  const outlet = useOutletContext();
  const store = useStore();
  const complaintId = outlet?.complaintId || store.activeComplaintId;
  const { messages, activeComplaint, startChat, fetchMessages, sendMessage } = useComplaintStore();
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [showLiveDraft, setShowLiveDraft] = useState(true);
  const [draftTab, setDraftTab] = useState("draft"); // "draft" | "timeline" | "entities"
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!complaintId) {
      startChat();
      return;
    }
    (async () => {
      const existing = await fetchMessages(complaintId);
      if (!existing || !existing.length) {
        await startChat(complaintId);
      }
    })();
  }, [complaintId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || sending) return;
    const text = input;
    setInput("");
    setSending(true);
    try {
      await sendMessage(complaintId, text);
    } finally {
      setSending(false);
    }
  };

  const handleCopyDraft = () => {
    const text = activeComplaint?.generated_complaint || "";
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadPdf = async () => {
    if (!complaintId) return;
    setDownloading(true);
    try {
      // Auto-generate if needed
      try {
        await client.post("/complaint/generate", { complaint_id: complaintId });
      } catch (e) {}

      const response = await client.get(`/complaint/${complaintId}/pdf`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `CyberSaathi_Complaint_Case_${complaintId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Could not generate PDF. Please send a message describing the incident first.");
    } finally {
      setDownloading(false);
    }
  };

  const hasDraftContent = Boolean(
    activeComplaint?.generated_complaint &&
    activeComplaint.generated_complaint.trim().length > 50
  );

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "calc(100vh - 110px)",
      minHeight: "550px",
    }}>
      {/* Top Bar */}
      <div style={{
        marginBottom: "14px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "12px",
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h1 style={{
              fontFamily: "var(--font-display, sans-serif)",
              fontSize: "1.3rem",
              fontWeight: 700,
              color: "#f8fafc",
              margin: 0,
            }}>
              Interactive Incident Intake
            </h1>
            <span style={{
              fontSize: "0.7rem",
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: "12px",
              backgroundColor: "rgba(34, 197, 94, 0.12)",
              color: "#4ade80",
              border: "1px solid rgba(34, 197, 94, 0.25)",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
            }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "#22c55e" }} />
              Real-Time Active
            </span>
          </div>
          <p style={{ fontSize: "0.82rem", color: "#94a3b8", marginTop: "2px", margin: 0 }}>
            Describe your incident in natural language — CyberSaathi automatically classifies, extracts identifiers, and drafts your complaint.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {activeComplaint?.crime_category && (
            <span style={{
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "0.75rem",
              background: "rgba(59, 130, 246, 0.12)",
              border: "1px solid rgba(59, 130, 246, 0.25)",
              color: "#60a5fa",
              padding: "4px 10px",
              borderRadius: "6px",
              fontWeight: 600,
            }}>
              {activeComplaint.crime_category}
            </span>
          )}
          <RiskBadge level={activeComplaint?.risk_level || "MEDIUM"} score={activeComplaint?.risk_score} size="sm" />
          
          <button
            onClick={() => setShowLiveDraft((v) => !v)}
            id="chat-toggle-live-draft-btn"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              borderRadius: "8px",
              padding: "6px 12px",
              fontSize: "0.78rem",
              fontWeight: 600,
              color: showLiveDraft ? "#38bdf8" : "#94a3b8",
              backgroundColor: showLiveDraft ? "rgba(56, 189, 248, 0.12)" : "rgba(15, 23, 42, 0.6)",
              border: `1px solid ${showLiveDraft ? "rgba(56, 189, 248, 0.3)" : "rgba(59, 130, 246, 0.2)"}`,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {showLiveDraft ? <Eye size={14} /> : <EyeOff size={14} />}
            {showLiveDraft ? "Hide Live Draft" : "Show Live Draft"}
          </button>
        </div>
      </div>

      {/* Main Workspace (Split Grid) */}
      <div style={{
        flex: 1,
        display: "grid",
        gridTemplateColumns: showLiveDraft ? "minmax(350px, 1fr) minmax(380px, 1fr)" : "1fr",
        gap: "16px",
        minHeight: 0,
      }}>
        {/* Left Side: Chat Conversation */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          borderRadius: "12px",
          border: "1px solid rgba(59, 130, 246, 0.18)",
          background: "rgba(15, 23, 42, 0.55)",
          backdropFilter: "blur(12px)",
          overflow: "hidden",
          minHeight: 0,
        }}>
          {/* Chat Messages */}
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "16px 20px",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}>
            {messages.map((m, i) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={m.id || i}
                  style={{
                    display: "flex",
                    justifyContent: isUser ? "flex-end" : "flex-start",
                  }}
                >
                  <div
                    style={{
                      maxWidth: "84%",
                      borderRadius: isUser ? "14px 14px 2px 14px" : "14px 14px 14px 2px",
                      padding: "12px 16px",
                      fontSize: "0.88rem",
                      lineHeight: 1.55,
                      backgroundColor: isUser ? "#f59e0b" : "rgba(30, 41, 59, 0.85)",
                      color: isUser ? "#020817" : "#f1f5f9",
                      border: isUser ? "none" : "1px solid rgba(59, 130, 246, 0.2)",
                      fontWeight: isUser ? 600 : 400,
                      whiteSpace: "pre-wrap",
                      boxShadow: isUser
                        ? "0 4px 14px rgba(245, 158, 11, 0.25)"
                        : "0 4px 12px rgba(0, 0, 0, 0.25)",
                    }}
                  >
                    {!isUser && (
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        marginBottom: "6px",
                        fontSize: "0.72rem",
                        color: "#60a5fa",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}>
                        <ShieldCheck size={13} /> CyberSaathi Assistant
                      </div>
                    )}
                    {m.content}
                  </div>
                </div>
              );
            })}

            {sending && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div style={{
                  borderRadius: "14px 14px 14px 2px",
                  border: "1px solid rgba(59, 130, 246, 0.25)",
                  background: "rgba(30, 41, 59, 0.7)",
                  padding: "10px 16px",
                  fontSize: "0.83rem",
                  color: "#94a3b8",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}>
                  <div className="spinner" style={{ width: 14, height: 14 }} />
                  <span>Analyzing statement & updating live complaint draft...</span>
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>

          {/* Chat Input Bar */}
          <div style={{
            padding: "14px 16px",
            borderTop: "1px solid rgba(59, 130, 246, 0.15)",
            background: "rgba(10, 18, 36, 0.8)",
          }}>
            <form onSubmit={handleSend} style={{ display: "flex", gap: "10px" }}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Describe what happened (amount, bank, UTR, suspect number)..."
                id="chat-message-input"
                style={{
                  flex: 1,
                  borderRadius: "8px",
                  border: "1px solid rgba(59, 130, 246, 0.25)",
                  background: "rgba(15, 23, 42, 0.9)",
                  padding: "10px 14px",
                  fontSize: "0.88rem",
                  color: "#f8fafc",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                id="chat-send-btn"
                style={{
                  borderRadius: "8px",
                  background: "#f59e0b",
                  border: "none",
                  padding: "10px 18px",
                  fontSize: "0.88rem",
                  fontWeight: 700,
                  color: "#020817",
                  cursor: sending || !input.trim() ? "not-allowed" : "pointer",
                  opacity: sending || !input.trim() ? 0.5 : 1,
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  flexShrink: 0,
                  transition: "all 0.15s ease",
                }}
              >
                <Send size={15} />
                Send
              </button>
            </form>
            <p style={{
              marginTop: "8px",
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "0.7rem",
              color: "#64748b",
              margin: "8px 0 0",
            }}>
              🛡️ Never share OTPs, UPI PINs, or bank passwords with anyone.
            </p>
          </div>
        </div>

        {/* Right Side: Live Real-Time Complaint Draft Panel */}
        {showLiveDraft && (
          <div style={{
            display: "flex",
            flexDirection: "column",
            borderRadius: "12px",
            border: "1px solid rgba(59, 130, 246, 0.22)",
            background: "rgba(15, 23, 42, 0.65)",
            backdropFilter: "blur(12px)",
            overflow: "hidden",
            minHeight: 0,
          }}>
            {/* Live Draft Header */}
            <div style={{
              padding: "12px 16px",
              borderBottom: "1px solid rgba(59, 130, 246, 0.18)",
              background: "rgba(10, 20, 42, 0.8)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "8px",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 26,
                  height: 26,
                  borderRadius: "6px",
                  backgroundColor: "rgba(245, 158, 11, 0.15)",
                  color: "#f59e0b",
                }}>
                  <FileText size={15} />
                </span>
                <div>
                  <h3 style={{
                    fontSize: "0.9rem",
                    fontWeight: 700,
                    color: "#f8fafc",
                    margin: 0,
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}>
                    Live Complaint Draft
                    <span style={{
                      fontSize: "0.68rem",
                      fontWeight: 600,
                      color: "#38bdf8",
                      backgroundColor: "rgba(56, 189, 248, 0.12)",
                      border: "1px solid rgba(56, 189, 248, 0.25)",
                      padding: "1px 6px",
                      borderRadius: "8px",
                    }}>
                      10 Sections
                    </span>
                  </h3>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <button
                  onClick={handleCopyDraft}
                  disabled={!hasDraftContent}
                  id="chat-copy-draft-btn"
                  title="Copy formal draft to clipboard"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    borderRadius: "6px",
                    padding: "4px 8px",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: copied ? "#22c55e" : "#94a3b8",
                    backgroundColor: "rgba(30, 41, 59, 0.8)",
                    border: "1px solid rgba(59, 130, 246, 0.2)",
                    cursor: hasDraftContent ? "pointer" : "not-allowed",
                    opacity: hasDraftContent ? 1 : 0.5,
                  }}
                >
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  {copied ? "Copied" : "Copy"}
                </button>

                <button
                  onClick={handleDownloadPdf}
                  disabled={downloading || !hasDraftContent}
                  id="chat-download-pdf-btn"
                  title="Download legal PDF complaint"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    borderRadius: "6px",
                    padding: "4px 10px",
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    color: "#020817",
                    backgroundColor: "#f59e0b",
                    border: "none",
                    cursor: downloading || !hasDraftContent ? "not-allowed" : "pointer",
                    opacity: downloading || !hasDraftContent ? 0.6 : 1,
                  }}
                >
                  <Download size={12} />
                  {downloading ? "Preparing..." : "PDF"}
                </button>

                <Link
                  to={`/case/${complaintId}/complaint`}
                  title="Open Full Review & Edit"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    borderRadius: "6px",
                    padding: "4px 8px",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "#60a5fa",
                    backgroundColor: "rgba(59, 130, 246, 0.12)",
                    border: "1px solid rgba(59, 130, 246, 0.25)",
                    textDecoration: "none",
                  }}
                >
                  <ExternalLink size={12} />
                  Review
                </Link>
              </div>
            </div>

            {/* Sub-tabs */}
            <div style={{
              display: "flex",
              borderBottom: "1px solid rgba(59, 130, 246, 0.15)",
              background: "rgba(10, 18, 36, 0.5)",
            }}>
              <button
                onClick={() => setDraftTab("draft")}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  fontSize: "0.78rem",
                  fontWeight: draftTab === "draft" ? 700 : 500,
                  color: draftTab === "draft" ? "#f59e0b" : "#94a3b8",
                  background: "none",
                  border: "none",
                  borderBottom: draftTab === "draft" ? "2px solid #f59e0b" : "2px solid transparent",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                }}
              >
                <FileText size={13} />
                Formal Draft
              </button>
              <button
                onClick={() => setDraftTab("timeline")}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  fontSize: "0.78rem",
                  fontWeight: draftTab === "timeline" ? 700 : 500,
                  color: draftTab === "timeline" ? "#f59e0b" : "#94a3b8",
                  background: "none",
                  border: "none",
                  borderBottom: draftTab === "timeline" ? "2px solid #f59e0b" : "2px solid transparent",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                }}
              >
                <Clock size={13} />
                Timeline ({activeComplaint?.timeline?.length || 0})
              </button>
              <button
                onClick={() => setDraftTab("entities")}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  fontSize: "0.78rem",
                  fontWeight: draftTab === "entities" ? 700 : 500,
                  color: draftTab === "entities" ? "#f59e0b" : "#94a3b8",
                  background: "none",
                  border: "none",
                  borderBottom: draftTab === "entities" ? "2px solid #f59e0b" : "2px solid transparent",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                }}
              >
                <Fingerprint size={13} />
                Identifiers
              </button>
            </div>

            {/* Sub-tab Content Area */}
            <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
              {draftTab === "draft" && (
                <div>
                  {hasDraftContent ? (
                    <div style={{
                      borderRadius: "8px",
                      border: "1px solid rgba(59, 130, 246, 0.18)",
                      background: "rgba(2, 8, 23, 0.8)",
                      padding: "16px",
                    }}>
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "12px",
                        paddingBottom: "8px",
                        borderBottom: "1px solid rgba(59, 130, 246, 0.15)",
                      }}>
                        <span style={{
                          fontSize: "0.72rem",
                          fontWeight: 700,
                          color: "#22c55e",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "5px",
                        }}>
                          <Sparkles size={13} /> Official Police Complaint Draft (Auto-Updating)
                        </span>
                        <span style={{ fontSize: "0.7rem", color: "#64748b" }}>
                          Case #{complaintId}
                        </span>
                      </div>

                      <pre style={{
                        whiteSpace: "pre-wrap",
                        fontFamily: "var(--font-mono, monospace)",
                        fontSize: "0.75rem",
                        lineHeight: 1.6,
                        color: "#cbd5e1",
                        margin: 0,
                      }}>
                        {activeComplaint.generated_complaint}
                      </pre>
                    </div>
                  ) : (
                    <div style={{
                      height: "100%",
                      minHeight: "260px",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      textAlign: "center",
                      padding: "32px 16px",
                      color: "#94a3b8",
                      border: "1px dashed rgba(59, 130, 246, 0.25)",
                      borderRadius: "10px",
                      background: "rgba(10, 18, 36, 0.3)",
                    }}>
                      <Sparkles size={32} color="#f59e0b" style={{ marginBottom: "12px", opacity: 0.8 }} />
                      <h4 style={{ fontSize: "0.95rem", fontWeight: 600, color: "#f8fafc", margin: "0 0 6px" }}>
                        Real-Time Draft Generator
                      </h4>
                      <p style={{ fontSize: "0.82rem", maxWidth: "340px", margin: 0, lineHeight: 1.5 }}>
                        Send your first message in the chat describing the incident. Your 10-section formal complaint will begin assembling here in real time.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {draftTab === "timeline" && (
                <TimelinePanel events={activeComplaint?.timeline || []} />
              )}

              {draftTab === "entities" && (
                <EntityPanel entities={activeComplaint?.extracted_entities || {}} />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
