import { useState } from 'react';
import { StepShell } from '../../components/StepShell.jsx';
import { ABOUT_TEMPLATES } from './games.js';
import { useStore } from '../../store.jsx';
import { haptic } from '../../telegram.js';

const MIN = 10;
const MAX = 300;

export function CreateAboutScreen({ go }) {
  const { state, dispatch } = useStore();
  const [text, setText] = useState(state.createDraft?.about || '');
  const [error, setError] = useState(null);

  const length = text.length;
  const tooShort = length > 0 && length < MIN;
  const okLength = length >= MIN && length <= MAX;

  const insertTemplate = (t) => {
    setText((cur) => (cur.trim().length === 0 ? t : `${cur.trim()}. ${t}`));
  };

  const handleNext = () => {
    const trimmed = text.trim();
    if (trimmed.length < MIN) {
      setError(`Минимум ${MIN} символов`);
      return;
    }
    if (trimmed.length > MAX) {
      setError(`Максимум ${MAX} символов`);
      return;
    }
    haptic('light');
    dispatch({ type: 'SET_CREATE_DRAFT', payload: { about: trimmed } });
    go('create-shot');
  };

  return (
    <StepShell
      step={4}
      total={6}
      title="Расскажите коротко о себе"
      subtitle="Что для вас важно в команде, когда играете, чего ждёте"
      onBack={() => go('create-prefs')}
      footer={
        <button
          onClick={handleNext}
          disabled={!okLength}
          className="btn btn-primary"
          style={{
            width: '100%',
            height: 54,
            opacity: okLength ? 1 : 0.5,
            cursor: okLength ? 'pointer' : 'not-allowed',
          }}
        >
          Продолжить
        </button>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <textarea
            className="input"
            rows={5}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              if (error) setError(null);
            }}
            maxLength={MAX}
            placeholder="Играю вечером, ищу адекватную команду для рейтинга"
            style={{ resize: 'none', fontFamily: 'inherit', minHeight: 120 }}
          />
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: 6,
              fontSize: 12,
              color: tooShort ? '#FF6961' : 'var(--t-3)',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            <span>
              {tooShort ? `Минимум ${MIN} символов` : ' '}
            </span>
            <span>
              {length} / {MAX}
            </span>
          </div>
        </div>

        <div>
          <div className="input-label">Быстрые шаблоны</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {ABOUT_TEMPLATES.map((t) => (
              <span
                key={t}
                onClick={() => insertTemplate(t)}
                className="chip"
                style={{ padding: '8px 12px' }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>

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
