import { useEffect, useState } from 'react';
import { Icon } from '../../components/Icon.jsx';
import {
  Avatar,
  CMBackground,
  EmptyState,
  StatusBar,
  TopBar,
} from '../../components/ui.jsx';
import { likeUser, listActivity, startChat, toggleSubscription } from '../../api.js';
import { haptic, showAlert } from '../../telegram.js';

const SECTION_META = {
  likes: { title: 'Мои лайки', empty: 'Вы пока никого не лайкали' },
  liked_by: { title: 'Кто лайкнул меня', empty: 'Никто пока не лайкнул вашу анкету' },
  friends: { title: 'Друзья', empty: 'Друзей пока нет — взаимные лайки появятся здесь' },
  subscribers: { title: 'Подписчики', empty: 'У вас пока нет подписчиков' },
  subscriptions: { title: 'Подписки', empty: 'Вы пока ни на кого не подписаны' },
};

function avSeed(id) {
  const i = (Math.abs(Number(id) || 0) % 8) + 1;
  return `av-${i}`;
}

function getId(item) {
  return item?.user_id ?? item?.id ?? item?.target_user_id ?? null;
}

function getName(item) {
  return (
    item?.nickname ||
    item?.full_name ||
    item?.first_name ||
    item?.username ||
    `id${getId(item) ?? '?'}`
  );
}

function getMeta(item) {
  const parts = [];
  if (item?.game) parts.push(String(item.game).toUpperCase());
  if (item?.role) parts.push(item.role);
  if (item?.rank) parts.push(item.rank);
  return parts.join(' · ');
}

export function ActivityListScreen({ go, section, onOpenChat }) {
  const meta = SECTION_META[section] || { title: 'Активность', empty: 'Пусто' };

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listActivity(section, 100)
      .then((res) => {
        if (cancelled) return;
        setItems(res?.items || []);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || 'Не удалось загрузить');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [section]);

  const onLikeBack = async (item) => {
    const id = getId(item);
    if (!id || busyId) return;
    setBusyId(id);
    haptic('success');
    try {
      const res = await likeUser(id);
      setItems((prev) =>
        prev.map((x) =>
          getId(x) === id ? { ...x, has_like: true, mutual: !!res?.mutual } : x,
        ),
      );
      if (res?.mutual) {
        showAlert('Взаимный лайк! Теперь вы друзья');
      }
    } catch (e) {
      showAlert(e?.message || 'Не удалось лайкнуть');
    } finally {
      setBusyId(null);
    }
  };

  const onSubscribeToggle = async (item) => {
    const id = getId(item);
    if (!id || busyId) return;
    setBusyId(id);
    haptic('light');
    try {
      const res = await toggleSubscription(id);
      setItems((prev) =>
        prev.map((x) =>
          getId(x) === id ? { ...x, is_subscribed: !!res?.subscribed } : x,
        ),
      );
    } catch (e) {
      showAlert(e?.message || 'Не удалось');
    } finally {
      setBusyId(null);
    }
  };

  const openProfile = (item) => {
    const id = getId(item);
    if (!id) return;
    haptic('light');
    go('user-profile', { id, fallback: { id, nickname: item.nickname, avatar_data_url: item.avatar_data_url } });
  };

  const onWrite = async (item) => {
    const id = getId(item);
    if (!id || busyId) return;
    setBusyId(id);
    haptic('medium');
    try {
      const res = await startChat(id);
      onOpenChat?.({
        chat_id: res.chat_id,
        counterpart: res.counterpart || item,
      });
    } catch (e) {
      showAlert(e?.message || 'Не удалось начать чат');
    } finally {
      setBusyId(null);
    }
  };

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
        <TopBar title={meta.title} onBack={() => go('activity')} />

        {loading && (
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
        )}

        {!loading && error && (
          <div
            style={{
              margin: '0 16px',
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

        {!loading && !error && items.length === 0 && (
          <EmptyState
            icon={<Icon name="star" size={28} />}
            title="Пусто"
            subtitle={meta.empty}
          />
        )}

        {!loading && !error && items.length > 0 && (
          <div className="glass" style={{ margin: '0 16px', borderRadius: 22, padding: 6 }}>
            {items.map((item, i) => {
              const id = getId(item);
              const name = getName(item);
              const subtitle = getMeta(item) || (item?.username ? `@${item.username}` : '');
              const isBusy = busyId === id;
              return (
                <div
                  key={`${id}-${i}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '10px',
                    borderRadius: 16,
                    borderBottom:
                      i < items.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                  }}
                >
                  <button
                    onClick={() => openProfile(item)}
                    aria-label="Открыть профиль"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      padding: 0,
                      cursor: 'pointer',
                    }}
                  >
                    <Avatar
                      av={avSeed(id)}
                      size={44}
                      label={(name || '?')[0]?.toUpperCase()}
                      src={item.avatar_data_url || undefined}
                    />
                  </button>
                  <div
                    onClick={() => openProfile(item)}
                    style={{ flex: 1, minWidth: 0, cursor: 'pointer' }}
                  >
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: 14,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {name}
                    </div>
                    {subtitle && (
                      <div
                        style={{
                          fontSize: 12,
                          color: 'var(--t-2)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {subtitle}
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    {/* Действие зависит от секции */}
                    {section === 'liked_by' && !item.has_like && (
                      <button
                        onClick={() => onLikeBack(item)}
                        disabled={isBusy}
                        className="btn btn-primary"
                        style={{ padding: '8px 12px', fontSize: 12, height: 34 }}
                      >
                        <Icon name="heart-fill" size={12} /> В ответ
                      </button>
                    )}

                    {(section === 'subscriptions' || section === 'subscribers') && (
                      <button
                        onClick={() => onSubscribeToggle(item)}
                        disabled={isBusy}
                        className={item.is_subscribed ? 'btn btn-secondary' : 'btn btn-primary'}
                        style={{ padding: '8px 12px', fontSize: 12, height: 34 }}
                      >
                        {item.is_subscribed ? 'Отписаться' : 'Подписаться'}
                      </button>
                    )}

                    <button
                      onClick={() => onWrite(item)}
                      disabled={isBusy}
                      className="btn btn-secondary"
                      style={{ padding: '8px 12px', fontSize: 12, height: 34 }}
                    >
                      <Icon name="send" size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div style={{ height: 130 }} />
      </div>
    </div>
  );
}
