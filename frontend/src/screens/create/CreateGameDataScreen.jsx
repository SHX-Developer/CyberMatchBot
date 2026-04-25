import { useState } from 'react';
import { Icon, cls } from '../../components/Icon.jsx';
import { StepShell } from '../../components/StepShell.jsx';
import { GAME_OPTIONS } from './games.js';
import { useStore } from '../../store.jsx';
import { haptic } from '../../telegram.js';

export function CreateGameDataScreen({ go }) {
  const { state, dispatch } = useStore();
  const draft = state.createDraft || {};
  const opt = GAME_OPTIONS[draft.game] || GAME_OPTIONS.mlbb;

  const [nick, setNick] = useState(draft.game_nickname || '');
  const [gameId, setGameId] = useState(draft.game_id || '');
  const [serverId, setServerId] = useState(draft.server_id || '');
  const [region, setRegion] = useState(draft.region || opt.regions[0]);
  const [rank, setRank] = useState(draft.rank || opt.ranks[0] || '');
  const [mainRole, setMainRole] = useState(draft.main_role || opt.roles[0] || '');
  const [secondaryRoles, setSecondaryRoles] = useState(draft.secondary_roles || []);
  const [error, setError] = useState(null);

  const toggleSecondary = (r) => {
    setSecondaryRoles((arr) => (arr.includes(r) ? arr.filter((x) => x !== r) : [...arr, r]));
  };

  const handleNext = () => {
    if (nick.trim().length < 2) {
      setError('Укажите игровой ник');
      return;
    }
    if (gameId.trim().length < 3) {
      setError('Укажите игровой ID');
      return;
    }
    if (opt.showServerId && serverId.trim().length < 2) {
      setError('Укажите Server ID');
      return;
    }
    if (!rank) {
      setError('Выберите ранг');
      return;
    }
    if (!mainRole) {
      setError('Выберите основную роль');
      return;
    }
    haptic('light');
    dispatch({
      type: 'SET_CREATE_DRAFT',
      payload: {
        game_nickname: nick.trim(),
        game_id: gameId.trim(),
        server_id: serverId.trim() || null,
        region,
        rank,
        main_role: mainRole,
        secondary_roles: secondaryRoles.filter((r) => r !== mainRole),
      },
    });
    go('create-prefs');
  };

  return (
    <StepShell
      step={2}
      total={6}
      title={opt.name}
      subtitle="Заполните игровые данные — они будут видны другим игрокам"
      onBack={() => go('create-game')}
      footer={
        <button onClick={handleNext} className="btn btn-primary" style={{ width: '100%', height: 54 }}>
          Продолжить
        </button>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <div className="input-label">Игровой ник</div>
          <input
            className="input"
            value={nick}
            onChange={(e) => setNick(e.target.value)}
            placeholder={opt.placeholders.nick}
          />
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <div className="input-label">Игровой ID</div>
            <input
              className="input"
              value={gameId}
              onChange={(e) => setGameId(e.target.value)}
              placeholder={opt.placeholders.gameId}
              inputMode="numeric"
              style={{ fontFamily: 'JetBrains Mono, monospace' }}
            />
          </div>
          {opt.showServerId && (
            <div style={{ width: 130 }}>
              <div className="input-label">Server ID</div>
              <input
                className="input"
                value={serverId}
                onChange={(e) => setServerId(e.target.value)}
                placeholder={opt.placeholders.serverId}
                inputMode="numeric"
                style={{ fontFamily: 'JetBrains Mono, monospace' }}
              />
            </div>
          )}
        </div>

        <div>
          <div className="input-label">Регион</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {opt.regions.map((r) => (
              <span
                key={r}
                onClick={() => setRegion(r)}
                className={cls('chip', region === r && 'chip-accent')}
                style={{ padding: '8px 14px', fontFamily: 'JetBrains Mono, monospace' }}
              >
                {r}
              </span>
            ))}
          </div>
        </div>

        <div>
          <div className="input-label">Ранг</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {opt.ranks.map((r) => (
              <span
                key={r}
                onClick={() => setRank(r)}
                className={cls('chip', rank === r && 'chip-accent')}
                style={{ padding: '8px 12px' }}
              >
                {r === rank && <Icon name="crown" size={11} stroke="#FFC43D" />} {r}
              </span>
            ))}
          </div>
        </div>

        <div>
          <div className="input-label">Основная роль</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {opt.roles.map((r) => (
              <span
                key={r}
                onClick={() => setMainRole(r)}
                className={cls('chip', mainRole === r && 'chip-accent')}
                style={{ padding: '8px 12px' }}
              >
                {r}
              </span>
            ))}
          </div>
        </div>

        <div>
          <div className="input-label">Дополнительные роли</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {opt.roles
              .filter((r) => r !== mainRole)
              .map((r) => (
                <span
                  key={r}
                  onClick={() => toggleSecondary(r)}
                  className={cls('chip', secondaryRoles.includes(r) && 'chip-accent')}
                  style={{ padding: '8px 12px' }}
                >
                  {r}
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
