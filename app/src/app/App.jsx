import { useMemo, useState } from 'react';
import { ActivityPage } from '../pages/ActivityPage';
import { ChatsPage } from '../pages/ChatsPage';
import { ProfilePage } from '../pages/ProfilePage';
import { ProfilesPage } from '../pages/ProfilesPage';
import { SearchPage } from '../pages/SearchPage';
import { initTelegramWebApp } from '../shared/config/telegram';

const tabs = [
  { id: 'search', label: '🔍 Найти тиммейта' },
  { id: 'chats', label: '💬 Чаты' },
  { id: 'activity', label: '📊 Активность' },
  { id: 'profiles', label: '🎮 Мои анкеты' },
  { id: 'profile', label: '👤 Профиль' },
];

function asNumber(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return Math.trunc(parsed);
}

export function App() {
  const tgInfo = useMemo(() => initTelegramWebApp(), []);
  const [activeTab, setActiveTab] = useState('search');
  const [userIdInput, setUserIdInput] = useState(String(tgInfo.userId ?? ''));
  const [userId, setUserId] = useState(asNumber(tgInfo.userId));

  const applyUser = () => {
    setUserId(asNumber(userIdInput));
  };

  return (
    <main className="page">
      <section className="shell">
        <header className="topbar">
          <div>
            <p className="kicker">CyberMatch Web App</p>
            <h1>Локальный MVP</h1>
            <p className="muted">Platform: {tgInfo.platform} · User: {tgInfo.userLabel}</p>
          </div>

          <div className="user-form">
            <label htmlFor="uid">User ID</label>
            <div className="form-inline">
              <input
                id="uid"
                value={userIdInput}
                onChange={(e) => setUserIdInput(e.target.value)}
                placeholder="Введите user_id"
              />
              <button onClick={applyUser}>Подключить</button>
            </div>
            <small>{userId ? `Активный user_id: ${userId}` : 'User ID не выбран'}</small>
          </div>
        </header>

        <nav className="menu-row wrap">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={tab.id === activeTab ? 'active' : ''}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {activeTab === 'search' && <SearchPage userId={userId} />}
        {activeTab === 'chats' && <ChatsPage userId={userId} />}
        {activeTab === 'activity' && <ActivityPage userId={userId} />}
        {activeTab === 'profiles' && <ProfilesPage userId={userId} />}
        {activeTab === 'profile' && <ProfilePage userId={userId} />}
      </section>
    </main>
  );
}
