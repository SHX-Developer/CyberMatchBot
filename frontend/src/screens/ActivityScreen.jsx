import { useEffect, useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import {
  Avatar,
  BottomNav,
  CMBackground,
  EmptyState,
  StatusBar,
  TopBar,
} from '../components/ui.jsx';
import { getMyStats, listActivity, startChat } from '../api.js';
import { haptic, showAlert } from '../telegram.js';

const ACCENT = {
  pink: '#FF4FD8',
  blue: '#168BFF',
  purple: '#8B5CFF',
  green: '#32D583',
  orange: '#FFC43D',
};

function avSeed(id) {
  const i = (Math.abs(Number(id) || 0) % 8) + 1;
  return `av-${i}`;
}

function getId(item) {
  return item?.user_id ?? item?.id ?? null;
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

function StatCard({ icon, count, label, accent, onClick, loading }) {
  return (
    <button
      onClick={onClick}
      className="glass"
      style={{
        padding: 14,
        borderRadius: 22,
        textAlign: 'left',
        border: '1px solid rgba(255,255,255,0.10)',
        cursor: 'pointer',
        background: 'rgba(255,255,255,0.04)',
      }}
    >
      <div
        style={{
          width: 38,
          height: 38,
          borderRadius: 12,
          background: `${ACCENT[accent]}20`,
          border: `1px solid ${ACCENT[accent]}55`,
          display: 'grid',
          placeItems: 'center',
          marginBottom: 14,
          fontSize: 18,
        }}
      >
        {icon}
      </div>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: 700,
          fontSize: 22,
          color: ACCENT[accent],
          letterSpacing: -0.5,
          lineHeight: 1,
        }}
      >
        {loading ? '–' : count}
      </div>
      <div style={{ fontSize: 12, color: '#fff', fontWeight: 600, marginTop: 6 }}>
        {label}
      </div>
    </button>
  );
}

