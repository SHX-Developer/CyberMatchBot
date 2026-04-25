import { useEffect, useRef, useState } from 'react';
import { Icon } from '../components/Icon.jsx';
import {
  Avatar,
  BottomNav,
  CMBackground,
  StatusBar,
  TopBar,
} from '../components/ui.jsx';
import { useStore } from '../store.jsx';
import { getMyStats, updateMe } from '../api.js';
import { closeApp, haptic, shareLink, showAlert, tg } from '../telegram.js';

// Сжимаем изображение в квадрат 256×256 JPEG ≈ 50–80 КБ.
function fileToCompressedDataURL(file, size = 256, quality = 0.85) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        // обрезаем по центру в квадрат
        const min = Math.min(img.width, img.height);
        const sx = (img.width - min) / 2;
        const sy = (img.height - min) / 2;
        ctx.drawImage(img, sx, sy, min, min, 0, 0, size, size);
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      img.onerror = () => reject(new Error('Не удалось прочитать изображение'));
      img.src = reader.result;
    };
    reader.onerror = () => reject(new Error('Не удалось прочитать файл'));
    reader.readAsDataURL(file);
  });
}

const GENDER_LABEL = {
  male: 'М',
  female: 'Ж',
  hidden: 'не указан',
  not_specified: 'не указан',
};

const LANGUAGE_LABEL = {
  ru: 'Русский',
  uz: "O'zbekcha",
  en: 'English',
};

function plural(n, [one, few, many]) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}

function calcAge(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split('-').map(Number);
  if (!y) return null;
  const today = new Date();
  let age = today.getFullYear() - y;
  const md = today.getMonth() + 1 - m;
  if (md < 0 || (md === 0 && today.getDate() < d)) age -= 1;
  return age;
}

function StatCard({ label, value, accent, onClick }) {
  return (
    <button
      onClick={onClick}
      className="glass"
      style={{
        padding: '14px 14px',
        borderRadius: 18,
        flex: 1,
        textAlign: 'left',
        cursor: onClick ? 'pointer' : 'default',
        border: '1px solid rgba(255,255,255,0.10)',
        background: 'rgba(255,255,255,0.04)',
      }}
    >
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: 700,
          fontSize: 24,
          color: accent || '#fff',
          letterSpacing: -0.5,
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: 11,
          color: 'var(--t-2)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          fontWeight: 700,
          marginTop: 6,
        }}
      >
        {label}
      </div>
    </button>
  );
}

function MenuRow({ icon, label, sub, onClick, right, danger }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 10px',
        cursor: 'pointer',
        borderRadius: 14,
        width: '100%',
        background: 'transparent',
        border: 'none',
        textAlign: 'left',
        color: '#fff',
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: danger ? 'rgba(255,59,48,0.10)' : 'rgba(255,255,255,0.06)',
          border: `1px solid ${danger ? 'rgba(255,59,48,0.30)' : 'rgba(255,255,255,0.10)'}`,
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
          color: danger ? '#FF6961' : '#fff',
        }}
      >
        <Icon name={icon} size={16} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: danger ? '#FF6961' : '#fff' }}>
          {label}
        </div>
        {sub && (
          <div
            style={{
              fontSize: 12,
              color: 'var(--t-2)',
              marginTop: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {sub}
          </div>
        )}
      </div>
      {right ?? <Icon name="caret-right" size={16} stroke="var(--t-2)" />}
    </button>
  );
}

