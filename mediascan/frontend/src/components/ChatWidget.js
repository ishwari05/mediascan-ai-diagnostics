/**
 * ChatWidget — Floating health assistant slide-over panel.
 *
 * Contract with backend (routes/chatbot.py):
 *   POST /api/chatbot/message  { message: string }  → { reply: string }
 *   GET  /api/chatbot/suggestions                   → { suggestions: string[] }
 *
 * The backend is stateless (keyword matching); history is kept client-side only
 * so we do NOT send it with each request.
 */

import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
} from 'react';
import { useTranslation } from 'react-i18next';
import { MessageCircle, X, Send, AlertCircle } from 'lucide-react';
import { chatbotAPI } from '../utils/api';

/* ─── tiny inline styles kept here so we don't touch the global stylesheet ─── */
const S = {
  fab: {
    position: 'fixed',
    bottom: '32px',
    right: '32px',
    width: '60px',
    height: '60px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #1a56db, #2563eb)',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 8px 24px rgba(26,86,219,0.40)',
    zIndex: 1000,
    transition: 'transform 0.2s, box-shadow 0.2s',
    color: '#fff',
  },
  panel: (open) => ({
    position: 'fixed',
    bottom: '104px',
    right: '32px',
    width: '380px',
    maxWidth: 'calc(100vw - 48px)',
    height: '560px',
    maxHeight: 'calc(100vh - 140px)',
    background: '#ffffff',
    borderRadius: '24px',
    boxShadow: '0 24px 60px rgba(0,0,0,0.18)',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 999,
    overflow: 'hidden',
    border: '1px solid #e2e8f0',
    opacity: open ? 1 : 0,
    transform: open ? 'translateY(0) scale(1)' : 'translateY(20px) scale(0.96)',
    pointerEvents: open ? 'auto' : 'none',
    transition: 'opacity 0.22s ease, transform 0.22s ease',
  }),
  panelHeader: {
    padding: '16px 20px',
    background: 'linear-gradient(135deg, #1a56db, #2563eb)',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
  },
  disclaimer: {
    padding: '8px 16px',
    background: '#fffbeb',
    borderBottom: '1px solid #fde68a',
    fontSize: '11px',
    color: '#92400e',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '6px',
    flexShrink: 0,
    lineHeight: 1.4,
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  bubble: (fromUser) => ({
    maxWidth: '85%',
    padding: '10px 14px',
    borderRadius: fromUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
    background: fromUser ? 'linear-gradient(135deg, #1a56db, #2563eb)' : '#f1f5f9',
    color: fromUser ? '#fff' : '#1e293b',
    fontSize: '14px',
    lineHeight: 1.5,
    alignSelf: fromUser ? 'flex-end' : 'flex-start',
    wordBreak: 'break-word',
    boxShadow: fromUser ? '0 2px 8px rgba(26,86,219,0.25)' : '0 1px 3px rgba(0,0,0,0.06)',
  }),
  typingDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    background: '#94a3b8',
    display: 'inline-block',
  },
  inputRow: {
    padding: '12px 16px',
    borderTop: '1px solid #e2e8f0',
    display: 'flex',
    gap: '8px',
    flexShrink: 0,
    background: '#fff',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    fontSize: '14px',
    outline: 'none',
    fontFamily: "'DM Sans', sans-serif",
    color: '#1e293b',
    background: '#f8fafc',
    transition: 'border-color 0.15s',
  },
  sendBtn: (active) => ({
    width: '40px',
    height: '40px',
    borderRadius: '12px',
    border: 'none',
    background: active ? 'linear-gradient(135deg, #1a56db, #2563eb)' : '#e2e8f0',
    color: active ? '#fff' : '#94a3b8',
    cursor: active ? 'pointer' : 'default',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s, color 0.2s',
    flexShrink: 0,
  }),
  errorBanner: {
    margin: '0 16px',
    padding: '10px 14px',
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '12px',
    color: '#dc2626',
    fontSize: '13px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexShrink: 0,
  },
  chipRow: {
    padding: '0 16px 10px',
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    flexShrink: 0,
  },
  chip: {
    padding: '5px 12px',
    borderRadius: '999px',
    background: '#eff6ff',
    color: '#1a56db',
    border: '1px solid #bfdbfe',
    fontSize: '12px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    fontFamily: "'DM Sans', sans-serif",
    transition: 'background 0.15s',
  },
};

const TypingIndicator = ({ label }) => (
  <div
    style={{ ...S.bubble(false), display: 'flex', gap: '5px', alignItems: 'center', padding: '12px 16px' }}
    role="status"
    aria-label={label}
  >
    {[0, 1, 2].map((i) => (
      <span
        key={i}
        style={{
          ...S.typingDot,
          animation: `chatDotBounce 1.2s ${i * 0.2}s infinite ease-in-out`,
        }}
      />
    ))}
  </div>
);

