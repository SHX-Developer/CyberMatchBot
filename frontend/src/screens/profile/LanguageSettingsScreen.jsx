import { useState } from 'react';
import { StepShell } from '../../components/StepShell.jsx';
import { updateMe } from '../../api.js';
import { useStore } from '../../store.jsx';
import { haptic, showAlert } from '../../telegram.js';

const LANGUAGES = [
  { code: 'ru', flag: '🇷🇺', label: 'Русский' },
  { code: 'uz', flag: '🇺🇿', label: "O'zbekcha" },
  { code: 'en', flag: '🇬🇧', label: 'English' },
];

export function LanguageSettingsScreen({ go }) {
  const { state, dispatch } = useStore();
  const [current, setCurrent] = useState(state.user?.language || 'ru');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const pick = async (code) => {
    if (saving || code === current) return;
    setError(null);
    setSaving(true);
    haptic('select');
    const prev = current;
    setCurrent(code);
    try {
      const updated = await updateMe({ language: code });
      dispatch({ type: 'UPDATE_USER', patch: { ...updated, is_registered: true } });
      haptic('success');
      showAlert('Язык обновлён');
    } catch (e) {
      setCurrent(prev);
      setError(e?.message || 'Не удалось сохранить');
    } finally {
      setSaving(false);
    }
  };

  return (
    <StepShell
      title="Язык"
      subtitle="Выберите язык интерфейса"
      onBack={() => go('profile')}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {LANGUAGES.map((l) => {
          const active = current === l.code;
          return (
            <button
              key={l.code}
              onClick={() => pick(l.code)}
              disabled={saving}
              className="glass"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                padding: '16px 18px',
                borderRadius: 18,
                cursor: saving ? 'wait' : 'pointer',
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
              <span style={{ fontSize: 24 }}>{l.flag}</span>
              <span style={{ fontSize: 16, fontWeight: 700, flex: 1 }}>{l.label}</span>
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
                    <path d="m2 6 3 3 5-6" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              )}
            </button>
          );
        })}

        {error && (
          <div
            style={{
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
      </div>
    </StepShell>
  );
}