export function ActivityScreen({ go, onOpenList, onOpenChat, onHome }) {
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [recent, setRecent] = useState([]);
  const [recentLoading, setRecentLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setStatsLoading(true);
    getMyStats()
      .then((s) => {
        if (cancelled) return;
        setStats(s);
      })
      .catch(() => {
        if (cancelled) return;
        setStats(null);
      })
      .finally(() => {
        if (!cancelled) setStatsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setRecentLoading(true);
    listActivity('liked_by', 5)
      .then((res) => {
        if (cancelled) return;
        setRecent(res?.items || []);
      })
      .catch(() => {
        if (cancelled) return;
        setRecent([]);
      })
      .finally(() => {
        if (!cancelled) setRecentLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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

  const friendsCount = stats?.friends_count ?? 0;
  const likesCount = stats?.likes_count ?? 0;
  const incomingCount = stats?.likes_count_received ?? recent.length;
  const followersCount = stats?.followers_count ?? 0;
  const subscriptionsCount = stats?.subscriptions_count ?? 0;

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
        <TopBar title="Активность" subtitle="Лайки, друзья и подписки" onHome={onHome} />

        {/* Hero — взаимные (= друзья) */}
        <div style={{ padding: '0 16px 14px' }}>
          <button
            onClick={() => onOpenList?.('friends')}
            className="glass"
            style={{
              width: '100%',
              padding: 20,
              borderRadius: 26,
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              background: 'linear-gradient(135deg, rgba(255,79,216,0.18), rgba(139,92,255,0.10))',
              border: '1px solid rgba(255,79,216,0.30)',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 20,
                background: 'linear-gradient(135deg, #FF4FD8, #8B5CFF)',
                display: 'grid',
                placeItems: 'center',
                boxShadow: '0 0 28px rgba(255,79,216,0.5)',
                color: '#fff',
                flexShrink: 0,
              }}
            >
              <Icon name="flame" size={32} />
            </div>
            <div style={{ flex: 1 }}>
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontWeight: 700,
                  fontSize: 28,
                  letterSpacing: -0.5,
                }}
              >
                {statsLoading ? '–' : friendsCount}
              </div>
              <div style={{ fontSize: 13, color: '#fff', fontWeight: 700 }}>
                {friendsCount === 0 ? 'Пока нет взаимных лайков' : 'Взаимных лайков'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--t-2)', marginTop: 2 }}>
                {friendsCount === 0
                  ? 'Лайкай в поиске, появятся взаимные'
                  : 'Открой и напиши первым'}
              </div>
            </div>
            <Icon name="caret-right" size={18} stroke="#fff" />
          </button>
        </div>

        {/* Stats grid */}
        <div style={{ padding: '0 16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <StatCard
            icon="❤"
            count={likesCount}
            label="Мои лайки"
            accent="pink"
            loading={statsLoading}
            onClick={() => onOpenList?.('likes')}
          />
          <StatCard
            icon="💘"
            count={incomingCount}
            label="Кто меня лайкнул"
            accent="pink"
            loading={statsLoading && recentLoading}
            onClick={() => onOpenList?.('liked_by')}
          />
          <StatCard
            icon="👥"
            count={followersCount}
            label="Подписчики"
            accent="blue"
            loading={statsLoading}
            onClick={() => onOpenList?.('subscribers')}
          />
          <StatCard
            icon="⭐"
            count={subscriptionsCount}
            label="Подписки"
            accent="purple"
            loading={statsLoading}
            onClick={() => onOpenList?.('subscriptions')}
          />
          <StatCard
            icon="🤝"
            count={friendsCount}
            label="Друзья"
            accent="green"
            loading={statsLoading}
            onClick={() => onOpenList?.('friends')}
          />
        </div>

        {/* Recent likers */}
        <div style={{ padding: '20px 16px 0' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 4px',
              marginBottom: 10,
            }}
          >
            <span className="section-title">Кто лайкнул недавно</span>
            <button
              onClick={() => onOpenList?.('liked_by')}
              className="btn btn-ghost"
              style={{ padding: '4px 8px', fontSize: 12 }}
            >
              Все →
            </button>
          </div>
        </div>

        <div style={{ padding: '0 16px' }}>
          {recentLoading && (
            <div
              style={{
                color: 'var(--t-2)',
                fontSize: 13,
                textAlign: 'center',
                padding: 16,
              }}
            >
              Загружаем…
            </div>
          )}
          {!recentLoading && recent.length === 0 && (
            <EmptyState
              icon={<Icon name="heart" size={28} />}
              title="Пока нет лайков"
              subtitle="Найди тиммейтов в поиске и они начнут лайкать в ответ"
            />
          )}
          {!recentLoading && recent.length > 0 && (
            <div className="glass" style={{ borderRadius: 22, padding: 6 }}>
              {recent.map((item, i) => {
                const id = getId(item);
                const name = getName(item);
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
                        i < recent.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                    }}
                  >
                    <Avatar
                      av={avSeed(id)}
                      size={44}
                      label={(name || '?')[0]?.toUpperCase()}
                      src={item.avatar_data_url || undefined}
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
                        {name}
                      </div>
                      {(item.role || item.rank || item.game) && (
                        <div
                          style={{
                            fontSize: 12,
                            color: 'var(--t-2)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {[item.game?.toUpperCase(), item.role, item.rank]
                            .filter(Boolean)
                            .join(' · ')}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => onWrite(item)}
                      disabled={isBusy}
                      className="btn btn-primary"
                      style={{
                        padding: '8px 12px',
                        fontSize: 12,
                        height: 34,
                        opacity: isBusy ? 0.6 : 1,
                      }}
                    >
                      <Icon name="heart-fill" size={12} /> В ответ
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div style={{ height: 130 }} />
      </div>

      <BottomNav active="activity" onChange={go} />
    </div>
  );
}
