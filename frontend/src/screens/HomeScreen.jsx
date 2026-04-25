import { Icon } from '../components/Icon.jsx';
import {
  Avatar,
  BottomNav,
  CMBackground,
  GameBlock,
  SectionHeading,
  StatusBar,
} from '../components/ui.jsx';
import { GAMES, PLAYERS } from '../data/mock.js';

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
      {badge && (
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

export function HomeScreen({ go }) {
  const onlinePlayers = PLAYERS.filter((p) => p.online);
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
            <Icon name="settings" size={18} />
          </button>
        </div>

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
            Найди
            <br />
            <span
              style={{
                background: 'linear-gradient(120deg, var(--accent), var(--accent-2))',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              тиммейта
            </span>
            <br />
            <span style={{ color: 'var(--t-2)', fontWeight: 700 }}>за пару секунд.</span>
          </div>
          <div
            style={{
              color: 'var(--t-2)',
              fontSize: 14,
              lineHeight: 1.5,
              maxWidth: 320,
            }}
          >
            Создавай игровые анкеты, лайкай игроков и собирай команду для катки.
          </div>

          <button
            onClick={() => go('search')}
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 22, height: 56, fontSize: 17 }}
          >
            <Icon name="search" size={20} />
            Найти тиммейта
          </button>
        </div>

        <div style={{ padding: '8px 20px 4px' }}>
          <SectionHeading>В сети сейчас · {onlinePlayers.length}</SectionHeading>
        </div>
        <div
          className="scroll-x"
          style={{ display: 'flex', gap: 10, padding: '0 20px 16px', overflowX: 'auto' }}
        >
          {[...onlinePlayers, ...PLAYERS.filter((p) => !p.online)].map((p) => (
            <div
              key={p.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 6,
                flexShrink: 0,
              }}
            >
              <Avatar av={p.av} size={56} label={p.nick[0]} online={p.online} ring />
              <div
                style={{
                  fontSize: 11,
                  color: '#fff',
                  fontWeight: 600,
                  maxWidth: 60,
                  textAlign: 'center',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {p.nick}
              </div>
            </div>
          ))}
        </div>

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
            hint="2 активных"
            gradient="linear-gradient(135deg, rgba(255,79,216,0.30), rgba(139,92,255,0.10))"
          />
          <QuickCard
            onClick={() => go('chats')}
            icon="chat"
            label="Сообщения"
            hint="3 новых"
            badge="3"
            gradient="linear-gradient(135deg, rgba(22,139,255,0.30), rgba(50,213,131,0.10))"
          />
          <QuickCard
            onClick={() => go('activity')}
            icon="star"
            label="Активность"
            hint="12 лайков"
            gradient="linear-gradient(135deg, rgba(255,196,61,0.20), rgba(255,79,216,0.10))"
          />
        </div>

        <div style={{ padding: '20px 20px 0' }}>
          <SectionHeading
            action={
              <button className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: 12 }}>
                Все →
              </button>
            }
          >
            Топ игры
          </SectionHeading>
        </div>
        <div
          className="scroll-x"
          style={{ display: 'flex', gap: 12, padding: '0 20px 24px', overflowX: 'auto' }}
        >
          {Object.keys(GAMES).map((g) => (
            <div key={g} style={{ flexShrink: 0, width: 140 }}>
              <GameBlock game={g} size="sm" />
              <div
                style={{
                  marginTop: 8,
                  fontSize: 11,
                  color: 'var(--t-2)',
                  fontFamily: 'JetBrains Mono, monospace',
                  letterSpacing: '0.1em',
                }}
              >
                {200 + g.length * 137} ИГРОКОВ
              </div>
            </div>
          ))}
        </div>

        <div style={{ height: 110 }} />
      </div>

      <BottomNav active="search" onChange={go} />
    </div>
  );
}
