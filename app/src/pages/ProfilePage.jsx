import { useEffect, useState } from 'react';
import { webApi } from '../shared/api/client';

export function ProfilePage({ userId }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);

  const load = async () => {
    if (!userId) return;
    setLoading(true);
    setError('');
    try {
      const payload = await webApi.profile(userId);
      setData(payload);
    } catch (err) {
      setError(err.message || 'Не удалось загрузить профиль');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [userId]);

  if (!userId) return <p>Введите user_id сверху, чтобы открыть профиль.</p>;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Профиль</h2>
        <button onClick={load} disabled={loading}>Обновить</button>
      </div>
      {loading && <p>Загрузка...</p>}
      {error && <p className="error">{error}</p>}
      {data && (
        <div className="grid two">
          <div className="item"><span>Никнейм</span><b>{data.user?.full_name || 'Не указан'}</b></div>
          <div className="item"><span>Username</span><b>{data.user?.username ? `@${data.user.username}` : 'Не указан'}</b></div>
          <div className="item"><span>Анкеты</span><b>{data.profiles_count}</b></div>
          <div className="item"><span>Лайки</span><b>{data.likes_count}</b></div>
          <div className="item"><span>Подписчики</span><b>{data.followers_count}</b></div>
          <div className="item"><span>Подписки</span><b>{data.subscriptions_count}</b></div>
          <div className="item"><span>Друзья</span><b>{data.friends_count}</b></div>
        </div>
      )}
    </section>
  );
}
