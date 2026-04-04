import { useMemo } from 'react';
import { initTelegramWebApp } from '../shared/config/telegram';

export function App() {
  const tgInfo = useMemo(() => initTelegramWebApp(), []);

  return (
    <main className="page">
      <section className="card">
        <p className="kicker">CyberMatch</p>
        <h1>Telegram Web App</h1>
        <p className="muted">Базовая React-структура готова. Следующий шаг: подключаем экраны чатов, анкет и активности.</p>
        <ul className="meta">
          <li><b>Platform:</b> {tgInfo.platform}</li>
          <li><b>User:</b> {tgInfo.userLabel}</li>
          <li><b>Theme:</b> {tgInfo.colorScheme}</li>
        </ul>
      </section>
    </main>
  );
}
