import { useState } from 'react';
import { cls } from '../../components/Icon.jsx';
import { StepShell } from '../../components/StepShell.jsx';
import { LOOKING_FOR, MICROPHONE, PLAY_STYLES, PLAY_TIME } from './games.js';
import { useStore } from '../../store.jsx';
import { haptic } from '../../telegram.js';

function ChipGroup({ options, value, onChange, multi = false }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {options.map((o) => {
        const active = multi ? value.includes(o.code) : value === o.code;
        return (
          <span
            key={o.code}
            onClick={() => {
              if (multi) {
                onChange(value.includes(o.code) ? value.filter((x) => x !== o.code) : [...value, o.code]);
              } else {
                onChange(o.code);
              }
            }}
            className={cls('chip', active && 'chip-accent')}
            style={{ padding: '8px 12px' }}
          >
            {o.label}
          </span>
        );
      })}
    </div>
  );
}

export function CreatePreferencesScreen({ go }) {
  const { state, dispatch } = useStore();
  const draft = state.createDraft || {};

  const [lookingFor, setLookingFor] = useState(draft.looking_for || ['ranked']);
  const [playStyle, setPlayStyle] = useState(draft.play_style || 'serious');
  const [microphone, setMicrophone] = useState(draft.microphone || 'yes');
  const [playTime, setPlayTime] = useState(draft.play_time || ['evening']);
  const [error, setError] = useState(null);

  const handleNext = () => {
    if (lookingFor.length === 0) {
      setError('Выберите хотя бы один вариант в "Ищу"');
      return;
    }
    if (playTime.length === 0) {
      setError('Выберите хотя бы один вариант в "Когда играю"');
      return;
    }
    haptic('light');
    dispatch({
      type: 'SET_CREATE_DRAFT',
      payload: {
        looking_for: lookingFor,
        play_style: playStyle,
        microphone,
        play_time: playTime,
      },
    });
    go('create-about');
  };

  return (
    <StepShell
      step={3}
      total={6}
      title="Что для вас важно"
      subtitle="Эти данные помогают подобрать совместимых тиммейтов"
      onBack={() => go('create-data')}
      footer={
        <button onClick={handleNext} className="btn btn-primary" style={{ width: '100%', height: 54 }}>
          Продолжить
        </button>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div>
          <div className="input-label">Ищу</div>
          <ChipGroup options={LOOKING_FOR} value={lookingFor} onChange={setLookingFor} multi />
        </div>
        <div>
          <div className="input-label">Стиль игры</div>
          <ChipGroup options={PLAY_STYLES} value={playStyle} onChange={setPlayStyle} />
        </div>
        <div>
          <div className="input-label">Микрофон</div>
          <ChipGroup options={MICROPHONE} value={microphone} onChange={setMicrophone} />
        </div>
        <div>
          <div className="input-label">Когда играю</div>
          <ChipGroup options={PLAY_TIME} value={playTime} onChange={setPlayTime} multi />
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
