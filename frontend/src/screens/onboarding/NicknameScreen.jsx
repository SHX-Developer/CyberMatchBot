import { useEffect, useRef, useState } from 'react';
import { StepShell } from '../../components/StepShell.jsx';
import { useStore } from '../../store.jsx';
import { checkNicknameAvailable, registerUser, validateNicknameLocal } from '../../api.js';
import { haptic } from '../../telegram.js';

const ERROR_MSG = {
  empty: 'Введите никнейм',
  too_short: 'Минимум 3 символа',
  too_long: 'Максимум 20 символов',
  bad_chars: 'Используйте только латинские буквы, цифры и _',
  leading_underscore: 'Никнейм не может начинаться с _',
  trailing_underscore: 'Никнейм не может заканчиваться на _',
  double_underscore: 'Нельзя использовать два _ подряд',
  bad_format: 'Используйте только латинские буквы, цифры и _',
  forbidden: 'Этот никнейм недоступен',
  taken: 'Никнейм уже занят',
};

export function NicknameScreen({ go }) {
  const { state, dispatch } = useStore();
  const [value, setValue] = useState(state.onboardingDraft.nickname || '');
  const [status, setStatus] = useState('idle'); // idle | checking | available | invalid
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = value.trim().toLowerCase();
    if (!trimmed) {
      setStatus('idle');
      setError(null);
      return;
    }
    const local = validateNicknameLocal(trimmed);
    if (!local.ok) {
      setStatus('invalid');
      setError(ERROR_MSG[local.code] || 'Некорректный никнейм');
      return;
    }
    setStatus('checking');
    setError(null);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await checkNicknameAvailable(trimmed);
        if (res.available) {
          setStatus('available');
          setError(null);
        } else {
          setStatus('invalid');
          setError(ERROR_MSG[res.reason] || 'Никнейм недоступен');
        }
      } catch (e) {
        setStatus('invalid');
        setError('Не удалось проверить никнейм. Попробуйте ещё раз');
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [value]);

  const handleSubmit = async () => {
    if (status !== 'available' || submitting) return;
    const nickname = value.trim().toLowerCase();
    setSubmitting(true);
    haptic('medium');
    dispatch({ type: 'SET_ONBOARDING_DRAFT', payload: { nickname } });

    const draft = { ...state.onboardingDraft, nickname };
    try {
      const res = await registerUser({
        language: draft.language,
        birth_date: draft.birth_date,
        gender: draft.gender,
        nickname,
      });
      dispatch({
        type: 'COMPLETE_REGISTRATION',
        user: { ...res.user, is_registered: true },
      });
      haptic('success');
      go('onb-done');
    } catch (e) {
      const reason = e?.body?.detail?.reason || e?.body?.detail;
      if (reason === 'taken') {
        setStatus('invalid');
        setError(ERROR_MSG.taken);
      } else {
        setError('Не удалось завершить регистрацию. Попробуйте ещё раз');
      }
      setSubmitting(false);
    }
  };

  return (
    <StepShell
      step={4}
      total={4}
      title="Придумайте никнейм"
      subtitle="По нему другие игроки смогут найти вас внутри Cyber Mate"
      onBack={() => go('onb-gender')}
      footer={
        <button
          onClick={handleSubmit}
          disabled={status !== 'available' || submitting}
          className="btn btn-primary"
          style={{
            width: '100%',
            height: 54,
            opacity: status === 'available' && !submitting ? 1 : 0.5,
            cursor: status === 'available' && !submitting ? 'pointer' : 'not-allowed',
          }}
        >
          {submitting ? 'Сохраняем…' : 'Продолжить'}
        </button>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div>
          <div className="input-label">Никнейм</div>
          <div style={{ position: 'relative' }}>
            <input
              className="input"
              value={value}
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              onChange={(e) => setValue(e.target.value)}
              placeholder="например: shadowplayer"
              maxLength={20}
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                paddingRight: 44,
                letterSpacing: '0.02em',
              }}
            />
            <div
              style={{
                position: 'absolute',
                right: 14,
                top: '50%',
                transform: 'translateY(-50%)',
              }}
            >
              {status === 'checking' && (
                <span
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    border: '2px solid rgba(255,255,255,0.18)',
                    borderTopColor: 'var(--accent)',
                    display: 'block',
                    animation: 'cm-spin 700ms linear infinite',
                  }}
                />
              )}
              {status === 'available' && (
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    background: 'var(--c-success)',
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
              {status === 'invalid' && (
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    background: 'rgba(255,59,48,0.20)',
                    border: '1px solid rgba(255,59,48,0.5)',
                    display: 'grid',
                    placeItems: 'center',
                    color: '#FF6961',
                  }}
                >
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path
                      d="M2 2l6 6M8 2 2 8"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
              )}
            </div>
          </div>
          <style>{`@keyframes cm-spin{to{transform:rotate(360deg)}}`}</style>
        </div>

        {error ? (
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
        ) : (
          <div
            style={{
              fontSize: 12,
              color: 'var(--t-3)',
              lineHeight: 1.5,
              padding: '0 4px',
            }}
          >
            3–20 символов, латиница, цифры и <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>_</span>.
            Без пробелов и без двух <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>__</span> подряд.
          </div>
        )}
      </div>
    </StepShell>
  );
}
