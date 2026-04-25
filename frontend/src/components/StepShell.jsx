import { Icon } from './Icon.jsx';
import { CMBackground, StatusBar } from './ui.jsx';

// Визуальной кнопки back нет — для возврата работает встроенная TG BackButton.
// onBack оставлен в сигнатуре для совместимости вызовов.
export function StepShell({
  step,
  total,
  title,
  subtitle,
  onBack: _onBack,
  children,
  footer,
  scrollable = true,
}) {
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
          minHeight: 0,
        }}
      >
        <StatusBar />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '6px 16px 14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Icon name="logo" size={28} />
            <div
              style={{
                fontWeight: 800,
                fontSize: 14,
                letterSpacing: -0.2,
                whiteSpace: 'nowrap',
              }}
            >
              CYBER MATE
            </div>
          </div>
          {step != null && total != null && (
            <div
              style={{
                marginLeft: 'auto',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: 'var(--t-2)',
                letterSpacing: '0.06em',
              }}
            >
              {step} / {total}
            </div>
          )}
        </div>

        {step != null && total != null && (
          <div style={{ padding: '0 16px 18px' }}>
            <div
              style={{
                height: 4,
                borderRadius: 2,
                background: 'rgba(255,255,255,0.08)',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${(step / total) * 100}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, var(--accent), var(--accent-2))',
                  borderRadius: 2,
                  transition: 'width 280ms ease',
                }}
              />
            </div>
          </div>
        )}

        <div
          className="no-scrollbar"
          style={{
            flex: 1,
            minHeight: 0,
            overflow: scrollable ? 'auto' : 'hidden',
            padding: '0 20px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {(title || subtitle) && (
            <div style={{ marginBottom: 22 }}>
              {title && (
                <div
                  style={{
                    fontSize: 28,
                    fontWeight: 800,
                    letterSpacing: -0.8,
                    lineHeight: 1.1,
                    marginBottom: 8,
                  }}
                >
                  {title}
                </div>
              )}
              {subtitle && (
                <div
                  style={{
                    fontSize: 14,
                    color: 'var(--t-2)',
                    lineHeight: 1.5,
                  }}
                >
                  {subtitle}
                </div>
              )}
            </div>
          )}
          {children}
          <div style={{ height: 24 }} />
        </div>

        {footer && (
          <div
            style={{
              padding: '12px 20px calc(20px + var(--safe-bottom))',
              borderTop: '1px solid rgba(255,255,255,0.06)',
              background: 'rgba(7,0,15,0.55)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
