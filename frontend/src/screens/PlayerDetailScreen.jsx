import { Icon, cls } from '../components/Icon.jsx';
import {
  Avatar,
  BottomNav,
  CMBackground,
  StatPill,
  StatusBar,
  TopBar,
} from '../components/ui.jsx';
import { GAMES, PLAYERS } from '../data/mock.js';

export function PlayerDetailScreen({ go, player }) {
  const p = player || PLAYERS[1];
  const g = GAMES[p.game];
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
          title="Анкета"
          onBack={() => go('search')}
          right={
            <button
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.10)',
                width: 38,
                height: 38,
                borderRadius: 12,
                color: '#fff',
                display: 'grid',
                placeItems: 'center',
                cursor: 'pointer',
              }}
            >
              <Icon name="send" size={16} />
            </button>
          }
        />

        <div
          className={cls('game-block', g.cls)}
          style={{
            margin: '0 16px',
            borderRadius: 28,
            height: 240,
            padding: '22px 24px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div className="gb-tag">{g.tag}</div>
            <span className="chip" style={{ background: 'rgba(0,0,0,0.4)', borderColor: 'rgba(255,255,255,0.20)' }}>
              <Icon name="crown" size={11} stroke="#FFC43D" /> {p.rank}
            </span>
          </div>
          <div className="gb-name" style={{ fontSize: 64, whiteSpace: 'pre-line' }}>
            {g.name}
          </div>
        </div>

        <div
          style={{
            margin: '-32px 24px 0',
            position: 'relative',
            zIndex: 2,
            display: 'flex',
            alignItems: 'flex-end',
            gap: 14,
          }}
        >
          <Avatar av={p.av} size={84} square label={p.nick[0]} online={p.online} ring />
          <div style={{ flex: 1, paddingBottom: 6 }}>
            <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.6 }}>{p.nick}</div>
            <div style={{ fontSize: 13, color: 'var(--t-2)' }}>
              {p.handle} · {p.age} · {p.gender}
            </div>
          </div>
        </div>

        <div style={{ padding: '16px 16px 0', display: 'flex', gap: 8 }}>
          <StatPill label="ID Игры" value={p.gameId} />
          <StatPill label="Регион" value={p.region.split(' • ')[1] || p.region} />
        </div>

        <div style={{ padding: '14px 16px 0' }}>
          <div className="section-title" style={{ marginBottom: 8 }}>
            Роли
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            <span className="chip chip-accent">★ {p.role}</span>
            {p.altRoles.map((r) => (
              <span key={r} className="chip">
                {r}
              </span>
            ))}
          </div>
        </div>

        <div style={{ padding: '14px 16px 0' }}>
          <div className="section-title" style={{ marginBottom: 8 }}>
            О себе
          </div>
          <div
            className="glass"
            style={{ padding: 16, borderRadius: 18, fontSize: 14, lineHeight: 1.5, color: '#E6E6F0' }}
          >
            {p.bio}
          </div>
        </div>

        <div style={{ padding: '14px 16px 0' }}>
          <div
            className="glass"
            style={{ padding: 16, borderRadius: 22, display: 'flex', alignItems: 'center', gap: 14 }}
          >
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: '50%',
                background: 'conic-gradient(var(--accent) 280deg, rgba(255,255,255,0.08) 280deg)',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <div
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: '50%',
                  background: 'rgba(7,0,15,0.85)',
                  display: 'grid',
                  placeItems: 'center',
                  fontWeight: 800,
                  fontSize: 14,
                }}
              >
                78%
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>Совместимость высокая</div>
              <div style={{ fontSize: 12, color: 'var(--t-2)', marginTop: 2 }}>
                Тот же регион, удобное время, дополняющие роли
              </div>
            </div>
          </div>
        </div>

        <div style={{ padding: '14px 16px 0' }}>
          <div className="section-title" style={{ marginBottom: 8 }}>
            Активность
          </div>
          <div
            className="glass"
            style={{ padding: '12px 16px', borderRadius: 18, display: 'flex', alignItems: 'center', gap: 10 }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: p.online ? 'var(--c-success)' : 'var(--t-3)',
                boxShadow: p.online ? '0 0 12px var(--c-success)' : 'none',
              }}
            />
            <span style={{ fontSize: 14, fontWeight: 600 }}>{p.activity}</span>
          </div>
        </div>

        <div style={{ padding: '20px 16px 130px', display: 'flex', gap: 10 }}>
          <button onClick={() => go('search')} className="btn btn-secondary" style={{ flex: 1 }}>
            <Icon name="x" size={18} /> Дальше
          </button>
          <button onClick={() => go('chat')} className="btn btn-primary" style={{ flex: 2 }}>
            <Icon name="heart-fill" size={18} /> Лайкнуть
          </button>
        </div>
      </div>

      <BottomNav active="search" onChange={go} />
    </div>
  );
}
