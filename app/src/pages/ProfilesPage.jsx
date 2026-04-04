import { useEffect, useState } from 'react';
import { webApi } from '../shared/api/client';

const defaultForm = {
  game_player_id: '',
  rank: '',
  role: '',
  server: '',
  main_lane: 'all_lanes',
  extra_lanes: '',
  description: '',
  mythic_stars: '',
};

export function ProfilesPage({ userId }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    if (!userId) return;
    setLoading(true);
    setError('');
    try {
      const payload = await webApi.myProfiles(userId);
      setItems(Array.isArray(payload.items) ? payload.items : []);
    } catch (err) {
      setError(err.message || 'Не удалось загрузить анкеты');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [userId]);

  const onDelete = async (profileId) => {
    if (!window.confirm('Удалить анкету?')) return;
    try {
      await webApi.deleteProfile(userId, profileId);
      await load();
    } catch (err) {
      setError(err.message || 'Не удалось удалить анкету');
    }
  };

  const onReset = async (profileId) => {
    try {
      await webApi.resetProfile(userId, profileId);
      await load();
    } catch (err) {
      setError(err.message || 'Не удалось сбросить анкету');
    }
  };

  const onSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await webApi.saveMlbbProfile({
        user_id: userId,
        game_player_id: form.game_player_id,
        rank: form.rank || null,
        role: form.role || null,
        server: form.server || null,
        main_lane: form.main_lane,
        extra_lanes: form.extra_lanes
          .split(',')
          .map((v) => v.trim())
          .filter(Boolean),
        description: form.description,
        mythic_stars: form.mythic_stars ? Number(form.mythic_stars) : null,
      });
      setForm(defaultForm);
      await load();
    } catch (err) {
      setError(err.message || 'Не удалось сохранить анкету');
    } finally {
      setSaving(false);
    }
  };

  if (!userId) return <p>Введите user_id сверху, чтобы открыть «Мои анкеты».</p>;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Мои анкеты</h2>
        <button onClick={load} disabled={loading}>Обновить</button>
      </div>

      {error && <p className="error">{error}</p>}

      <form className="form" onSubmit={onSave}>
        <h3>Создать/обновить MLBB анкету</h3>
        <input placeholder="Game ID" value={form.game_player_id} onChange={(e) => setForm({ ...form, game_player_id: e.target.value })} required />
        <input placeholder="Ранг" value={form.rank} onChange={(e) => setForm({ ...form, rank: e.target.value })} />
        <input placeholder="Роль" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
        <input placeholder="Сервер" value={form.server} onChange={(e) => setForm({ ...form, server: e.target.value })} />
        <input placeholder="Main lane (all_lanes/gold_lane/...)" value={form.main_lane} onChange={(e) => setForm({ ...form, main_lane: e.target.value })} required />
        <input placeholder="Extra lanes через запятую" value={form.extra_lanes} onChange={(e) => setForm({ ...form, extra_lanes: e.target.value })} />
        <input placeholder="Mythic stars" type="number" value={form.mythic_stars} onChange={(e) => setForm({ ...form, mythic_stars: e.target.value })} />
        <textarea placeholder="Описание" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
        <button type="submit" disabled={saving}>{saving ? 'Сохраняю...' : 'Сохранить'}</button>
      </form>

      {loading && <p>Загрузка...</p>}
      <div className="cards">
        {items.map((profile) => (
          <article className="card-sm" key={profile.id}>
            <h3>{profile.game.toUpperCase()}</h3>
            <p>ID игры: {profile.game_player_id || '—'}</p>
            <p>Ранг: {profile.rank || '—'}</p>
            <p>Описание: {profile.description || '—'}</p>
            <div className="menu-row wrap">
              <button onClick={() => onReset(profile.id)}>Сбросить</button>
              <button className="danger" onClick={() => onDelete(profile.id)}>Удалить</button>
            </div>
          </article>
        ))}
      </div>
      {!loading && items.length === 0 && <p>Анкет пока нет.</p>}
    </section>
  );
}
