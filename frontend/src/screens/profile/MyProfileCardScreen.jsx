import { useState } from 'react';
import { Icon, cls } from '../../components/Icon.jsx';
import {
  Avatar,
  CMBackground,
  StatusBar,
  TopBar,
} from '../../components/ui.jsx';
import { GAMES } from '../../data/mock.js';
import {
  GAME_KEY_FROM_CODE,
  LOOKING_FOR,
  MICROPHONE,
  PLAY_STYLES,
  PLAY_TIME,
} from '../create/games.js';
import { useStore } from '../../store.jsx';
import { deleteProfile, updateProfileStatus } from '../../api.js';
import { haptic, showAlert, showPopup } from '../../telegram.js';

const STATUS_LABEL = {
  active: 'Активна',
  paused: 'На паузе',
  draft: 'Черновик',
  moderation: 'На модерации',
  rejected: 'Отклонена',
};

function labelFor(options, code) {
  return options.find((o) => o.code === code)?.label;
}

function profileToDraft(profile) {
  return {
    game: GAME_KEY_FROM_CODE[profile.game] || profile.game,
    game_nickname: profile.game_nickname || '',
    game_id: profile.game_id || profile.game_player_id || '',
    server_id: profile.server_id || '',
    region: profile.region || '',
    rank: profile.rank || '',
    main_role: profile.main_role || profile.role || '',
    secondary_roles: profile.secondary_roles || [],
    looking_for: profile.looking_for || [],
    play_style: profile.play_style || '',
    microphone: profile.microphone || '',
    play_time: profile.play_time_slots || [],
    about: profile.about || profile.description || '',
    screenshot_url: profile.screenshot_url || null,
    screenshot_meta: null,
  };
}

