export const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : null;

// Версии Bot API, в которых появились методы WebApp.
// Если клиент старее — нельзя вызывать, иначе словим WebAppMethodUnsupported.
function supports(minVersion) {
  if (!tg) return false;
  if (typeof tg.isVersionAtLeast === 'function') {
    try {
      return tg.isVersionAtLeast(minVersion);
    } catch (e) {
      return false;
    }
  }
  // Старые клиенты без isVersionAtLeast — считаем что НЕ поддерживают новые фичи.
  return false;
}

function safe(fn) {
  try {
    return fn();
  } catch (e) {
    if (typeof console !== 'undefined') console.warn('TG call failed:', e?.message || e);
    return undefined;
  }
}

function applyViewportHeight() {
  if (!tg) return;
  const h = tg.viewportStableHeight || tg.viewportHeight;
  if (!h) return;
  document.documentElement.style.setProperty('--tg-viewport-h', `${h}px`);
}

export function initTelegram() {
  if (!tg) return null;
  safe(() => tg.ready());
  safe(() => tg.expand());

  // disableVerticalSwipes доступен с 7.7
  if (supports('7.7') && typeof tg.disableVerticalSwipes === 'function') {
    safe(() => tg.disableVerticalSwipes());
  }

  // hex-цвета в setHeaderColor поддерживаются с 6.9, до этого только 'bg_color' / 'secondary_bg_color'
  if (supports('6.9') && typeof tg.setHeaderColor === 'function') {
    safe(() => tg.setHeaderColor('#07000F'));
  } else if (supports('6.1') && typeof tg.setHeaderColor === 'function') {
    safe(() => tg.setHeaderColor('bg_color'));
  }

  if (supports('6.1') && typeof tg.setBackgroundColor === 'function') {
    safe(() => tg.setBackgroundColor('#07000F'));
  }

  // Динамическая высота viewport — обновляется при открытии клавиатуры в TG.
  applyViewportHeight();
  if (typeof tg.onEvent === 'function') {
    safe(() => tg.onEvent('viewportChanged', applyViewportHeight));
  }

  installGlobalHaptics();

  return tg;
}

// Глобальный haptic на любые тапы по интерактивным элементам.
// Так каждая кнопка / ссылка / .chip / .input триггерит лёгкую вибрацию,
// без необходимости дописывать onPointerDown в каждом компоненте.
let HAPTICS_INSTALLED = false;
function installGlobalHaptics() {
  if (HAPTICS_INSTALLED || typeof document === 'undefined') return;
  HAPTICS_INSTALLED = true;
  const isInteractive = (el) => {
    if (!el || el.nodeType !== 1) return false;
    if (el.disabled) return false;
    const tag = el.tagName;
    if (tag === 'BUTTON' || tag === 'A' || tag === 'SUMMARY' || tag === 'LABEL') return true;
    if (tag === 'INPUT') {
      const type = (el.type || '').toLowerCase();
      return ['button', 'submit', 'reset', 'checkbox', 'radio', 'file'].includes(type);
    }
    if (tag === 'SELECT') return true;
    if (el.getAttribute && el.getAttribute('role')) {
      const role = el.getAttribute('role').toLowerCase();
      if (['button', 'tab', 'switch', 'checkbox', 'menuitem', 'option'].includes(role)) return true;
    }
    if (el.classList && (el.classList.contains('chip') || el.classList.contains('btn'))) return true;
    return false;
  };
  document.addEventListener(
    'pointerdown',
    (e) => {
      // Только основная кнопка / тач — не контекстное меню.
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      let node = e.target;
      let depth = 0;
      while (node && depth < 5) {
        if (isInteractive(node)) {
          haptic('light');
          return;
        }
        node = node.parentElement;
        depth += 1;
      }
    },
    { capture: true, passive: true },
  );
}

export function haptic(type = 'light') {
  if (!tg?.HapticFeedback) return;
  if (!supports('6.1')) return;
  safe(() => {
    if (['light', 'medium', 'heavy', 'rigid', 'soft'].includes(type)) {
      tg.HapticFeedback.impactOccurred(type);
    } else if (['error', 'success', 'warning'].includes(type)) {
      tg.HapticFeedback.notificationOccurred(type);
    } else if (type === 'select') {
      tg.HapticFeedback.selectionChanged();
    }
  });
}

// Универсальный alert: на старых клиентах фоллбэк на window.alert.
export function showAlert(message) {
  if (supports('6.2') && typeof tg?.showAlert === 'function') {
    return safe(() => tg.showAlert(message));
  }
  if (typeof window !== 'undefined') window.alert(message);
}

export function showPopup(options) {
  return new Promise((resolve) => {
    if (supports('6.2') && typeof tg?.showPopup === 'function') {
      try {
        tg.showPopup(options, (id) => resolve(id || 'cancel'));
        return;
      } catch (e) {
        // fallthrough
      }
    }
    const ok = typeof window !== 'undefined' ? window.confirm(options.message || '') : false;
    resolve(ok ? (options.buttons?.find((b) => b.type !== 'cancel')?.id || 'ok') : 'cancel');
  });
}

export function shareLink(url, text) {
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text || '')}`;
  if (supports('6.1') && typeof tg?.openTelegramLink === 'function') {
    safe(() => tg.openTelegramLink(shareUrl));
    return;
  }
  if (typeof window !== 'undefined') window.open(shareUrl, '_blank');
}

export function setBackButton(show, onClick) {
  if (!tg?.BackButton || !supports('6.1')) return () => {};
  if (show) {
    safe(() => tg.BackButton.show());
    safe(() => tg.BackButton.onClick(onClick));
    return () => {
      safe(() => tg.BackButton.offClick(onClick));
      safe(() => tg.BackButton.hide());
    };
  } else {
    safe(() => tg.BackButton.hide());
  }
  return () => {};
}

export function closeApp() {
  safe(() => tg?.close?.());
}
