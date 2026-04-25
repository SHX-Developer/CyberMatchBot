import { useEffect, useRef, useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import { Avatar, BottomNav, CMBackground, StatusBar, TopBar } from '../components/ui.jsx';
import { listChatMessages, sendChatMessage } from '../api.js';
import { haptic, showAlert } from '../telegram.js';

function avSeed(id) {
  const i = (Math.abs(Number(id) || 0) % 8) + 1;
  return `av-${i}`;
}

function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function ChatScreen({ go, activeChat }) {
  const chatId = activeChat?.chat_id ?? null;
  const initialPartner = activeChat?.counterpart || null;

  const [partner, setPartner] = useState(initialPartner);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!chatId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    listChatMessages(chatId, 1, 100)
      .then((res) => {
        if (cancelled) return;
        if (res?.counterpart) setPartner(res.counterpart);
        setMessages(res?.items || []);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || 'Не удалось загрузить чат');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [chatId]);

  // прокрутить вниз при появлении новых сообщений
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  const send = async () => {
    const text = draft.trim();
    if (!text || sending || !chatId) return;
    setSending(true);
    haptic('light');
    try {
      const msg = await sendChatMessage(chatId, text);
      setMessages((prev) => [...prev, msg]);
      setDraft('');
      // вернуть фокус в инпут
      setTimeout(() => inputRef.current?.focus(), 0);
    } catch (e) {
      showAlert(e?.message || 'Не удалось отправить сообщение');
    } finally {
      setSending(false);
    }
  };

  if (!chatId) {
    return (
      <div
        style={{
          position: 'relative',
          height: '100%',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <CMBackground style="aurora" />
        <div style={{ position: 'relative', zIndex: 2, padding: 20 }}>
          <StatusBar />
          <TopBar title="Чат" onBack={() => go('chats')} />
          <div style={{ color: 'var(--t-2)', textAlign: 'center', marginTop: 40 }}>
            Чат не выбран
          </div>
        </div>
        <BottomNav active="chats" onChange={go} />
      </div>
    );
  }

  const partnerNick =
    partner?.nickname ||
    partner?.first_name ||
    partner?.full_name ||
    `id${partner?.id || '?'}`;
  const partnerLetter = (partnerNick || '?')[0]?.toUpperCase();

  return (
    <div
      style={{
        position: 'relative',
        height: '100%',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <CMBackground style="aurora" />
      <div style={{ position: 'relative', zIndex: 2, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <StatusBar />
        <TopBar
          onBack={() => go('chats')}
          title={partnerNick}
          subtitle={partner?.id ? `id${partner.id}` : ''}
          right={
            <Avatar
              av={avSeed(partner?.id)}
              size={38}
              label={partnerLetter}
              src={partner?.avatar_data_url || undefined}
            />
          }
        />

        {/* Messages */}
        <div
          ref={scrollRef}
          style={{ flex: 1, overflow: 'auto', padding: '8px 16px' }}
          className="no-scrollbar"
        >
          {loading && (
            <div style={{ color: 'var(--t-2)', fontSize: 13, textAlign: 'center', padding: 20 }}>
              Загружаем сообщения…
            </div>
          )}
          {!loading && error && (
            <div
              style={{
                margin: '12px 0',
                padding: '10px 14px',
                borderRadius: 12,
                background: 'rgba(255,59,48,0.12)',
                border: '1px solid rgba(255,59,48,0.30)',
                color: '#FF6961',
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {error}
            </div>
          )}
          {!loading && !error && messages.length === 0 && (
            <div
              style={{
                color: 'var(--t-2)',
                fontSize: 13,
                textAlign: 'center',
                padding: '40px 20px',
                lineHeight: 1.5,
              }}
            >
              Это начало вашего чата.
              <br />
              Напишите первое сообщение.
            </div>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              style={{
                display: 'flex',
                justifyContent: m.mine ? 'flex-end' : 'flex-start',
                marginBottom: 8,
              }}
            >
              <div
                style={{
                  maxWidth: '78%',
                  padding: '10px 14px',
                  borderRadius: m.mine ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                  background: m.mine
                    ? 'linear-gradient(135deg, var(--accent), var(--accent-2))'
                    : 'rgba(255,255,255,0.08)',
                  border: m.mine ? 'none' : '1px solid rgba(255,255,255,0.10)',
                  color: '#fff',
                  fontSize: 14,
                  lineHeight: 1.4,
                  boxShadow: m.mine ? '0 6px 18px var(--accent-glow)' : 'none',
                  wordBreak: 'break-word',
                }}
              >
                {m.text}
                <div
                  style={{
                    fontSize: 10,
                    opacity: 0.7,
                    marginTop: 4,
                    fontFamily: 'JetBrains Mono, monospace',
                    textAlign: 'right',
                  }}
                >
                  {fmtTime(m.created_at)}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Composer */}
        <div
          style={{
            padding: '8px 12px calc(16px + var(--safe-bottom))',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            background: 'rgba(7,0,15,0.6)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            borderTop: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Сообщение…"
            disabled={sending}
            className="input"
            style={{ flex: 1, padding: '12px 14px' }}
          />
          <button
            onClick={send}
            disabled={!draft.trim() || sending}
            style={{
              width: 44,
              height: 44,
              borderRadius: 14,
              background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
              color: '#fff',
              border: 'none',
              display: 'grid',
              placeItems: 'center',
              cursor: !draft.trim() || sending ? 'not-allowed' : 'pointer',
              opacity: !draft.trim() || sending ? 0.5 : 1,
              boxShadow: '0 6px 16px var(--accent-glow)',
              flexShrink: 0,
            }}
          >
            <Icon name="send" size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
