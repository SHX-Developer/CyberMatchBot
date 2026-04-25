import { useEffect, useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import {
  Avatar,
  CMBackground,
  GameBlock,
  SectionHeading,
  StatusBar,
  TopBar,
} from '../components/ui.jsx';
import { GAMES } from '../data/mock.js';
import { GAME_BACKEND_CODE, GAME_KEY_FROM_CODE } from './create/games.js';
import { getUserById, likeUser, startChat, toggleSubscription } from '../api.js';
import { haptic, showAlert } from '../telegram.js';

function avSeed(id) {
  const i = (Math.abs(Number(id) || 0) % 8) + 1;
  return `av-${i}`;
}

function plural(n, [one, few, many]) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

const GENDER_LABEL = {
  male: 'М',
  female: 'Ж',
  hidden: '',
  not_specified: '',
};

function ProfileCard({ profile }) {
  const wizardKey = GAME_KEY_FROM_CODE[profile.game] || profile.game;
  const blockKey = wizardKey in GAMES ? wizardKey : 'mlbb';

  return (
    <div
      className="glass"
      style={{
        borderRadius: 22,
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.10)',
      }}
    >
      <GameBlock game={blockKey} size="sm" />
      <div style={{ padding: '14px 16px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 800, fontSize: 16 }}>
            {profile.game_nickname || `id${profile.game_id || '?'}`}
          </span>
          {profile.rank && (
            <span className="chip" style={{ padding: '4px 8px', fontSize: 11 }}>
              <Icon name="crown" size={10} stroke="#FFC43D" /> {profile.rank}
            </span>
          )}
        </div>
        {profile.game_id && (
          <div
            style={{
              fontSize: 12,
              color: 'var(--t-2)',
              fontFamily: 'JetBrains Mono, monospace',
              marginTop: 4,
            }}
          >
            ID {profile.game_id}
            {profile.server_id ? ` · ${profile.server_id}` : ''}
            {profile.region ? ` · ${profile.region}` : ''}
          </div>
        )}
        {(profile.main_role || (profile.secondary_roles || []).length > 0) && (
          <div style={{ marginTop: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {profile.main_role && (
              <span className="chip chip-accent">{profile.main_role}</span>
            )}
            {(profile.secondary_roles || []).slice(0, 4).map((r) => (
              <span key={r} className="chip">
                {r}
              </span>
            ))}
          </div>
        )}
        {profile.about && (
          <div
            style={{
              marginTop: 10,
              fontSize: 13,
              color: '#E6E6F0',
              lineHeight: 1.45,
            }}
          >
            {profile.about}
          </div>
        )}
      </div>
    </div>
  );
}

export function UserProfileScreen({ go, onOpenChat, target }) {
  const targetId = target?.id ?? null;
  const fallback = target?.fallback || null;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!targetId) {
      setError('Не указан пользователь');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getUserById(targetId)
      .then((res) => {
        if (cancelled) return;
        setData(res);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || 'Не удалось загрузить профиль');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [targetId]);

  const user = data?.user || fallback || null;
  const profiles = data?.profiles || [];
  const isSelf = !!data?.is_self;

  const display =
    user?.nickname || user?.first_name || user?.full_name || `id${targetId || '?'}`;
  const handle = user?.nickname ? `@${user.nickname}` : null;
  const gender = user?.gender ? GENDER_LABEL[user.gender] : '';
  const age = user?.age;

  const subtitleParts = [
    handle,
    gender || null,
    age != null ? `${age} ${plural(age, ['год', 'года', 'лет'])}` : null,
  ].filter(Boolean);

  const onWrite = async () => {
    if (!targetId || busy || isSelf) return;
    setBusy(true);
    haptic('medium');
    try {
      const res = await startChat(targetId);
      onOpenChat?.({
        chat_id: res.chat_id,
        counterpart: res.counterpart || user,
      });
    } catch (e) {
      showAlert(e?.message || 'Не удалось начать чат');
    } finally {
      setBusy(false);
    }
  };

  const onLike = async () => {
    if (!targetId || busy || isSelf) return;
    setBusy(true);
    haptic('success');
    try {
      const game = profiles[0]?.game
        ? (GAME_BACKEND_CODE[profiles[0].game] || profiles[0].game)
        : 'mlbb';
      const res = await likeUser(targetId, game);
      setData((d) =>
        d
          ? { ...d, has_like: true, mutual: !!res?.mutual }
          : d,
      );
      if (res?.mutual) showAlert('Взаимный лайк! Теперь вы друзья');
    } catch (e) {
      showAlert(e?.message || 'Не удалось лайкнуть');
    } finally {
      setBusy(false);
    }
  };

  const onSubscribe = async () => {
    if (!targetId || busy || isSelf) return;
    setBusy(true);
    haptic('light');
    try {
      const res = await toggleSubscription(targetId);
      setData((d) => (d ? { ...d, is_subscribed: !!res?.subscribed } : d));
    } catch (e) {
      showAlert(e?.message || 'Не удалось');
    } finally {
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
        <TopBar title="Профиль" onBack={() => go('chats')} />

        {loading && (
          <div style={{ padding: 40, color: 'var(--t-2)', fontSize: 13, textAlign: 'center' }}>
            Загружаем…
          </div>
        )}
        {!loading && error && (
          <div
            style={{
              margin: '0 16px',
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

        {!loading && !error && (
          <>
            {/* Идентити-карточка */}
            <div style={{ padding: '0 16px 14px' }}>
              <div
                className="glass"
                style={{
                  padding: 20,
                  borderRadius: 26,
                  position: 'relative',
                  overflow: 'hidden',
                  background: 'linear-gradient(160deg, rgba(139,92,255,0.20), rgba(22,139,255,0.08))',
                  border: '1px solid rgba(255,255,255,0.10)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <Avatar
                    av={avSeed(targetId)}
                    size={80}
                    label={display[0]?.toUpperCase()}
                    ring
                    src={user?.avatar_data_url || undefined}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontWeight: 800,
                        fontSize: 22,
                        letterSpacing: -0.4,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {display}
                    </div>
                    {subtitleParts.length > 0 && (
                      <div
                        style={{
                          fontSize: 13,
                          color: 'var(--t-2)',
                          fontFamily: 'JetBrains Mono, monospace',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {subtitleParts.join(' · ')}
                      </div>
                    )}
                  </div>
                </div>

                {!isSelf && (
                  <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                    <button
                      onClick={onWrite}
                      disabled={busy}
                      className="btn btn-primary"
                      style={{ flex: 1, height: 44 }}
                    >
                      <Icon name="send" size={14} /> Написать
                    </button>
                    <button
                      onClick={onLike}
                      disabled={busy || !!data?.has_like}
                      className="btn btn-secondary"
                      style={{ width: 56, height: 44, padding: 0 }}
                      aria-label={data?.has_like ? 'Лайк уже поставлен' : 'Лайкнуть'}
                    >
                      <Icon
                        name={data?.has_like ? 'heart-fill' : 'heart'}
                        size={18}
                        stroke={data?.has_like ? 'var(--c-pink)' : '#fff'}
                      />
                    </button>
                    <button
                      onClick={onSubscribe}
                      disabled={busy}
                      className="btn btn-secondary"
                      style={{ width: 56, height: 44, padding: 0 }}
                      aria-label={
                        data?.is_subscribed ? 'Отписаться' : 'Подписаться'
                      }
                    >
                      <Icon
                        name={data?.is_subscribed ? 'check' : 'plus'}
                        size={16}
                      />
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Анкеты */}
            <div style={{ padding: '6px 16px 0' }}>
              <SectionHeading>
                {profiles.length === 0
                  ? 'Анкеты'
                  : `${profiles.length} ${plural(profiles.length, ['анкета', 'анкеты', 'анкет'])}`}
              </SectionHeading>
            </div>
            {profiles.length === 0 ? (
              <div
                style={{
                  margin: '0 16px',
                  padding: 20,
                  borderRadius: 18,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: 'var(--t-2)',
                  fontSize: 13,
                  textAlign: 'center',
                  lineHeight: 1.5,
                }}
              >
                У пользователя пока нет активных игровых анкет
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                  padding: '0 16px',
                }}
              >
                {profiles.map((p) => (
                  <ProfileCard key={p.id} profile={p} />
                ))}
              </div>
            )}

            <div style={{ height: 130 }} />
          </>
        )}
      </div>
    </div>
  );
}
