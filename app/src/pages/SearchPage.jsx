import { useEffect, useState } from 'react';
import { webApi } from '../shared/api/client';

export function SearchPage({ userId }) {
  const [game, setGame] = useState('mlbb');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    if (!userId) return;
    setLoading(true);
    setError('');
    try {
      const payload = await webApi.searchProfiles(userId, game);
      setItems(Array.isArray(payload.items) ? payload.items : []);
    } catch (err) {
      setError(err.message || 'Ошибка поиска');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setItems([]);
  }, [userId]);

  const onLike = async (targetUserId) => {
    try {
      await webApi.like(userId, targetUserId, game);
      await load();
    } catch (err) {
      setError(err.message || 'Не удалось поставить лайк');
    }
  };

  const onToggleSubscription = async (targetUserId) => {
    try {
      await webApi.toggleSubscription(userId, targetUserId);
      await load();
    } catch (err) {
      setError(err.message || 'Не удалось обновить подписку');
    }
  };

  const onMessage = async (targetUserId) => {
    const text = window.prompt('Введите сообщение');
    if (!text || !text.trim()) return;
    try {
      await webApi.sendDirectMessage(userId, targetUserId, text.trim());
      window.alert('Сообщение отправлено');
    } catch (err) {
      setError(err.message || 'Не удалось отправить сообщение');
    }
  };

  if (!userId) return <p>Введите user_id сверху, чтобы искать тиммейтов.</p>;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Найти тиммейта</h2>
        <button onClick={load} disabled={loading}>Искать</button>
      </div>

      <div className="menu-row">
        <button className={game === 'mlbb' ? 'active' : ''} onClick={() => setGame('mlbb')}>MLBB</button>
      </div>

      {loading && <p>Поиск...</p>}
      {error && <p className="error">{error}</p>}

      <div className="cards">
        {items.map((item) => {
          const owner = item.owner || {};
          const profile = item.profile || {};
          return (
            <article className="card-sm" key={profile.id}>
              <h3>{owner.full_name || owner.username || `user_${owner.id}`}</h3>
              <p>ID игры: {profile.game_player_id || '—'}</p>
              <p>Ранг: {profile.rank || '—'}</p>
              <p>О себе: {profile.description || '—'}</p>
              <div className="menu-row wrap">
                <button onClick={() => onLike(owner.id)}>{item.liked ? 'Лайк ✅' : 'Лайк'}</button>
                <button onClick={() => onToggleSubscription(owner.id)}>
                  {item.subscribed ? 'Отписаться' : 'Подписаться'}
                </button>
                <button onClick={() => onMessage(owner.id)}>Написать</button>
              </div>
            </article>
          );
        })}
      </div>
      {!loading && items.length === 0 && <p>Анкеты не найдены.</p>}
    </section>
  );
}
