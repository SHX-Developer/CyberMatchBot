import { useEffect, useRef, useState } from 'react';
import { Icon, cls } from '../../components/Icon.jsx';
import { StepShell } from '../../components/StepShell.jsx';
import { checkNicknameAvailable, updateMe, validateNicknameLocal } from '../../api.js';
import { useStore } from '../../store.jsx';
import { haptic, showAlert } from '../../telegram.js';

const NICK_ERROR = {
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

const GENDERS = [
  { code: 'male', emoji: '👨', label: 'Мужской' },
  { code: 'female', emoji: '👩', label: 'Женский' },
  { code: 'hidden', emoji: '⚪', label: 'Скрыть' },
];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

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

export function ProfileEditScreen({ go }) {
  const { state, dispatch } = useStore();
  const user = state.user;

  const [nickname, setNickname] = useState(user?.nickname || '');
  const [birthDate, setBirthDate] = useState(user?.birth_date || '');
  const [gender, setGender] = useState(user?.gender || 'hidden');

  const [nickStatus, setNickStatus] = useState('idle');
  const [nickError, setNickError] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const debounceRef = useRef(null);
  const initialNick = (user?.nickname || '').toLowerCase();

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = nickname.trim().toLowerCase();
    if (!trimmed) {
      setNickStatus('idle');
      setNickError(null);
      return;
    }
    if (trimmed === initialNick) {
      setNickStatus('idle');
      setNickError(null);
      return;
    }
    const local = validateNicknameLocal(trimmed);
    if (!local.ok) {
      setNickStatus('invalid');
      setNickError(NICK_ERROR[local.code] || 'Некорректный никнейм');
      return;
    }
    setNickStatus('checking');
    setNickError(null);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await checkNicknameAvailable(trimmed);
        if (res.available) {
          setNickStatus('available');
          setNickError(null);
        } else {
          setNickStatus('invalid');
          setNickError(NICK_ERROR[res.reason] || 'Никнейм недоступен');
        }
      } catch (e) {
        setNickStatus('invalid');
        setNickError('Не удалось проверить никнейм');
      }
    }, 300);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [nickname, initialNick]);

  const dirty =
    nickname.trim().toLowerCase() !== initialNick ||
    birthDate !== (user?.birth_date || '') ||
    gender !== (user?.gender || 'hidden');

  const nickOk = nickStatus === 'available' || nickname.trim().toLowerCase() === initialNick;

  const handleSave = async () => {
    if (submitting) return;
    setError(null);

    const patch = {};
    const trimmedNick = nickname.trim().toLowerCase();
    if (trimmedNick !== initialNick) {
      if (nickStatus !== 'available') {
        setError('Проверьте никнейм');
        return;
      }
      patch.nickname = trimmedNick;
    }

    if (birthDate !== (user?.birth_date || '')) {
      const age = calcAge(birthDate);
      if (!birthDate || age == null || age < 13 || age > 100) {
        setError('Cyber Mate доступен пользователям от 13 лет');
        return;
      }
      patch.birth_date = birthDate;
    }

    if (gender !== (user?.gender || 'hidden')) {
      patch.gender = gender;
    }

    if (Object.keys(patch).length === 0) {
      go('profile');
      return;
    }

    setSubmitting(true);
    haptic('medium');
    try {
      const updated = await updateMe(patch);
      dispatch({ type: 'UPDATE_USER', patch: { ...updated, is_registered: true } });
      haptic('success');
      showAlert('Сохранено');
      go('profile');
    } catch (e) {
      const reason = e?.body?.detail?.reason;
      if (reason === 'taken') {
        setNickStatus('invalid');
        setNickError(NICK_ERROR.taken);
      } else if (reason === 'invalid') {
        setError('Введите корректную дату рождения');
      } else {
        setError(e?.message || 'Не удалось сохранить');
      }
      setSubmitting(false);
    }
  };

  return (
    <StepShell
      title="Изменить данные"
      subtitle="Обновите никнейм, дату рождения и гендер"
      onBack={() => go('profile')}
      footer={
        <button
          onClick={handleSave}
          disabled={!dirty || !nickOk || submitting}
          className="btn btn-primary"
          style={{
            width: '100%',
            height: 54,
            opacity: dirty && nickOk && !submitting ? 1 : 0.5,
            cursor: dirty && nickOk && !submitting ? 'pointer' : 'not-allowed',
          }}
        >
          {submitting ? 'Сохраняем…' : 'Сохранить'}
        </button>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div>
          <div className="input-label">Никнейм</div>
          <div style={{ position: 'relative' }}>
            <input
              className="input"
              value={nickname}
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              onChange={(e) => setNickname(e.target.value)}
              maxLength={20}
              style={{ fontFamily: 'JetBrains Mono, monospace', paddingRight: 44 }}
            />
            <div style={{ position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)' }}>
              {nickStatus === 'checking' && (
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
              {nickStatus === 'available' && (
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
                    <path d="m2 6 3 3 5-6" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              )}
              {nickStatus === 'invalid' && (
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
                    <path d="M2 2l6 6M8 2 2 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </span>
              )}
            </div>
          </div>
          <style>{`@keyframes cm-spin{to{transform:rotate(360deg)}}`}</style>
          {nickError && (
            <div
              style={{
                marginTop: 6,
                fontSize: 12,
                color: '#FF6961',
                fontWeight: 600,
              }}
            >
              {nickError}
            </div>
          )}
        </div>

        <div>
          <div className="input-label">Дата рождения</div>
          <input
            type="date"
            className="input"
            value={birthDate}
            min="1925-01-01"
            max={todayIso()}
            onChange={(e) => setBirthDate(e.target.value)}
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 16,
              colorScheme: 'dark',
            }}
          />
        </div>

        <div>
          <div className="input-label">Гендер</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {GENDERS.map((g) => (
              <button
                key={g.code}
                onClick={() => setGender(g.code)}
                className={cls('chip', gender === g.code && 'chip-accent')}
                style={{
                  flex: 1,
                  justifyContent: 'center',
                  padding: '12px 8px',
                  fontSize: 13,
                  border: 'none',
                }}
              >
                <span style={{ fontSize: 18 }}>{g.emoji}</span>
                <span>{g.label}</span>
              </button>
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
