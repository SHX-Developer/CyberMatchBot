import { useEffect, useRef, useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import {
  Avatar,
  BottomNav,
  CMBackground,
  EmptyState,
  StatusBar,
  TopBar,
} from '../components/ui.jsx';
import { listChats, searchUsers, startChat } from '../api.js';
import { haptic, showAlert } from '../telegram.js';

function timeLabel(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (sameDay) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (
    d.getFullYear() === yesterday.getFullYear() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getDate() === yesterday.getDate()
  ) {
    return 'Вчера';
  }
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function avSeed(id) {
  const i = (Math.abs(Number(id) || 0) % 8) + 1;
  return `av-${i}`;
}

export function ChatsScreen({ go, onOpenChat, onHome }) {
  const [chats, setChats] = useState([]);
  const [chatsLoading, setChatsLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [startingId, setStartingId] = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setChatsLoading(true);
    listChats(1, 50)
      .then((res) => {
        if (cancelled) return;
        setChats(res?.items || []);
      })
      .catch(() => {
        if (cancelled) return;
        setChats([]);
      })
      .finally(() => {
        if (!cancelled) setChatsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchUsers(q);
        setResults(res?.items || []);
      } catch (e) {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 280);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [query]);

  const openChat = (chat) => {
    haptic('light');
    onOpenChat?.({
      chat_id: chat.chat_id ?? chat.id,
      counterpart: chat.counterpart || {
        id: chat.counterpart_user_id,
        nickname: chat.counterpart_nickname || chat.counterpart_full_name,
        first_name: chat.counterpart_full_name,
      },
    });
  };

  const writeTo = async (user) => {
    if (startingId) return;
    setStartingId(user.id);
    haptic('medium');
    try {
      const res = await startChat(user.id);
      onOpenChat?.({
        chat_id: res.chat_id,
        counterpart: res.counterpart || user,
        wasJustCreated: res.created,
      });
    } catch (e) {
      showAlert(e?.message || 'Не удалось начать чат');
    } finally {
      setStartingId(null);
    }
  };

  const showSearchResults = query.trim().length >= 2;

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
      <div
        style={{ position: 'relative', zIndex: 2, flex: 1, overflow: 'auto' }}
        className="no-scrollbar"
      >
        <StatusBar />
        <TopBar
          title="Сообщения"
          subtitle={
            chatsLoading
              ? '…'
              : showSearchResults
                ? 'поиск'
                : chats.length > 0
                  ? `${chats.length} ${chats.length === 1 ? 'чат' : chats.length < 5 ? 'чата' : 'чатов'}`
                  : 'нет чатов'
          }
          onHome={onHome}
        />

        {/* Search input */}
        <div style={{ padding: '0 16px 14px' }}>
          <div
            className="input"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 14px',
            }}
          >
            <Icon name="search" size={16} stroke="var(--t-2)" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Найти по нику"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: '#fff',
                fontSize: 14,
                fontFamily: 'inherit',
              }}
            />
            {query.length > 0 && (
              <button
                onClick={() => setQuery('')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--t-2)',
                  display: 'grid',
                  placeItems: 'center',
                  padding: 0,
                }}
                aria-label="Очистить"
              >
                <Icon name="x" size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Search results */}
        {showSearchResults && (
          <>
            {searching && results.length === 0 && (
              <div
                style={{
                  padding: '12px 16px',
                  color: 'var(--t-2)',
                  fontSize: 13,
                  textAlign: 'center',
                }}
              >
                Ищем…
              </div>
            )}
            {!searching && results.length === 0 && (
              <div
                style={{
                  padding: '24px 16px',
                  color: 'var(--t-2)',
                  fontSize: 13,
                  textAlign: 'center',
                }}
              >
                По запросу «{query.trim()}» никого не нашли
              </div>
            )}
            {results.length > 0 && (
              <div className="glass" style={{ margin: '0 16px', borderRadius: 22, padding: 6 }}>
                {results.map((u, i) => (
                  <div
                    key={u.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '10px 10px',
                      borderRadius: 16,
                      borderBottom:
                        i < results.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                    }}
                  >
                    <Avatar
                      av={avSeed(u.id)}
                      size={44}
                      label={(u.nickname || u.first_name || '?')[0]?.toUpperCase()}
                      src={u.avatar_data_url || undefined}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontWeight: 700,
                          fontSize: 14,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {u.nickname || u.first_name || `id${u.id}`}
                      </div>
                      <div
                        style={{
                          fontSize: 12,
                          color: 'var(--t-2)',
                          fontFamily: 'JetBrains Mono, monospace',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {u.nickname ? `@${u.nickname}` : `id${u.id}`}
                      </div>
                    </div>
                    <button
                      onClick={() => writeTo(u)}
                      disabled={startingId === u.id}
                      className="btn btn-primary"
                      style={{
                        padding: '8px 14px',
                        fontSize: 12,
                        height: 36,
                        opacity: startingId === u.id ? 0.6 : 1,
                      }}
                    >
                      <Icon name="send" size={12} />
                      {startingId === u.id ? 'Открываем…' : 'Написать'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Chat list */}
        {!showSearchResults && (
          <>
            {chatsLoading ? (
              <div
                style={{
                  padding: 24,
                  color: 'var(--t-2)',
                  fontSize: 13,
                  textAlign: 'center',
                }}
              >
                Загружаем…
              </div>
            ) : chats.length === 0 ? (
              <EmptyState
                icon={<Icon name="chat" size={28} />}
                title="Пока нет чатов"
                subtitle="Найди тиммейта по нику в поиске сверху и напиши первым"
              />
            ) : (
              <div className="glass" style={{ margin: '0 16px', borderRadius: 22, padding: 6 }}>
                {chats.map((c, i) => {
                  const counterId =
                    c.counterpart_user_id ??
                    c.counterpart?.id ??
                    c.counterpart_id ??
                    c.id;
                  const nick =
                    c.counterpart?.nickname ||
                    c.counterpart_nickname ||
                    c.counterpart?.first_name ||
                    c.counterpart_full_name ||
                    `id${counterId || '?'}`;
                  const last = c.last_message_text ?? c.last_message ?? '';
                  const time = timeLabel(c.last_message_at || c.updated_at);
                  const unread = Number(c.unread_count || 0);
                  return (
                    <div
                      key={c.id ?? c.chat_id}
                      onClick={() => openChat(c)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '10px 10px',
                        cursor: 'pointer',
                        borderRadius: 16,
                        borderBottom:
                          i < chats.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                      }}
                    >
                      <Avatar
                        av={avSeed(counterId)}
                        size={48}
                        label={(nick || '?')[0]?.toUpperCase()}
                        src={c.counterpart?.avatar_data_url || undefined}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: 8,
                          }}
                        >
                          <span
                            style={{
                              fontWeight: 700,
                              fontSize: 15,
                              letterSpacing: -0.2,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {nick}
                          </span>
                          {time && (
                            <span
                              style={{
                                fontSize: 11,
                                color: 'var(--t-2)',
                                fontFamily: 'JetBrains Mono, monospace',
                                flexShrink: 0,
                              }}
                            >
                              {time}
                            </span>
                          )}
                        </div>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: 8,
                            marginTop: 2,
                          }}
                        >
                          <span
                            style={{
                              fontSize: 13,
                              color: unread ? '#fff' : 'var(--t-2)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              fontWeight: unread ? 600 : 400,
                            }}
                          >
                            {last || (
                              <span style={{ fontStyle: 'italic', color: 'var(--t-3)' }}>
                                нет сообщений
                              </span>
                            )}
                          </span>
                          {unread > 0 && (
                            <span
                              style={{
                                minWidth: 20,
                                height: 20,
                                padding: '0 6px',
                                borderRadius: 100,
                                background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                                color: '#fff',
                                fontSize: 11,
                                fontWeight: 800,
                                display: 'grid',
                                placeItems: 'center',
                                flexShrink: 0,
                                boxShadow: '0 0 14px var(--accent-glow)',
                              }}
                            >
                              {unread}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        <div style={{ height: 130 }} />
      </div>

      <BottomNav active="chats" onChange={go} />
    </div>
  );
}
