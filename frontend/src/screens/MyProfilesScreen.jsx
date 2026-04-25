import { Icon } from '../components/Icon.jsx';
import {
  BottomNav,
  CMBackground,
  GameBlock,
  StatusBar,
  TopBar,
} from '../components/ui.jsx';
import { GAMES } from '../data/mock.js';
import { GAME_BACKEND_CODE, GAME_KEY_FROM_CODE, GAME_OPTIONS } from './create/games.js';
import { useStore } from '../store.jsx';
import { haptic, showAlert } from '../telegram.js';
import { deleteProfile, updateProfileStatus } from '../api.js';

const STATUS_LABEL = {
  active: 'Активна',
  paused: 'На паузе',
  draft: 'Черновик',
};

function ProfileRow({ profile, onClick, onToggle, onDelete, onEdit }) {
  const wizardKey = GAME_KEY_FROM_CODE[profile.game] || profile.game;
  const blockKey = wizardKey in GAMES ? wizardKey : 'mlbb';
  const active = profile.status === 'active';
  return (
    <div
      onClick={onClick}
      className="glass"
      style={{
        padding: 0,
        borderRadius: 22,
        cursor: 'pointer',
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.10)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 0 }}>
        <div style={{ width: 110, flexShrink: 0 }}>
          <GameBlock
            game={blockKey}
            size="sm"
            style={{ borderRadius: 0, height: '100%', border: 'none' }}
          />
        </div>
        <div
          style={{
            flex: 1,
            padding: 14,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: active ? 'var(--c-success)' : 'var(--t-3)',
                  boxShadow: active ? '0 0 8px var(--c-success)' : 'none',
                }}
              />
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: active ? 'var(--c-success)' : 'var(--t-2)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                }}
              >
                {STATUS_LABEL[profile.status] || profile.status}
              </span>
            </div>
            <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: -0.3 }}>
              {profile.game_nickname}
            </div>
            <div style={{ fontSize: 12, color: 'var(--t-2)', marginTop: 2 }}>
              {profile.rank}
              {profile.main_role ? ` · ${profile.main_role}` : ''}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
              style={{
                flex: 1,
                height: 30,
                borderRadius: 10,
                border: '1px solid rgba(255,255,255,0.10)',
                background: 'rgba(255,255,255,0.05)',
                color: '#fff',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
              }}
            >
              <Icon name="edit" size={12} /> Изм.
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggle();
              }}
              style={{
                height: 30,
                padding: '0 10px',
                borderRadius: 10,
                border: '1px solid rgba(255,255,255,0.10)',
                background: 'rgba(255,255,255,0.05)',
                color: 'var(--t-2)',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {active ? 'Пауза' : 'Включить'}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              style={{
                width: 30,
                height: 30,
                borderRadius: 10,
                border: '1px solid rgba(255,59,48,0.30)',
                background: 'rgba(255,59,48,0.10)',
                color: '#FF6961',
                cursor: 'pointer',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <Icon name="trash" size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptySlot({ gameKey, onClick }) {
  const opt = GAME_OPTIONS[gameKey];
  return (
    <button
      onClick={onClick}
      className="glass"
      style={{
        textAlign: 'left',
        padding: 14,
        borderRadius: 22,
        color: '#fff',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        background: 'rgba(255,255,255,0.03)',
        border: '1px dashed rgba(255,255,255,0.18)',
        width: '100%',
      }}
    >
      <div
        style={{
          width: 60,
          height: 60,
          borderRadius: 16,
          background: 'rgba(255,255,255,0.04)',
          border: '1px dashed rgba(255,255,255,0.18)',
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
          color: 'var(--t-2)',
        }}
      >
        <Icon name="plus" size={22} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, fontSize: 16 }}>{opt.name}</div>
        <div style={{ fontSize: 12, color: 'var(--t-2)', marginTop: 2 }}>
          Анкета не создана · нажми, чтобы заполнить
        </div>
      </div>
      <Icon name="caret-right" size={18} stroke="var(--t-2)" />
    </button>
  );
}

export function MyProfilesScreen({ go, onHome }) {
  const { state, dispatch } = useStore();
  const profiles = state.profiles;
  const usedWizardKeys = new Set(
    profiles.map((p) => GAME_KEY_FROM_CODE[p.game] || p.game),
  );
  const emptyGames = Object.entries(GAME_OPTIONS)
    .filter(([k, opt]) => opt.enabled && !usedWizardKeys.has(k))
    .map(([k]) => k);

  const activeCount = profiles.filter((p) => p.status === 'active').length;

  const editProfile = (profile) => {
    haptic('light');
    dispatch({ type: 'CLEAR_CREATE_DRAFT' });
    dispatch({
      type: 'SET_CREATE_DRAFT',
      payload: {
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
      },
    });
    go('create-data');
  };

  const togglePause = async (profile) => {
    haptic('light');
    const next = profile.status === 'active' ? 'paused' : 'active';
    dispatch({ type: 'UPDATE_PROFILE', id: profile.id, patch: { status: next } });
    try {
      const updated = await updateProfileStatus(profile.id, next);
      dispatch({ type: 'UPDATE_PROFILE', id: profile.id, patch: updated });
    } catch (e) {
      // откат
      dispatch({ type: 'UPDATE_PROFILE', id: profile.id, patch: { status: profile.status } });
      showAlert('Не удалось обновить статус анкеты');
    }
  };

  const removeProfile = async (profile) => {
    haptic('warning');
    const prev = profiles;
    dispatch({ type: 'DELETE_PROFILE', id: profile.id });
    try {
      await deleteProfile(profile.id);
    } catch (e) {
      // откат
      dispatch({ type: 'ADD_PROFILE', payload: profile });
      showAlert('Не удалось удалить анкету');
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
      <div style={{ position: 'relative', zIndex: 2, flex: 1, overflow: 'auto' }} className="no-scrollbar">
        <StatusBar />
        <TopBar
          title="Мои анкеты"
          subtitle={`${activeCount} активных · ${emptyGames.length} доступно для создания`}
          onHome={onHome}
        />

        <div style={{ padding: '0 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {profiles.length === 0 && emptyGames.length === 0 && (
            <div className="glass" style={{ padding: 22, borderRadius: 22, textAlign: 'center' }}>
              <div style={{ fontWeight: 700, fontSize: 16 }}>Создайте первую анкету</div>
              <div style={{ fontSize: 13, color: 'var(--t-2)', marginTop: 6, lineHeight: 1.5 }}>
                Без анкеты другие игроки не смогут понять, с кем и во что вы играете
              </div>
              <button
                onClick={() => go('create-game')}
                className="btn btn-primary"
                style={{ marginTop: 14, width: '100%', height: 50 }}
              >
                <Icon name="controller" size={18} />
                Создать анкету
              </button>
            </div>
          )}

          {profiles.map((p) => (
            <ProfileRow
              key={p.id}
              profile={p}
              onClick={() => go('my-card', p)}
              onEdit={() => editProfile(p)}
              onToggle={() => togglePause(p)}
              onDelete={() => removeProfile(p)}
            />
          ))}

          {emptyGames.map((g) => (
            <EmptySlot
              key={g}
              gameKey={g}
              onClick={() => {
                dispatch({ type: 'CLEAR_CREATE_DRAFT' });
                dispatch({ type: 'SET_CREATE_DRAFT', payload: { game: g } });
                go('create-data');
              }}
            />
          ))}

          <div className="glass" style={{ padding: 16, borderRadius: 22, marginTop: 8, display: 'flex', gap: 12 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 12,
                background: 'rgba(255,196,61,0.15)',
                border: '1px solid rgba(255,196,61,0.30)',
                display: 'grid',
                placeItems: 'center',
                flexShrink: 0,
                color: '#FFC43D',
              }}
            >
              <Icon name="bolt" size={18} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>Заполни больше анкет</div>
              <div style={{ fontSize: 12, color: 'var(--t-2)', lineHeight: 1.45, marginTop: 2 }}>
                Игроки с 3+ анкетами получают на 4× больше лайков. Создай по анкете в каждой своей игре.
              </div>
            </div>
          </div>

          <div style={{ height: 130 }} />
        </div>
      </div>

      <BottomNav active="profiles" onChange={go} />
    </div>
  );
}