export function MyProfileCardScreen({ go, profile }) {
  const { state, dispatch } = useStore();
  const [busy, setBusy] = useState(false);

  if (!profile) {
    return (
      <div style={{ position: 'relative', height: '100%' }}>
        <CMBackground style="aurora" />
        <div style={{ position: 'relative', zIndex: 2, padding: 20 }}>
          <StatusBar />
          <TopBar title="Анкета" onBack={() => go('profiles')} />
          <div style={{ color: 'var(--t-2)', textAlign: 'center', marginTop: 40 }}>
            Анкета не найдена
          </div>
        </div>
      </div>
    );
  }

  const wizardKey = GAME_KEY_FROM_CODE[profile.game] || profile.game;
  const blockKey = wizardKey in GAMES ? wizardKey : 'mlbb';
  const g = GAMES[blockKey];
  const owner = state.user;
  const active = profile.status === 'active';

  const handleEdit = () => {
    haptic('light');
    dispatch({ type: 'CLEAR_CREATE_DRAFT' });
    dispatch({ type: 'SET_CREATE_DRAFT', payload: profileToDraft(profile) });
    go('create-data');
  };

  const handleToggle = async () => {
    if (busy) return;
    haptic('light');
    setBusy(true);
    const next = active ? 'paused' : 'active';
    try {
      const updated = await updateProfileStatus(profile.id, next);
      dispatch({ type: 'UPDATE_PROFILE', id: profile.id, patch: updated });
    } catch (e) {
      showAlert('Не удалось обновить статус');
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (busy) return;
    const choice = await showPopup({
      title: 'Удалить анкету?',
      message: `Анкета по ${g.name.replace('\n', ' ')} будет удалена. Это действие нельзя отменить.`,
      buttons: [
        { id: 'cancel', type: 'cancel' },
        { id: 'delete', type: 'destructive', text: 'Удалить' },
      ],
    });
    if (choice !== 'delete') return;
    haptic('warning');
    setBusy(true);
    try {
      await deleteProfile(profile.id);
      dispatch({ type: 'DELETE_PROFILE', id: profile.id });
      go('profiles');
    } catch (e) {
      showAlert('Не удалось удалить анкету');
      setBusy(false);
    }
  };

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
        style={{ position: 'relative', zIndex: 2, flex: 1, overflow: 'auto' }}
        className="no-scrollbar"
      >
        <StatusBar />
        <TopBar
          title="Моя анкета"
          subtitle={STATUS_LABEL[profile.status] || profile.status}
          onBack={() => go('profiles')}
          right={
            <button
              onClick={handleEdit}
              aria-label="Редактировать"
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.10)',
                width: 38,
                height: 38,
                borderRadius: 12,
                color: '#fff',
                display: 'grid',
                placeItems: 'center',
                cursor: 'pointer',
              }}
            >
              <Icon name="edit" size={16} />
            </button>
          }
        />

        {/* Hero — скриншот или геймблок */}
        <div style={{ padding: '0 16px' }}>
          <div
            className="glass glass-strong"
            style={{
              borderRadius: 28,
              overflow: 'hidden',
              border: '1px solid rgba(255,255,255,0.10)',
            }}
          >
            {profile.screenshot_url ? (
              <img
                src={profile.screenshot_url}
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div className="gb-tag">{g.tag}</div>
                  {profile.rank && (
                    <span
                      className="chip"
                      style={{
                        background: 'rgba(0,0,0,0.4)',
                        borderColor: 'rgba(255,255,255,0.20)',
                      }}
                    >
                      <Icon name="crown" size={11} stroke="#FFC43D" /> {profile.rank}
                    </span>
                  )}
                </div>
                <div className="gb-name" style={{ fontSize: 48, whiteSpace: 'pre-line' }}>
                  {g.name}
                </div>
              </div>
            )}

            {/* Identity */}
            <div
              style={{
                padding: '0 20px',
                marginTop: -28,
                position: 'relative',
                zIndex: 2,
                display: 'flex',
                alignItems: 'flex-end',
                gap: 12,
              }}
            >
              <Avatar
                av="av-3"
                size={64}
                square
                label={(profile.game_nickname || owner?.nickname || '?')[0]?.toUpperCase()}
                ring
              />
              <div style={{ paddingBottom: 4, flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 800,
                    letterSpacing: -0.4,
                    color: '#fff',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {profile.game_nickname || owner?.nickname || '—'}
                </div>
                {(profile.game_id || profile.server_id) && (
                  <div
                    style={{
                      fontSize: 12,
                      color: 'var(--t-2)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    ID {profile.game_id}
                    {profile.server_id ? ` · ${profile.server_id}` : ''}
                  </div>
                )}
              </div>
            </div>

            {/* meta chips */}
            <div style={{ padding: '14px 20px 0', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {profile.region && (
                <span className="chip">
                  <Icon name="pin" size={11} /> {profile.region}
                </span>
              )}
              {profile.rank && profile.screenshot_url && (
                <span className="chip">
                  <Icon name="crown" size={11} stroke="#FFC43D" /> {profile.rank}
                </span>
              )}
              {profile.main_role && <span className="chip chip-accent">★ {profile.main_role}</span>}
              {(profile.secondary_roles || []).map((r) => (
                <span key={r} className="chip">
                  {r}
                </span>
              ))}
            </div>

            {/* about */}
            {profile.about && (
              <div style={{ padding: '14px 20px 0' }}>
                <div className="section-title" style={{ marginBottom: 6 }}>
                  О себе
                </div>
                <div style={{ fontSize: 14, color: '#E6E6F0', lineHeight: 1.45 }}>
                  {profile.about}
                </div>
              </div>
            )}

            {/* preferences */}
            {(profile.looking_for?.length ||
              profile.play_style ||
              profile.microphone ||
              profile.play_time_slots?.length) > 0 && (
              <div style={{ padding: '14px 20px 0' }}>
                <div className="section-title" style={{ marginBottom: 6 }}>
                  Предпочтения
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(profile.looking_for || []).map((c) => (
                    <span key={c} className="chip">
                      {labelFor(LOOKING_FOR, c) || c}
                    </span>
                  ))}
                  {profile.play_style && profile.play_style !== 'any' && (
                    <span className="chip">{labelFor(PLAY_STYLES, profile.play_style)}</span>
                  )}
                  {profile.microphone && profile.microphone !== 'any' && (
                    <span className="chip">
                      <Icon name="mic" size={11} /> {labelFor(MICROPHONE, profile.microphone)}
                    </span>
                  )}
                  {(profile.play_time_slots || []).map((c) => (
                    <span key={c} className="chip">
                      {labelFor(PLAY_TIME, c) || c}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div style={{ padding: '14px 20px 18px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  fontSize: 12,
                  color: 'var(--t-2)',
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: active ? 'var(--c-success)' : 'var(--t-3)',
                    boxShadow: active ? '0 0 8px var(--c-success)' : 'none',
                  }}
                />
                {STATUS_LABEL[profile.status] || profile.status}
              </div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div
          style={{
            padding: '20px 16px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <button
            onClick={handleEdit}
            disabled={busy}
            className="btn btn-primary"
            style={{ width: '100%', height: 54 }}
          >
            <Icon name="edit" size={18} />
            Редактировать
          </button>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={handleToggle}
              disabled={busy}
              className="btn btn-secondary"
              style={{ flex: 1, height: 50 }}
            >
              {active ? (
                <>
                  <Icon name="x" size={16} /> На паузу
                </>
              ) : (
                <>
                  <Icon name="check" size={16} /> Включить
                </>
              )}
            </button>
            <button
              onClick={handleDelete}
              disabled={busy}
              className="btn btn-danger"
              style={{ flex: 1, height: 50 }}
            >
              <Icon name="trash" size={16} /> Удалить
            </button>
          </div>
        </div>

        <div style={{ height: 130 }} />
      </div>
    </div>
  );
}
