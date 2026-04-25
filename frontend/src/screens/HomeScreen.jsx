import { useEffect, useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import {
  BottomNav,
  CMBackground,
  GameBlock,
  SectionHeading,
  StatusBar,
} from '../components/ui.jsx';
import { GAMES } from '../data/mock.js';
import { GAME_BACKEND_CODE } from './create/games.js';
import { getMyStats } from '../api.js';
import { useStore } from '../store.jsx';

const TOP_GAMES = ['mlbb', 'magic_chess', 'pubg', 'genshin', 'honkai', 'zzz', 'csgo'];

function QuickCard({ onClick, icon, label, hint, badge, gradient }) {
  return (
    <button
      onClick={onClick}
      className="glass"
      style={{
        textAlign: 'left',
        padding: 14,
        borderRadius: 22,
        color: '#fff',
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.10)',
        background: gradient,
        backdropFilter: 'blur(var(--frost))',
        WebkitBackdropFilter: 'blur(var(--frost))',
      }}
    >
      <div
        style={{
          width: 38,
          height: 38,
          borderRadius: 12,
          background: 'rgba(255,255,255,0.10)',
          border: '1px solid rgba(255,255,255,0.14)',
          display: 'grid',
          placeItems: 'center',
          marginBottom: 22,
        }}
      >
        <Icon name={icon} size={20} />
      </div>
      <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: -0.2 }}>{label}</div>
      <div style={{ fontSize: 11, color: 'var(--t-2)', marginTop: 2 }}>{hint}</div>
      {badge != null && Number(badge) > 0 && (
        <span
          style={{
            position: 'absolute',
            top: 12,
            right: 12,
            background: 'var(--c-pink)',
            color: '#fff',
            fontSize: 10,
            fontWeight: 800,
            padding: '3px 7px',
            borderRadius: 100,
            boxShadow: '0 0 14px rgba(255,79,216,0.6)',
          }}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

function plural(n, [one, few, many]) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

export function HomeScreen({ go }) {
  const { state } = useStore();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getMyStats()
      .then((s) => !cancelled && setStats(s))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [state.profiles.length]);

  const display =
    state.user?.nickname || state.user?.first_name || 'тиммейт';

  const profilesCount = stats?.profiles_count ?? state.profiles.length;
  const likesCount = stats?.likes_count ?? 0;
  const friendsCount = stats?.friends_count ?? 0;

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

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '4px 20px 0',
            gap: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flex: 1 }}>
            <Icon name="logo" size={32} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 800, fontSize: 17, letterSpacing: -0.4, whiteSpace: 'nowrap' }}>
                CYBER MATE
              </div>
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 9,
                  color: 'var(--t-2)',
                  letterSpacing: '0.14em',
                  whiteSpace: 'nowrap',
                }}
              >
                FIND YOUR TEAM
              </div>
            </div>
          </div>
          <button
            onClick={() => go('profile')}
            style={{
              width: 38,
              height: 38,
              borderRadius: 12,
              flexShrink: 0,
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.10)',
              color: '#fff',
              display: 'grid',
              placeItems: 'center',
              cursor: 'pointer',
            }}
          >
            <Icon name="user" size={18} />
          </button>
        </div>

        {/* Hero */}
        <div style={{ padding: '24px 20px 16px' }}>
          <div
            style={{
              fontSize: 36,
              lineHeight: 1.0,
              fontWeight: 800,
              letterSpacing: -1.2,
              marginBottom: 14,
            }}
          >
            Привет,
            <br />
            <span
              style={{
                background: 'linear-gradient(120deg, var(--accent), var(--accent-2))',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              {display}
            </span>
            <br />
            <span style={{ color: 'var(--t-2)', fontWeight: 700, fontSize: 28 }}>
              готов к катке?
            </span>
          </div>
          <div
            style={{
              color: 'var(--t-2)',
              fontSize: 14,
              lineHeight: 1.5,
              maxWidth: 320,
            }}
          >
            {profilesCount === 0
              ? 'Начни с создания игровой анкеты — без неё другие игроки тебя не увидят.'
              : `${profilesCount} ${plural(profilesCount, ['анкета', 'анкеты', 'анкет'])} · ${friendsCount} ${plural(friendsCount, ['друг', 'друга', 'друзей'])} · ${likesCount} ${plural(likesCount, ['лайк', 'лайка', 'лайков'])}`}
          </div>

          <button
            onClick={() => go(profilesCount === 0 ? 'create-game' : 'search')}
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 22, height: 56, fontSize: 17 }}
          >
            <Icon name={profilesCount === 0 ? 'controller' : 'search'} size={20} />
            {profilesCount === 0 ? 'Создать анкету' : 'Найти тиммейта'}
          </button>
        </div>

        {/* Quick actions grid */}
        <div style={{ padding: '4px 20px 0' }}>
          <SectionHeading>Быстрые действия</SectionHeading>
        </div>
        <div
          style={{
            padding: '0 20px',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 10,
          }}
        >
          <QuickCard
            onClick={() => go('search')}
            icon="search"
            label="Найти тиммейта"
            hint="свайпы и лайки"
            gradient="linear-gradient(135deg, rgba(139,92,255,0.35), rgba(22,139,255,0.15))"
          />
          <QuickCard
            onClick={() => go('profiles')}
            icon="controller"
            label="Мои анкеты"
            hint={
              profilesCount === 0
                ? 'нет анкет'
                : `${profilesCount} ${plural(profilesCount, ['анкета', 'анкеты', 'анкет'])}`
            }
            gradient="linear-gradient(135deg, rgba(255,79,216,0.30), rgba(139,92,255,0.10))"
          />
          <QuickCard
            onClick={() => go('chats')}
            icon="chat"
            label="Сообщения"
            hint="новые чаты появятся здесь"
            gradient="linear-gradient(135deg, rgba(22,139,255,0.30), rgba(50,213,131,0.10))"
          />
          <QuickCard
            onClick={() => go('activity')}
            icon="star"
            label="Активность"
            hint={`${likesCount} ${plural(likesCount, ['лайк', 'лайка', 'лайков'])}`}
            gradient="linear-gradient(135deg, rgba(255,196,61,0.20), rgba(255,79,216,0.10))"
          />
        </div>

        {/* Featured games */}
        <div style={{ padding: '20px 20px 0' }}>
          <SectionHeading
            action={
              <button
                onClick={() => go('search')}
                className="btn btn-ghost"
                style={{ padding: '4px 8px', fontSize: 12 }}
              >
                Поиск →
              </button>
            }
          >
            Поддерживаемые игры
          </SectionHeading>
        </div>
        <div
          className="scroll-x"
          style={{ display: 'flex', gap: 12, padding: '0 20px 24px', overflowX: 'auto' }}
        >
          {TOP_GAMES.filter((g) => GAMES[g]).map((g) => (
            <button
              key={g}
              onClick={() => go('search')}
              style={{
                flexShrink: 0,
                width: 140,
                background: 'transparent',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <GameBlock game={g} size="sm" />
            </button>
          ))}
        </div>

        <div style={{ height: 110 }} />
      </div>

      <BottomNav active="home" onChange={go} />
    </div>
  );
}
