import { StepShell } from '../../components/StepShell.jsx';
import { useStore } from '../../store.jsx';
import { haptic } from '../../telegram.js';

const GENDERS = [
  { code: 'male', emoji: '👨', label: 'Мужской' },
  { code: 'female', emoji: '👩', label: 'Женский' },
  { code: 'hidden', emoji: '⚪', label: 'Не указывать' },
];

export function GenderScreen({ go }) {
  const { state, dispatch } = useStore();
  const current = state.onboardingDraft.gender;

  const pick = (code) => {
    haptic('select');
    dispatch({ type: 'SET_ONBOARDING_DRAFT', payload: { gender: code } });
    setTimeout(() => go('onb-nickname'), 120);
  };

  return (
    <StepShell
      step={2}
      total={3}
      title="Выберите гендер"
      subtitle="Эта информация будет отображаться в вашем профиле"
      onBack={() => go('onb-language')}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {GENDERS.map((g) => {
          const active = current === g.code;
          return (
            <button
              key={g.code}
              onClick={() => pick(g.code)}
              className="glass"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                padding: '18px 20px',
                borderRadius: 20,
                cursor: 'pointer',
                color: '#fff',
                textAlign: 'left',
                background: active
                  ? 'linear-gradient(135deg, rgba(139,92,255,0.30), rgba(22,139,255,0.18))'
                  : undefined,
                border: active
                  ? '1px solid rgba(139,92,255,0.55)'
                  : '1px solid rgba(255,255,255,0.10)',
                boxShadow: active ? '0 0 24px var(--accent-glow)' : 'none',
              }}
            >
              <span style={{ fontSize: 26 }}>{g.emoji}</span>
              <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: -0.2, flex: 1 }}>
                {g.label}
              </span>
              {active && (
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                    display: 'grid',
                    placeItems: 'center',
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path
                      d="m2 6 3 3 5-6"
                      stroke="#fff"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              )}
            </button>
          );
        })}
      </div>
    </StepShell>
  );
}
