import { useMemo, useState } from 'react';
import { StepShell } from '../../components/StepShell.jsx';
import { useStore } from '../../store.jsx';
import { haptic } from '../../telegram.js';

function calcAge(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return null;
  const today = new Date();
  let age = today.getFullYear() - y;
  const md = today.getMonth() + 1 - m;
  if (md < 0 || (md === 0 && today.getDate() < d)) age -= 1;
  return age;
}

function isValidDate(iso) {
  if (!iso) return false;
  const d = new Date(iso);
  return !Number.isNaN(d.getTime()) && iso === d.toISOString().slice(0, 10);
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function BirthDateScreen({ go }) {
  const { state, dispatch } = useStore();
  const [value, setValue] = useState(state.onboardingDraft.birth_date || '');
  const [error, setError] = useState(null);
  const age = useMemo(() => calcAge(value), [value]);

  const max = todayIso();
  const min = '1925-01-01';

  const handleContinue = () => {
    if (!isValidDate(value)) {
      setError('Введите корректную дату рождения');
      return;
    }
    if (value > max) {
      setError('Введите корректную дату рождения');
      return;
    }
    if (age == null || age < 13) {
      setError('Cyber Mate доступен пользователям от 13 лет');
      return;
    }
    if (age > 100) {
      setError('Введите корректную дату рождения');
      return;
    }
    haptic('success');
    dispatch({ type: 'SET_ONBOARDING_DRAFT', payload: { birth_date: value } });
    go('onb-gender');
  };

  return (
    <StepShell
      step={2}
      total={4}
      title="Укажите дату рождения"
      subtitle="Это нужно для безопасности и корректного подбора игроков"
      onBack={() => go('onb-language')}
      footer={
        <button onClick={handleContinue} className="btn btn-primary" style={{ width: '100%', height: 54 }}>
          Продолжить
        </button>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <div className="input-label">Дата рождения</div>
          <input
            type="date"
            className="input"
            value={value}
            min={min}
            max={max}
            onChange={(e) => {
              setValue(e.target.value);
              if (error) setError(null);
            }}
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 18,
              letterSpacing: '0.04em',
              colorScheme: 'dark',
            }}
          />
        </div>

        {age != null && age >= 0 && age <= 120 && !error && (
          <div
            className="glass"
            style={{
              padding: '14px 16px',
              borderRadius: 16,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 12,
                background: 'rgba(50,213,131,0.15)',
                border: '1px solid rgba(50,213,131,0.30)',
                display: 'grid',
                placeItems: 'center',
                color: 'var(--c-success)',
                fontWeight: 800,
                fontFamily: 'JetBrains Mono, monospace',
              }}
            >
              {age}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>
                {age} {age >= 11 && age <= 14 ? 'лет' : age % 10 === 1 ? 'год' : age % 10 >= 2 && age % 10 <= 4 ? 'года' : 'лет'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--t-2)' }}>Эта информация будет видна другим</div>
            </div>
          </div>
        )}

        {error && (
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 14,
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
