import { Icon } from '../../components/Icon.jsx';
import { CMBackground, StatusBar } from '../../components/ui.jsx';
import { useStore } from '../../store.jsx';

export function RegisteredScreen({ go }) {
  const { state } = useStore();
  const nick = state.user?.nickname ?? '';

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
        style={{
          position: 'relative',
          zIndex: 2,
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          padding: '0 24px',
        }}
      >
        <StatusBar />

        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            textAlign: 'center',
            gap: 16,
          }}
        >
          <div
            style={{
              width: 96,
              height: 96,
              borderRadius: 28,
              background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
              display: 'grid',
              placeItems: 'center',
              boxShadow: '0 0 40px var(--accent-glow), 0 24px 60px rgba(0,0,0,0.4)',
              marginBottom: 8,
            }}
          >
            <svg width="46" height="46" viewBox="0 0 46 46" fill="none">
              <path
                d="m12 24 7 7 16-18"
                stroke="#fff"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: -0.8 }}>
            Профиль создан
          </div>
          {nick && (
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 14,
                color: 'var(--t-2)',
              }}
            >
              @{nick}
            </div>
          )}
          <div
            style={{
              fontSize: 15,
              color: 'var(--t-2)',
              lineHeight: 1.5,
              maxWidth: 320,
            }}
          >
            Теперь создайте игровую анкету, чтобы другие игроки могли найти вас
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            paddingBottom: 'calc(28px + var(--safe-bottom))',
          }}
        >
          <button
            onClick={() => go('create-game')}
            className="btn btn-primary"
            style={{ width: '100%', height: 56, fontSize: 17 }}
          >
            <Icon name="controller" size={20} />
            Создать анкету
          </button>
          <button
            onClick={() => go('search')}
            className="btn btn-secondary"
            style={{ width: '100%', height: 52 }}
          >
            <Icon name="search" size={18} />
            Посмотреть игроков
          </button>
        </div>
      </div>
    </div>
  );
}
