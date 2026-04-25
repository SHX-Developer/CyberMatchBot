import { Icon, cls } from './Icon.jsx';
import { GAMES } from '../data/mock.js';

export function Avatar({ av = 'av-1', size = 44, square = false, label, online = false, ring = false, src }) {
  const fontSize = Math.max(11, Math.round(size * 0.36));
  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <div
        className={cls('avatar', av, square && 'sq')}
        style={{
          width: size,
          height: size,
          fontSize,
          padding: 0,
          boxShadow: ring
            ? `0 0 0 2px var(--accent), 0 0 0 4px rgba(255,255,255,0.06), 0 0 0 1px rgba(255,255,255,0.10) inset, 0 8px 24px rgba(0,0,0,0.25)`
            : undefined,
        }}
      >
        {src ? (
          <img
            src={src}
            alt={label || 'avatar'}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              display: 'block',
              borderRadius: 'inherit',
            }}
          />
        ) : (
          label
        )}
      </div>
      {online && (
        <span
          style={{
            position: 'absolute',
            right: 0,
            bottom: 0,
            width: Math.max(10, size * 0.24),
            height: Math.max(10, size * 0.24),
            borderRadius: '50%',
            background: 'var(--c-success)',
            border: '2px solid #07000F',
          }}
        />
      )}
    </div>
  );
}

export function GameBlock({ game = 'mlbb', size = 'md', style, children }) {
  const g = GAMES[game] || GAMES.mlbb;
  const fontSize = size === 'lg' ? 56 : size === 'sm' ? 22 : 34;
  const pad = size === 'lg' ? '20px 22px 22px' : size === 'sm' ? '10px 12px 12px' : '14px 16px 16px';
  return (
    <div className={cls('game-block', g.cls)} style={{ padding: pad, ...style }}>
      <div className="gb-tag">{g.tag}</div>
      <div className="gb-name" style={{ fontSize, whiteSpace: 'pre-line' }}>
        {g.name}
      </div>
      {children}
    </div>
  );
}

export function BottomNav({ active, onChange }) {
  const tabs = [
    { id: 'home', icon: 'home', label: 'Главная' },
    { id: 'search', icon: 'search', label: 'Поиск' },
    { id: 'chats', icon: 'chat', label: 'Чаты' },
    { id: 'profiles', icon: 'controller', label: 'Анкеты' },
    { id: 'activity', icon: 'star', label: 'Актив' },
    { id: 'profile', icon: 'user', label: 'Профиль' },
  ];
  return (
    <div className="bottom-nav">
      {tabs.map((t) => {
        const on = t.id === active;
        return (
          <button
            key={t.id}
            onClick={() => onChange?.(t.id)}
            style={{
              border: 'none',
              background: 'transparent',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 3,
              height: '100%',
              cursor: 'pointer',
              color: on ? 'var(--accent)' : 'var(--t-2)',
              position: 'relative',
            }}
          >
            {on && (
              <span
                style={{
                  position: 'absolute',
                  top: 6,
                  width: 28,
                  height: 3,
                  borderRadius: 2,
                  background: 'var(--accent)',
                  boxShadow: '0 0 12px var(--accent-glow)',
                }}
              />
            )}
            <Icon name={t.icon} size={20} />
            <span
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: 0.15,
                textTransform: 'uppercase',
              }}
            >
              {t.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function StatusBar() {
  // Безусловный отступ под полосу с кнопками TG, плюс iOS safe-area-inset-top.
  return (
    <div
      style={{ height: 'calc(var(--tg-top-pad) + var(--safe-top))' }}
      aria-hidden="true"
    />
  );
}

// Визуальные кнопки back/home убраны: для возврата работает встроенная Telegram
// BackButton (см. setBackButton в telegram.js + App.jsx), а на главную ведёт
// первая иконка в BottomNav. props onBack/onHome оставлены для совместимости.
export function TopBar({ title, subtitle, onBack: _onBack, onHome: _onHome, right, transparent = false }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '6px 16px 12px',
        position: 'relative',
        zIndex: 5,
        background: transparent ? 'transparent' : 'rgba(7,0,15,0.0)',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 800, fontSize: 18, letterSpacing: -0.3, color: '#fff' }}>{title}</div>
        {subtitle && <div style={{ fontSize: 12, color: 'var(--t-2)', marginTop: 1 }}>{subtitle}</div>}
      </div>
      {right}
    </div>
  );
}

export function CMBackground({ style = 'aurora' }) {
  const variant = style === 'solid' ? 'cm-bg-solid' : style === 'gradient' ? 'cm-bg-gradient' : '';
  return <div className={cls('cm-bg', variant)} />;
}

export function SectionHeading({ children, action }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 4px',
        marginBottom: 10,
      }}
    >
      <span className="section-title">{children}</span>
      {action}
    </div>
  );
}

// Универсальный пустой стейт для разделов «нет чатов / нет лайков / нет друзей».
export function EmptyState({ icon, title, subtitle, action }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '40px 24px',
        gap: 14,
        color: 'var(--t-2)',
      }}
    >
      {icon && (
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: 20,
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.10)',
            display: 'grid',
            placeItems: 'center',
            color: 'var(--accent)',
          }}
        >
          {icon}
        </div>
      )}
      {title && (
        <div style={{ fontWeight: 700, fontSize: 16, color: '#fff' }}>{title}</div>
      )}
      {subtitle && (
        <div style={{ fontSize: 13, lineHeight: 1.5, maxWidth: 280 }}>
          {subtitle}
        </div>
      )}
      {action}
    </div>
  );
}

export function StatPill({ label, value, accent }) {
  return (
    <div className="glass" style={{ padding: '12px 14px', borderRadius: 18, flex: 1 }}>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: 700,
          fontSize: 22,
          color: accent || '#fff',
          letterSpacing: -0.5,
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: 11,
          color: 'var(--t-2)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          fontWeight: 700,
          marginTop: 2,
        }}
      >
        {label}
      </div>
    </div>
  );
}
