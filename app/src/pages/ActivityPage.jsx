import { useEffect, useState } from 'react';
import { webApi } from '../shared/api/client';

const sections = [
  { key: 'subscriptions', label: 'Мои подписки' },
  { key: 'subscribers', label: 'Мои подписчики' },
  { key: 'likes', label: 'Мои лайки' },
  { key: 'liked_by', label: 'Кто лайкнул меня' },
  { key: 'friends', label: 'Друзья' },
];

export function ActivityPage({ userId }) {
  const [section, setSection] = useState('subscriptions');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async (nextSection = section) => {
    if (!userId) return;
    setLoading(true);
    setError('');
    try {
      const payload = await webApi.activity(nextSection, userId, 100);
      setItems(Array.isArray(payload.items) ? payload.items : []);
    } catch (err) {
      setError(err.message || 'Ошибка загрузки активности');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(section);
  }, [userId, section]);

  if (!userId) return <p>Введите user_id сверху, чтобы открыть активность.</p>;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Активность</h2>
        <button onClick={() => load()} disabled={loading}>Обновить</button>
      </div>

      <div className="menu-row wrap">
        {sections.map((s) => (
          <button
            key={s.key}
            className={s.key === section ? 'active' : ''}
            onClick={() => setSection(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {loading && <p>Загрузка...</p>}
      {error && <p className="error">{error}</p>}

      <ul className="list">
        {items.map((item) => (
          <li key={`${section}-${item.user_id}`}>
            <b>{item.full_name || `user_${item.user_id}`}</b>
            <span>{item.username ? `@${item.username}` : `id: ${item.user_id}`}</span>
          </li>
        ))}
      </ul>
      {!loading && items.length === 0 && <p>Список пуст.</p>}
    </section>
  );
}
