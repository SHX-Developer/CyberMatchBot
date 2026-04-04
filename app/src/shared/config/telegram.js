export function initTelegramWebApp() {
  const tg = window.Telegram?.WebApp;

  if (tg) {
    tg.ready();
    tg.expand();
  }

  const user = tg?.initDataUnsafe?.user;

  return {
    platform: tg?.platform ?? 'browser',
    colorScheme: tg?.colorScheme ?? 'unknown',
    userLabel: user?.username ? `@${user.username}` : user?.first_name ?? 'Guest',
  };
}
