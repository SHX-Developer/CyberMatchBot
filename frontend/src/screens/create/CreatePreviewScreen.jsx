import { useState } from 'react';
import { Icon, cls } from '../../components/Icon.jsx';
import { Avatar } from '../../components/ui.jsx';
import { StepShell } from '../../components/StepShell.jsx';
import { GAMES } from '../../data/mock.js';
import {
  GAME_BACKEND_CODE,
  GAME_OPTIONS,
  LOOKING_FOR,
  MICROPHONE,
  PLAY_STYLES,
  PLAY_TIME,
} from './games.js';
import { useStore } from '../../store.jsx';
import { createGameProfile } from '../../api.js';
import { haptic, showAlert } from '../../telegram.js';

function labelFor(options, code) {
  return options.find((o) => o.code === code)?.label;
}

export function CreatePreviewScreen({ go }) {
  const { state, dispatch } = useStore();
  const draft = state.createDraft || {};
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const opt = GAME_OPTIONS[draft.game] || GAME_OPTIONS.mlbb;
  const blockKey = draft.game in GAMES ? draft.game : 'mlbb';
  const g = GAMES[blockKey];
  const nick = state.user?.nickname || 'you';

  const publish = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    haptic('medium');
    try {
      const profile = await createGameProfile({
        game: GAME_BACKEND_CODE[draft.game] || draft.game,
        game_nickname: draft.game_nickname,
        game_id: draft.game_id,
        server_id: draft.server_id || null,
        region: draft.region || null,
        rank: draft.rank || null,
        main_role: draft.main_role,
        secondary_roles: draft.secondary_roles || [],
        looking_for: draft.looking_for || [],
        play_style: draft.play_style || null,
        microphone: draft.microphone || null,
        play_time_slots: draft.play_time || [],
        about: draft.about,
        screenshot_url: draft.screenshot_url || null,
      });
      dispatch({ type: 'ADD_PROFILE', payload: profile });
      haptic('success');
      showAlert('Анкета опубликована');
      go('search');
    } catch (e) {
      setError(e?.message || 'Не удалось опубликовать анкету');
      setSubmitting(false);
    }
  };

  return (
    <StepShell
      step={6}
      total={6}
      title="Так анкета будет видна другим"
      subtitle="Проверьте перед публикацией"
      onBack={() => go('create-shot')}
      footer={
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => go('create-game')}
            disabled={submitting}
            className="btn btn-secondary"
            style={{ flex: 1, height: 54 }}
          >
            <Icon name="edit" size={16} />
            Изменить
          </button>
          <button
            onClick={publish}
            disabled={submitting}
            className="btn btn-primary"
            style={{ flex: 2, height: 54, opacity: submitting ? 0.6 : 1 }}
          >
            <Icon name="check" size={16} />
            {submitting ? 'Публикуем…' : 'Опубликовать'}
          </button>
        </div>
      }
    >
      <div
        className="glass glass-strong"
        style={{
          borderRadius: 28,
          overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.10)',
        }}
      >
        {draft.screenshot_url ? (
          <img
            src={draft.screenshot_url}
            alt="screenshot"
            style={{ width: '100%', aspectRatio: '16/9', objectFit: 'cover', display: 'block' }}
          />
        ) : (
          <div
            className={cls('game-block', g.cls)}
            style={{
              height: 200,
              borderRadius: 0,
              padding: '20px 22px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              border: 'none',
            }}
          >
            <div className="gb-tag">{g.tag}</div>
            <div className="gb-name" style={{ fontSize: 48, whiteSpace: 'pre-line' }}>
              {g.name}
            </div>
          </div>
        )}

        <div style={{ padding: '0 20px', marginTop: -28, position: 'relative', display: 'flex', alignItems: 'flex-end', gap: 12 }}>
          <Avatar av="av-3" size={64} square label={(draft.game_nickname || nick)[0]?.toUpperCase()} ring />
          <div style={{ paddingBottom: 4, flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: -0.4, color: '#fff' }}>
              {draft.game_nickname || nick}
            </div>
            <div style={{ fontSize: 12, color: 'var(--t-2)', fontFamily: 'JetBrains Mono, monospace' }}>
              ID {draft.game_id}
              {draft.server_id ? ` · ${draft.server_id}` : ''}
            </div>
          </div>
        </div>

        <div style={{ padding: '14px 20px 0', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {draft.region && (
            <span className="chip">
              <Icon name="pin" size={11} /> {draft.region}
            </span>
          )}
          {draft.rank && (
            <span className="chip">
              <Icon name="crown" size={11} stroke="#FFC43D" /> {draft.rank}
            </span>
          )}
          {draft.main_role && <span className="chip chip-accent">★ {draft.main_role}</span>}
          {(draft.secondary_roles || []).map((r) => (
            <span key={r} className="chip">
              {r}
            </span>
          ))}
        </div>

        <div style={{ padding: '14px 20px 0' }}>
          <div className="section-title" style={{ marginBottom: 6 }}>
            О себе
          </div>
          <div style={{ fontSize: 14, color: '#E6E6F0', lineHeight: 1.45 }}>{draft.about}</div>
        </div>

        <div style={{ padding: '14px 20px 18px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {(draft.looking_for || []).map((c) => (
            <span key={c} className="chip">
              {labelFor(LOOKING_FOR, c)}
            </span>
          ))}
          {draft.play_style && draft.play_style !== 'any' && (
            <span className="chip">{labelFor(PLAY_STYLES, draft.play_style)}</span>
          )}
          {draft.microphone && draft.microphone !== 'any' && (
            <span className="chip">
              <Icon name="mic" size={11} /> {labelFor(MICROPHONE, draft.microphone)}
            </span>
          )}
          {(draft.play_time || []).map((c) => (
            <span key={c} className="chip">
              {labelFor(PLAY_TIME, c)}
            </span>
          ))}
        </div>
      </div>

      {error && (
        <div
          style={{
            marginTop: 12,
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
    </StepShell>
  );
}
