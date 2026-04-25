import { GameBlock } from '../../components/ui.jsx';
import { StepShell } from '../../components/StepShell.jsx';
import { GAMES } from '../../data/mock.js';
import { GAME_KEY_FROM_CODE, GAME_OPTIONS } from './games.js';
import { useStore } from '../../store.jsx';
import { haptic } from '../../telegram.js';

export function CreateGameScreen({ go }) {
  const { state, dispatch } = useStore();
  const draftGame = state.createDraft?.game;

  const usedGames = new Set(
    state.profiles
      .filter((p) => p.status !== 'draft')
      .map((p) => GAME_KEY_FROM_CODE[p.game] || p.game),
  );

  const pick = (gameKey, opt) => {
    if (!opt.enabled) return;
    if (usedGames.has(gameKey)) return;
    haptic('select');
    dispatch({ type: 'SET_CREATE_DRAFT', payload: { game: gameKey } });
    setTimeout(() => go('create-data'), 100);
  };

  const continueDisabled = !draftGame || usedGames.has(draftGame);

  return (
    <StepShell
      step={1}
      total={6}
      title="Выберите игру"
      subtitle="По каждой игре можно создать одну активную анкету"
      onBack={() => go('profiles')}
      footer={
        <button
          onClick={() => !continueDisabled && go('create-data')}
          disabled={continueDisabled}
          className="btn btn-primary"
          style={{
            width: '100%',
            height: 54,
            opacity: continueDisabled ? 0.5 : 1,
            cursor: continueDisabled ? 'not-allowed' : 'pointer',
          }}
        >
          Продолжить
        </button>
      }
    >
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {Object.entries(GAME_OPTIONS).map(([key, opt]) => {
          const used = usedGames.has(key);
          const sel = draftGame === key;
          const blockKey = key in GAMES ? key : 'mlbb';
          const disabled = used || !opt.enabled;
          return (
            <button
              key={key}
              onClick={() => pick(key, opt)}
              disabled={disabled}
              style={{
                padding: 0,
                border: 'none',
                cursor: disabled ? 'not-allowed' : 'pointer',
                borderRadius: 18,
                outline: sel
                  ? '2px solid var(--accent)'
                  : '1px solid rgba(255,255,255,0.10)',
                outlineOffset: sel ? 1 : 0,
                boxShadow: sel ? '0 0 24px var(--accent-glow)' : 'none',
                transition: 'all 0.2s',
                position: 'relative',
                opacity: disabled ? 0.5 : 1,
              }}
            >
              <GameBlock
                game={blockKey}
                size="sm"
                style={{ borderRadius: 18, height: 110, border: 'none' }}
              />
              {used && (
                <span
                  style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    padding: '4px 8px',
                    borderRadius: 100,
                    background: 'rgba(0,0,0,0.55)',
                    fontSize: 10,
                    fontWeight: 800,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: '#fff',
                  }}
                >
                  Уже создана
                </span>
              )}
              {!opt.enabled && !used && (
                <span
                  style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    padding: '4px 8px',
                    borderRadius: 100,
                    background: 'rgba(0,0,0,0.55)',
                    fontSize: 10,
                    fontWeight: 800,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: '#fff',
                  }}
                >
                  Скоро
                </span>
              )}
            </button>
          );
        })}
      </div>

      {draftGame && usedGames.has(draftGame) && (
        <div
          style={{
            marginTop: 16,
            padding: '12px 14px',
            borderRadius: 14,
            background: 'rgba(255,59,48,0.12)',
            border: '1px solid rgba(255,59,48,0.30)',
            color: '#FF6961',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          Анкета для этой игры уже создана
        </div>
      )}
    </StepShell>
  );
}
