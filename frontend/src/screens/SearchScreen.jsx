import { useEffect, useMemo, useState } from 'react';
import { Icon, cls } from '../components/Icon.jsx';
import {
  Avatar,
  BottomNav,
  CMBackground,
  EmptyState,
  StatusBar,
  TopBar,
} from '../components/ui.jsx';
import { GAMES } from '../data/mock.js';
import {
  GAME_BACKEND_CODE,
  GAME_KEY_FROM_CODE,
  GAME_OPTIONS,
} from './create/games.js';
import { useStore } from '../store.jsx';
import { likeUser, searchPlayers, startChat } from '../api.js';
import { haptic, showAlert } from '../telegram.js';

function avSeed(id) {
  const i = (Math.abs(Number(id) || 0) % 8) + 1;
  return `av-${i}`;
}

function ActionFab({ icon, size = 56, kind, onClick, disabled }) {
  const styles =
    {
      like: { bg: 'linear-gradient(135deg, #FF4FD8, #8B5CFF)', glow: '0 0 28px rgba(255,79,216,0.55)' },
      pass: { bg: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.18)', color: 'var(--t-1)' },
      msg: { bg: 'linear-gradient(135deg, #168BFF, #8B5CFF)', glow: '0 0 22px rgba(22,139,255,0.5)' },
      next: { bg: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.18)', color: 'var(--t-1)' },
    }[kind] || {};
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: styles.bg,
        border: styles.border || 'none',
        color: styles.color || '#fff',
        display: 'grid',
        placeItems: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        boxShadow: styles.glow
          ? `${styles.glow}, 0 8px 24px rgba(0,0,0,0.4)`
          : '0 8px 24px rgba(0,0,0,0.4)',
        transition: 'transform 0.15s',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <Icon name={icon} size={size * 0.42} />
    </button>
  );
}

