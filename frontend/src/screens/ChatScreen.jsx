import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import { Avatar, BottomNav, CMBackground, StatusBar, TopBar } from '../components/ui.jsx';
import { buildChatSocketUrl, listChatMessages, sendChatMessage } from '../api.js';
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
  const [partnerOnline, setPartnerOnline] = useState(false);
  const [partnerTyping, setPartnerTyping] = useState(false);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const wsRef = useRef(null);
  const typingHideTimerRef = useRef(null);
  const lastTypingSentAtRef = useRef(0);
  const partnerIdRef = useRef(initialPartner?.id ?? null);

  useEffect(() => {
    partnerIdRef.current = partner?.id ?? null;
  }, [partner?.id]);

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

  // Auto-scroll к низу: после рендера новых сообщений раскручиваем до самого
  // конца. useLayoutEffect срабатывает до paint — не будет «прыжка».
  // requestAnimationFrame подстраховывает на случай асинхронного layout
  // (картинки, пузыри сообщений переменной высоты).
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const scroll = () => {
      el.scrollTop = el.scrollHeight;
    };
    scroll();
    const raf = requestAnimationFrame(scroll);
    return () => cancelAnimationFrame(raf);
  }, [messages, partnerTyping]);

  // Realtime через WebSocket: новые сообщения, typing, presence.
  // Если WS-handshake не пройдёт (например, прокси не настроен) — упадём
  // на polling, чтобы чат всё равно обновлялся.
  useEffect(() => {
    if (!chatId) return undefined;
    const url = buildChatSocketUrl(chatId);
    if (!url) return undefined;

    let closed = false;
    let pollTimer = null;
    let reconnectTimer = null;
    let socket = null;

    const startPolling = () => {
      if (pollTimer) return;
      pollTimer = setInterval(async () => {
        try {
          const res = await listChatMessages(chatId, 1, 100);
          const fresh = res?.items || [];
          setMessages((prev) => {
            if (fresh.length === prev.length) {
              const lastA = prev[prev.length - 1];
              const lastB = fresh[fresh.length - 1];
              if (lastA?.id === lastB?.id) return prev;
            }
            return fresh;
          });
        } catch (e) {
          // ignore
        }
      }, 4000);
    };

    const stopPolling = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const connect = () => {
      if (closed) return;
      try {
        socket = new WebSocket(url);
      } catch (e) {
        startPolling();
        return;
      }
      wsRef.current = socket;

      socket.onopen = () => {
        stopPolling();
      };

      socket.onmessage = (ev) => {
        let data;
        try {
          data = JSON.parse(ev.data);
        } catch (e) {
          return;
        }
        if (!data || typeof data !== 'object') return;
        if (data.type === 'message' && data.message) {
          const m = data.message;
          const meIsSender = !!m.from_user_id && m.from_user_id !== (partnerIdRef.current ?? -1);
          const item = { ...m, mine: meIsSender };
          setMessages((prev) => {
            if (prev.some((x) => x.id === item.id)) return prev;
            return [...prev, item];
          });
          // Партнёр явно онлайн, раз шлёт сообщение.
          if (!meIsSender) setPartnerOnline(true);
        } else if (data.type === 'typing') {
          if (data.user_id && data.user_id === partnerIdRef.current) {
            setPartnerTyping(true);
            if (typingHideTimerRef.current) clearTimeout(typingHideTimerRef.current);
            typingHideTimerRef.current = setTimeout(() => setPartnerTyping(false), 2500);
          }
        } else if (data.type === 'presence') {
          if (data.user_id === partnerIdRef.current) {
            setPartnerOnline(!!data.online);
            if (!data.online) setPartnerTyping(false);
          }
        } else if (data.type === 'presence_state') {
          const ids = Array.isArray(data.online_user_ids) ? data.online_user_ids : [];
          if (partnerIdRef.current != null) {
            setPartnerOnline(ids.includes(partnerIdRef.current));
          }
        }
      };

      socket.onerror = () => {
        // Логировать не нужно — обработка в onclose.
      };

      socket.onclose = () => {
        wsRef.current = null;
        if (closed) return;
        // Подстрахуемся: пока WS лежит, тянем сообщения poll-ом.
        startPolling();
        // Переподключение с небольшим бэкоффом.
        reconnectTimer = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      closed = true;
      stopPolling();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (typingHideTimerRef.current) clearTimeout(typingHideTimerRef.current);
      if (socket) {
        try { socket.close(); } catch (e) { /* noop */ }
      }
      wsRef.current = null;
      setPartnerOnline(false);
      setPartnerTyping(false);
    };
  }, [chatId]);

  // Шлём typing на сервер (с throttling — не чаще раза в секунду).
  const notifyTyping = () => {
    const sock = wsRef.current;
    if (!sock || sock.readyState !== WebSocket.OPEN) return;
    const now = Date.now();
    if (now - lastTypingSentAtRef.current < 1500) return;
    lastTypingSentAtRef.current = now;
    try {
      sock.send(JSON.stringify({ type: 'typing' }));
    } catch (e) {
      // ignore
    }
  };

  const send = async () => {
    const text = draft.trim();
    if (!text || sending || !chatId) return;
    setSending(true);
    haptic('light');
    try {
      const msg = await sendChatMessage(chatId, text);
      setMessages((prev) => {
        if (prev.some((x) => x.id === msg.id)) return prev;
        return [...prev, msg];
      });
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

  const openPartnerProfile = () => {
    const id = partner?.id;
    if (!id) return;
    haptic('light');
    go('user-profile', { id, fallback: partner });
  };

  return (
    <div
      style={{
        position: 'relative',
        height: '100%',
        overflow: 'hidden',
        // Жёсткий grid: header сверху, композер снизу, скролл-панель в середине.
        // flex-column с min-height:0 на iOS WebApp иногда «выпускает» композер
        // под край вьюпорта — grid с шаблоном строк решает это однозначно.
        display: 'grid',
        gridTemplateRows: 'auto auto 1fr auto',
        gridTemplateColumns: '1fr',
      }}
    >
      <CMBackground style="aurora" />
      <div style={{ position: 'relative', zIndex: 2, gridRow: '1' }}>
        <StatusBar />
      </div>
      <div style={{ position: 'relative', zIndex: 2, gridRow: '2' }}>
        <TopBar
          onBack={() => go('chats')}
          title={
            <span
              onClick={openPartnerProfile}
              style={{ cursor: 'pointer' }}
            >
              {partnerNick}
            </span>
          }
          subtitle={
            partnerTyping
              ? 'печатает…'
              : partnerOnline
                ? 'в сети'
                : partner?.id
                  ? `id${partner.id}`
                  : ''
          }
          right={
            <button
              onClick={openPartnerProfile}
              aria-label="Открыть профиль"
              style={{
                background: 'transparent',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
              }}
            >
              <Avatar
                av={avSeed(partner?.id)}
                size={38}
                label={partnerLetter}
                src={partner?.avatar_data_url || undefined}
                online={partnerOnline}
              />
            </button>
          }
        />
      </div>

      {/* Messages — отдельная «панель» с фоном и рамкой. Скролл живёт ВНУТРИ
          этой панели, а композер снаружи в нижней строке grid. */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          gridRow: '3',
          minHeight: 0,
          padding: '0 12px',
          display: 'flex',
        }}
      >
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            overflowX: 'hidden',
            overscrollBehavior: 'contain',
            WebkitOverflowScrolling: 'touch',
            padding: '16px 12px 20px',
            borderRadius: 22,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
          }}
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
          {partnerTyping && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 8 }}>
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: '18px 18px 18px 4px',
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.10)',
                  color: 'var(--t-2)',
                  fontSize: 13,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <span className="cm-typing-dots" aria-hidden="true">
                  <span /><span /><span />
                </span>
                печатает
              </div>
            </div>
          )}
          <style>{`
            .cm-typing-dots { display: inline-flex; gap: 3px; }
            .cm-typing-dots span {
              width: 5px; height: 5px; border-radius: 50%;
              background: var(--t-2);
              animation: cm-typing 1s infinite ease-in-out;
            }
            .cm-typing-dots span:nth-child(2) { animation-delay: 0.15s; }
            .cm-typing-dots span:nth-child(3) { animation-delay: 0.3s; }
            @keyframes cm-typing {
              0%, 80%, 100% { opacity: 0.3; transform: translateY(0); }
              40% { opacity: 1; transform: translateY(-3px); }
            }
          `}</style>
        </div>
      </div>

      {/* Composer — нижняя строка grid. Никогда не уезжает за вьюпорт даже
          если в чате тысячи сообщений: grid-row:auto = высота по контенту. */}
      <div
        style={{
          position: 'relative',
          zIndex: 3,
          gridRow: '4',
          padding: '10px 12px calc(14px + var(--safe-bottom))',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'rgba(7,0,15,0.85)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderTop: '1px solid rgba(255,255,255,0.10)',
        }}
      >
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            if (e.target.value.length > 0) notifyTyping();
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="Сообщение…"
          disabled={sending}
          className="input"
          style={{ flex: 1, padding: '12px 14px', minWidth: 0 }}
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
  );
}