export default function ChatWidget() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suggestions, setSuggestions] = useState([]);

  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  /* ── Fetch suggestions once on mount ── */
  useEffect(() => {
    chatbotAPI
      .getSuggestions()
      .then((r) => setSuggestions(r.data.suggestions || []))
      .catch(() => {/* silent – suggestions are optional */});
  }, []);

  /* ── Focus input whenever panel opens ── */
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  }, [open]);

  /* ── Auto-scroll to latest message ── */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  /* ── Global Esc closes panel ── */
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open]);

  const sendMessage = useCallback(async (text) => {
    const trimmed = (text || input).trim();
    if (!trimmed || loading) return;

    setInput('');
    setError(null);
    setMessages((prev) => [...prev, { from: 'user', text: trimmed, id: Date.now() }]);
    setLoading(true);

    try {
      const res = await chatbotAPI.sendMessage(trimmed);
      setMessages((prev) => [
        ...prev,
        { from: 'bot', text: res.data.reply, id: Date.now() + 1 },
      ]);
    } catch {
      setError(t('chatbot.error'));
    } finally {
      setLoading(false);
    }
  }, [input, loading, t]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const showChips = messages.length === 0 && suggestions.length > 0;

  return (
    <>
      {/* ── Slide-over panel ── */}
      <div
        style={S.panel(open)}
        role="dialog"
        aria-modal="true"
        aria-label={t('chatbot.title')}
      >
        {/* Header */}
        <div style={S.panelHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <MessageCircle size={20} />
            <span style={{ fontWeight: 700, fontSize: '15px', fontFamily: "'Outfit', sans-serif" }}>
              {t('chatbot.title')}
            </span>
          </div>
          <button
            onClick={() => setOpen(false)}
            style={{
              background: 'rgba(255,255,255,0.15)',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
            aria-label={t('chatbot.close')}
          >
            <X size={18} />
          </button>
        </div>

        {/* Disclaimer banner */}
        <div style={S.disclaimer}>
          <AlertCircle size={13} style={{ marginTop: '1px', flexShrink: 0, color: '#d97706' }} />
          <span>{t('chatbot.disclaimer')}</span>
        </div>

        {/* Messages */}
        <div style={S.messages} aria-live="polite" aria-label="Chat messages">
          {messages.map((msg) => (
            <div
              key={msg.id}
              style={S.bubble(msg.from === 'user')}
              /* bot replies may contain bold HTML from the server */
              {...(msg.from === 'bot'
                ? { dangerouslySetInnerHTML: { __html: msg.text } }
                : { children: msg.text })}
            />
          ))}
          {loading && <TypingIndicator label={t('chatbot.typing')} />}
          <div ref={bottomRef} />
        </div>

        {/* Error banner */}
        {error && (
          <div style={S.errorBanner} role="alert">
            <AlertCircle size={15} />
            {error}
          </div>
        )}

        {/* Suggestion chips — shown before first message */}
        {showChips && (
          <div style={S.chipRow}>
            {suggestions.slice(0, 4).map((s) => (
              <button
                key={s}
                style={S.chip}
                onClick={() => sendMessage(s)}
                onMouseOver={(e) => (e.currentTarget.style.background = '#dbeafe')}
                onMouseOut={(e) => (e.currentTarget.style.background = '#eff6ff')}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input row */}
        <div style={S.inputRow}>
          <input
            ref={inputRef}
            style={S.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={(e) => (e.target.style.borderColor = '#1a56db')}
            onBlur={(e) => (e.target.style.borderColor = '#e2e8f0')}
            placeholder={t('chatbot.placeholder')}
            aria-label={t('chatbot.placeholder')}
            disabled={loading}
            maxLength={500}
          />
          <button
            style={S.sendBtn(!!input.trim() && !loading)}
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            aria-label={t('chatbot.send')}
          >
            <Send size={16} />
          </button>
        </div>
      </div>

      {/* ── Floating Action Button ── */}
      <button
        style={S.fab}
        onClick={() => setOpen((v) => !v)}
        aria-label={t('chatbot.open')}
        aria-expanded={open}
        onMouseOver={(e) => {
          e.currentTarget.style.transform = 'scale(1.08)';
          e.currentTarget.style.boxShadow = '0 12px 32px rgba(26,86,219,0.50)';
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 8px 24px rgba(26,86,219,0.40)';
        }}
      >
        {open ? <X size={24} /> : <MessageCircle size={24} />}
      </button>

      {/* Keyframe for typing dots */}
      <style>{`
        @keyframes chatDotBounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40%            { transform: translateY(-5px); opacity: 1; }
        }
      `}</style>
    </>
  );
}