export function ProfileScreen({ go, onHome }) {
  const { state, dispatch } = useStore();
  const user = state.user;
  const tgUser = tg?.initDataUnsafe?.user;

  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [avatarError, setAvatarError] = useState(null);
  const fileInputRef = useRef(null);

  const onPickAvatar = () => {
    if (uploadingAvatar) return;
    haptic('light');
    fileInputRef.current?.click();
  };

  const onAvatarFile = async (file) => {
    if (!file) return;
    if (!/^image\//.test(file.type)) {
      setAvatarError('Поддерживаются только изображения');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setAvatarError('Файл больше 5 МБ');
      return;
    }
    setAvatarError(null);
    setUploadingAvatar(true);
    try {
      const dataUrl = await fileToCompressedDataURL(file, 256, 0.85);
      const updated = await updateMe({ avatar_data_url: dataUrl });
      dispatch({ type: 'UPDATE_USER', patch: { ...updated, is_registered: true } });
      haptic('success');
    } catch (e) {
      setAvatarError(e?.message || 'Не удалось загрузить аватар');
    } finally {
      setUploadingAvatar(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const onRemoveAvatar = async () => {
    if (uploadingAvatar) return;
    setAvatarError(null);
    setUploadingAvatar(true);
    haptic('warning');
    try {
      const updated = await updateMe({ avatar_data_url: '' });
      dispatch({ type: 'UPDATE_USER', patch: { ...updated, is_registered: true } });
    } catch (e) {
      setAvatarError(e?.message || 'Не удалось удалить аватар');
    } finally {
      setUploadingAvatar(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    setStatsLoading(true);
    getMyStats()
      .then((s) => {
        if (!cancelled) {
          setStats(s);
          setStatsLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setStatsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  // Статистика анкет берётся локально из стора как fallback.
  const profilesCount = stats?.profiles_count ?? state.profiles.length;
  const likesCount = stats?.likes_count ?? 0;
  const friendsCount = stats?.friends_count ?? 0;
  const followersCount = stats?.followers_count ?? 0;
  const subscriptionsCount = stats?.subscriptions_count ?? 0;

  const display = user?.nickname || user?.first_name || tgUser?.first_name || 'Cyber Mate';
  const handle = user?.nickname ? `@${user.nickname}` : tgUser?.username ? `@${tgUser.username}` : null;
  const age = calcAge(user?.birth_date);
  const langLabel = LANGUAGE_LABEL[user?.language] || 'Русский';
  const genderLabel = user?.gender ? GENDER_LABEL[user.gender] : null;

  const subtitleParts = [
    handle,
    genderLabel && genderLabel !== 'не указан' ? genderLabel : null,
    age != null ? `${age} ${plural(age, ['год', 'года', 'лет'])}` : null,
  ].filter(Boolean);

  const onShare = () => {
    haptic('light');
    if (!user?.nickname) {
      showAlert('Никнейм не задан');
      return;
    }
    const url = `https://t.me/cybermate_bot?start=u_${user.nickname}`;
    const text = `Найди меня в Cyber Mate — @${user.nickname}`;
    shareLink(url, text);
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
          title="Профиль"
          onHome={onHome}
          right={
            <button
              onClick={() => go('profile-security')}
              aria-label="Настройки"
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
              <Icon name="settings" size={16} />
            </button>
          }
        />

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
              <button
                onClick={onPickAvatar}
                disabled={uploadingAvatar}
                aria-label="Сменить аватар"
                style={{
                  position: 'relative',
                  background: 'transparent',
                  border: 'none',
                  padding: 0,
                  cursor: uploadingAvatar ? 'wait' : 'pointer',
                  borderRadius: '50%',
                  flexShrink: 0,
                }}
              >
                <Avatar
                  av="av-3"
                  size={80}
                  label={display[0]?.toUpperCase()}
                  ring
                  src={user?.avatar_data_url || undefined}
                />
                <span
                  style={{
                    position: 'absolute',
                    right: -2,
                    bottom: -2,
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: uploadingAvatar
                      ? 'rgba(255,255,255,0.16)'
                      : 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                    border: '2px solid #07000F',
                    display: 'grid',
                    placeItems: 'center',
                    color: '#fff',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
                  }}
                >
                  {uploadingAvatar ? (
                    <span
                      style={{
                        width: 14,
                        height: 14,
                        borderRadius: '50%',
                        border: '2px solid rgba(255,255,255,0.35)',
                        borderTopColor: '#fff',
                        animation: 'cm-spin 700ms linear infinite',
                      }}
                    />
                  ) : (
                    <Icon name="image" size={14} />
                  )}
                </span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={(e) => onAvatarFile(e.target.files?.[0])}
              />
              <style>{`@keyframes cm-spin{to{transform:rotate(360deg)}}`}</style>
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
                <span
                  className="chip chip-accent"
                  style={{ marginTop: 8, fontSize: 11, padding: '4px 10px' }}
                >
                  <Icon name="bolt" size={10} /> CYBER PRO
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button
                onClick={() => go('profile-edit')}
                className="btn btn-secondary"
                style={{ flex: 1, height: 44 }}
              >
                <Icon name="edit" size={14} /> Изменить
              </button>
              <button onClick={onShare} className="btn btn-secondary" style={{ flex: 1, height: 44 }}>
                <Icon name="send" size={14} /> Поделиться
              </button>
            </div>

            {avatarError && (
              <div
                style={{
                  marginTop: 10,
                  padding: '8px 12px',
                  borderRadius: 10,
                  background: 'rgba(255,59,48,0.12)',
                  border: '1px solid rgba(255,59,48,0.30)',
                  color: '#FF6961',
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                {avatarError}
              </div>
            )}

            {user?.avatar_data_url && !uploadingAvatar && (
              <button
                onClick={onRemoveAvatar}
                style={{
                  marginTop: 10,
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--t-2)',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: 0,
                  textDecoration: 'underline',
                }}
              >
                Убрать аватар
              </button>
            )}
          </div>
        </div>

        {/* Stats grid */}
        <div style={{ padding: '0 16px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          <StatCard
            label="Лайки"
            value={statsLoading ? '–' : likesCount}
            accent="var(--c-pink)"
            onClick={() => go('activity')}
          />
          <StatCard
            label="Друзья"
            value={statsLoading ? '–' : friendsCount}
            accent="var(--c-success)"
            onClick={() => go('activity')}
          />
          <StatCard
            label="Анкеты"
            value={profilesCount}
            accent="var(--accent)"
            onClick={() => go('profiles')}
          />
        </div>
        <div style={{ padding: '8px 16px 0', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <StatCard
            label="Подписчики"
            value={statsLoading ? '–' : followersCount}
            accent="var(--c-blue)"
            onClick={() => go('activity')}
          />
          <StatCard
            label="Подписки"
            value={statsLoading ? '–' : subscriptionsCount}
            accent="var(--accent)"
            onClick={() => go('activity')}
          />
        </div>

        {/* Меню */}
        <div style={{ padding: '20px 16px 0' }}>
          <div className="glass" style={{ borderRadius: 22, padding: 6 }}>
            <MenuRow
              icon="edit"
              label="Изменить данные"
              sub="Ник, гендер, дата рождения"
              onClick={() => go('profile-edit')}
            />
            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 10px' }} />
            <MenuRow
              icon="controller"
              label="Мои анкеты"
              sub={`${profilesCount} ${plural(profilesCount, ['анкета', 'анкеты', 'анкет'])}`}
              onClick={() => go('profiles')}
            />
            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 10px' }} />
            <MenuRow
              icon="bolt"
              label="Активность"
              sub="Лайки, матчи, подписки"
              onClick={() => go('activity')}
            />
            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 10px' }} />
            <MenuRow
              icon="shield"
              label="Безопасность"
              sub="Приватность, удаление аккаунта"
              onClick={() => go('profile-security')}
            />
            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 10px' }} />
            <MenuRow
              icon="globe"
              label="Язык"
              sub={langLabel}
              onClick={() => go('profile-language')}
            />
          </div>
        </div>

        {/* Telegram ID + версия */}
        <div
          style={{
            padding: '20px 16px 0',
            fontSize: 11,
            color: 'var(--t-3)',
            fontFamily: 'JetBrains Mono, monospace',
            textAlign: 'center',
            letterSpacing: '0.06em',
          }}
        >
          {user?.id ? `TG ID · ${user.id}` : ''}
        </div>

        <div style={{ padding: '14px 16px 130px' }}>
          <button
            onClick={() => {
              haptic('light');
              closeApp();
            }}
            className="btn btn-secondary"
            style={{ width: '100%' }}
          >
            <Icon name="x" size={16} /> Закрыть приложение
          </button>
        </div>
      </div>

      <BottomNav active="profile" onChange={go} />
    </div>
  );
}