function PlayerCard({ item, compact = false, onTap, showDecal }) {
  if (!item) return null;
  const profile = item.profile;
  const owner = item.owner || {};
  const wizardKey = GAME_KEY_FROM_CODE[profile.game] || profile.game;
  const blockKey = wizardKey in GAMES ? wizardKey : 'mlbb';
  const g = GAMES[blockKey];

  const nick = profile.game_nickname || owner.nickname || `id${owner.id}`;
  const age = owner.age;
  const region = profile.region || '';
  const role = profile.main_role || profile.role;

  return (
    <div
      onClick={onTap}
      className="glass glass-strong"
      style={{
        height: '100%',
        borderRadius: 28,
        padding: 0,
        position: 'relative',
        overflow: 'hidden',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 30px 60px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.10) inset',
      }}
    >
      {profile.screenshot_url ? (
        <img
          src={profile.screenshot_url}
          alt="screenshot"
          style={{
            width: '100%',
            height: compact ? 160 : 220,
            objectFit: 'cover',
            display: 'block',
          }}
        />
      ) : (
        <div
          className={cls('game-block', g.cls)}
          style={{
            height: compact ? 160 : 220,
            borderRadius: 0,
            padding: '20px 22px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            border: 'none',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div className="gb-tag">{g.tag}</div>
            {profile.rank && (
              <span
                className="chip"
                style={{
                  background: 'rgba(0,0,0,0.4)',
                  borderColor: 'rgba(255,255,255,0.20)',
                  color: '#fff',
                  backdropFilter: 'blur(8px)',
                }}
              >
                <Icon name="crown" size={11} stroke="#FFC43D" /> {profile.rank}
              </span>
            )}
          </div>
          <div className="gb-name" style={{ fontSize: compact ? 40 : 56, whiteSpace: 'pre-line', lineHeight: 0.92 }}>
            {g.name}
          </div>
        </div>
      )}

      <div
        style={{
          padding: '0 20px',
          marginTop: -28,
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          alignItems: 'flex-end',
          gap: 14,
        }}
      >
        <Avatar
          av={avSeed(owner.id)}
          size={72}
          square
          label={(nick || '?')[0]?.toUpperCase()}
          ring
          src={owner.avatar_data_url || undefined}
        />
        <div style={{ paddingBottom: 4, flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div
              style={{
                fontSize: 22,
                fontWeight: 800,
                letterSpacing: -0.5,
                color: '#fff',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {nick}
            </div>
            {age != null && (
              <span style={{ color: 'var(--t-2)', fontSize: 14, fontWeight: 600 }}>· {age}</span>
            )}
          </div>
          {profile.game_id && (
            <div
              style={{
                fontSize: 12,
                color: 'var(--t-2)',
                fontFamily: 'JetBrains Mono, monospace',
                letterSpacing: '0.04em',
              }}
            >
              ID {profile.game_id}
              {profile.server_id ? ` · ${profile.server_id}` : ''}
            </div>
          )}
        </div>
      </div>

      <div style={{ padding: '14px 20px 0', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {region && (
          <span className="chip">
            <Icon name="pin" size={11} /> {region}
          </span>
        )}
        {role && <span className="chip chip-accent">{role}</span>}
        {(profile.secondary_roles || []).slice(0, 3).map((r) => (
          <span key={r} className="chip">
            {r}
          </span>
        ))}
      </div>

      {!compact && profile.about && (
        <div style={{ padding: '14px 20px 0', flex: 1, minHeight: 0 }}>
          <div className="section-title" style={{ marginBottom: 6 }}>
            О себе
          </div>
          <div
            style={{
              fontSize: 14,
              color: '#E6E6F0',
              lineHeight: 1.45,
              display: '-webkit-box',
              WebkitLineClamp: 4,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {profile.about}
          </div>
        </div>
      )}

      <div
        style={{
          padding: '14px 20px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--t-2)' }}>
          {item.subscribed && (
            <span style={{ color: 'var(--c-success)', fontWeight: 700 }}>
              <Icon name="check" size={11} /> подписан
            </span>
          )}
        </div>
        <span style={{ fontSize: 11, color: 'var(--t-3)', fontFamily: 'JetBrains Mono, monospace' }}>
          TAP FOR DETAILS →
        </span>
      </div>

      {showDecal === 'like' && (
        <div
          style={{
            position: 'absolute',
            top: 24,
            right: 24,
            zIndex: 5,
            padding: '8px 14px',
            border: '3px solid var(--c-pink)',
            color: 'var(--c-pink)',
            fontWeight: 900,
            fontSize: 24,
            letterSpacing: 2,
            transform: 'rotate(-12deg)',
            borderRadius: 8,
            textShadow: '0 0 12px rgba(255,79,216,0.6)',
            boxShadow: '0 0 24px rgba(255,79,216,0.5)',
          }}
        >
          LIKE
        </div>
      )}
      {showDecal === 'pass' && (
        <div
          style={{
            position: 'absolute',
            top: 24,
            left: 24,
            zIndex: 5,
            padding: '8px 14px',
            border: '3px solid #fff',
            color: '#fff',
            opacity: 0.85,
            fontWeight: 900,
            fontSize: 24,
            letterSpacing: 2,
            transform: 'rotate(12deg)',
            borderRadius: 8,
          }}
        >
          NOPE
        </div>
      )}
    </div>
  );
}

function NoProfilesBanner({ onCreate }) {
  return (
    <div
      className="glass"
      style={{
        margin: '0 16px 12px',
        padding: 16,
        borderRadius: 22,
        display: 'flex',
        gap: 12,
        background: 'linear-gradient(135deg, rgba(139,92,255,0.20), rgba(22,139,255,0.10))',
        border: '1px solid rgba(139,92,255,0.30)',
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 14,
          background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
          color: '#fff',
          boxShadow: '0 0 20px var(--accent-glow)',
        }}
      >
        <Icon name="controller" size={20} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 14 }}>Создайте первую игровую анкету</div>
        <div style={{ fontSize: 12, color: 'var(--t-2)', marginTop: 4, lineHeight: 1.45 }}>
          Без анкеты другие игроки не смогут понять, с кем и во что вы играете
        </div>
        <button
          onClick={onCreate}
          className="btn btn-primary"
          style={{ marginTop: 10, padding: '8px 14px', fontSize: 13, height: 'auto' }}
        >
          <Icon name="controller" size={14} /> Создать анкету
        </button>
      </div>
    </div>
  );
}

const FILTER_GAMES = ['mlbb', 'magic_chess', 'pubg', 'genshin', 'honkai', 'zzz', 'csgo'];

export function SearchScreen({ go, onOpenChat, onHome }) {
  const { state } = useStore();
  const hasProfiles = state.profiles.some((p) => p.status === 'active');

  // По умолчанию выбираем игру, по которой у пользователя есть анкета.
  const defaultGame = useMemo(() => {
    const active = state.profiles.find((p) => p.status === 'active');
    if (active) return GAME_KEY_FROM_CODE[active.game] || 'mlbb';
    return 'mlbb';
  }, [state.profiles]);

  const [filter, setFilter] = useState(defaultGame);
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);
  const [exit, setExit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setIdx(0);
    setItems([]);
    const backendGame = GAME_BACKEND_CODE[filter] || filter;
    searchPlayers({ game: backendGame, limit: 50 })
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
  }, [filter, reloadKey]);

  const current = items[idx];
  const next = items[idx + 1];

  const guard = (msg) => {
    haptic('warning');
    showAlert(msg);
  };

  const swipe = async (dir) => {
    if (!current || actionBusy) return;
    if (dir === 'like' && !hasProfiles) {
      guard('Сначала создайте игровую анкету, чтобы лайкать игроков');
      return;
    }
    haptic(dir === 'like' ? 'success' : 'light');
    setExit(dir);
    if (dir === 'like') {
      setActionBusy(true);
      try {
        const res = await likeUser(current.owner.id, GAME_BACKEND_CODE[filter] || filter);
        if (res?.mutual) {
          showAlert(`Взаимный лайк с ${current.owner.nickname || 'игроком'}!`);
        }
      } catch (e) {
        showAlert(e?.message || 'Не удалось лайкнуть');
      } finally {
        setActionBusy(false);
      }
    }
    setTimeout(() => {
      setIdx((i) => i + 1);
      setExit(null);
    }, 320);
  };

  const openMessage = async () => {
    if (!current) return;
    if (!hasProfiles) {
      guard('Сначала создайте игровую анкету, чтобы писать игрокам');
      return;
    }
    if (actionBusy) return;
    setActionBusy(true);
    haptic('medium');
    try {
      const res = await startChat(current.owner.id);
      onOpenChat?.({
        chat_id: res.chat_id,
        counterpart: res.counterpart || current.owner,
      });
    } catch (e) {
      showAlert(e?.message || 'Не удалось начать чат');
    } finally {
      setActionBusy(false);
    }
  };

  const filterOptions = FILTER_GAMES.filter((k) => GAME_OPTIONS[k]?.enabled).map((k) => ({
    id: k,
    label: GAME_OPTIONS[k].name,
  }));

  const exhausted = !loading && !error && items.length === 0;
  const allViewed = !loading && !error && items.length > 0 && idx >= items.length;

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
          title="Поиск тиммейта"
          subtitle={`${items.length} ${items.length === 1 ? 'игрок' : items.length < 5 ? 'игрока' : 'игроков'} · ${(GAME_OPTIONS[filter]?.name || filter)}`}
          onHome={onHome}
        />

        {!hasProfiles && <NoProfilesBanner onCreate={() => go('create-game')} />}

        <div className="scroll-x" style={{ display: 'flex', gap: 8, padding: '0 16px 14px', overflowX: 'auto' }}>
          {filterOptions.map((c) => (
            <span
              key={c.id}
              onClick={() => setFilter(c.id)}
              className={cls('chip', filter === c.id && 'chip-accent')}
              style={{ padding: '8px 14px', fontSize: 12, flexShrink: 0 }}
            >
              {c.label}
            </span>
          ))}
        </div>

        <div style={{ position: 'relative', flex: 1, padding: '0 16px', minHeight: 0 }}>
          {loading && (
            <div
              style={{
                color: 'var(--t-2)',
                fontSize: 13,
                textAlign: 'center',
                padding: 40,
              }}
            >
              Загружаем тиммейтов…
            </div>
          )}
          {error && (
            <EmptyState
              icon={<Icon name="x" size={28} />}
              title="Ошибка загрузки"
              subtitle={error}
            />
          )}
          {exhausted && (
            <EmptyState
              icon={<Icon name="search" size={28} />}
              title="По этой игре пока никого"
              subtitle="Попробуй другую игру в фильтре сверху или зайди позже"
            />
          )}
          {allViewed && (
            <EmptyState
              icon={<Icon name="check" size={28} />}
              title="Это все игроки"
              subtitle="На сегодня вы пересмотрели всех. Возвращайтесь позже"
              action={
                <button
                  onClick={() => setReloadKey((k) => k + 1)}
                  className="btn btn-secondary"
                  style={{ marginTop: 12 }}
                >
                  Обновить список
                </button>
              }
            />
          )}

          {!loading && !error && current && (
            <>
              {next && (
                <div
                  style={{
                    position: 'absolute',
                    top: 8,
                    left: 26,
                    right: 26,
                    bottom: 16,
                    transform: 'scale(0.96)',
                    opacity: 0.55,
                    pointerEvents: 'none',
                  }}
                >
                  <PlayerCard item={next} />
                </div>
              )}
              <div
                style={{
                  position: 'relative',
                  height: '100%',
                  transform:
                    exit === 'like'
                      ? 'translateX(120%) rotate(15deg)'
                      : exit === 'pass'
                        ? 'translateX(-120%) rotate(-15deg)'
                        : 'translateX(0) rotate(0deg)',
                  opacity: exit ? 0 : 1,
                  transition: 'transform 320ms cubic-bezier(.2,.8,.3,1), opacity 320ms',
                }}
              >
                <PlayerCard
                  item={current}
                  showDecal={exit}
                  onTap={() => {
                    const owner = current?.owner;
                    if (!owner?.id) return;
                    haptic('light');
                    go('user-profile', { id: owner.id, fallback: owner });
                  }}
                />
              </div>
            </>
          )}
        </div>

        {!loading && !error && current && !allViewed && (
          <div
            style={{
              padding: '14px 16px 132px',
              display: 'flex',
              justifyContent: 'center',
              gap: 18,
              alignItems: 'center',
            }}
          >
            <ActionFab icon="x" size={56} kind="pass" onClick={() => swipe('pass')} />
            <ActionFab icon="chat" size={48} kind="msg" onClick={openMessage} disabled={!hasProfiles || actionBusy} />
            <ActionFab
              icon="heart-fill"
              size={68}
              kind="like"
              onClick={() => swipe('like')}
              disabled={!hasProfiles || actionBusy}
            />
            <ActionFab icon="next" size={56} kind="next" onClick={() => swipe('pass')} />
          </div>
        )}
      </div>

      <BottomNav active="search" onChange={go} />
    </div>
  );
}
