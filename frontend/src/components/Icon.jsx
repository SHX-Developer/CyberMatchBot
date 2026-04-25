export function Icon({ name, size = 22, stroke = 'currentColor', fill = 'none', strokeWidth = 1.8 }) {
  const p = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill,
    stroke,
    strokeWidth,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
  };
  switch (name) {
    case 'search':
      return (
        <svg {...p}>
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      );
    case 'chat':
      return (
        <svg {...p}>
          <path d="M21 12a8 8 0 0 1-11.5 7.2L4 20l1-4.5A8 8 0 1 1 21 12Z" />
        </svg>
      );
    case 'controller':
      return (
        <svg {...p}>
          <path d="M5 8h14a3 3 0 0 1 3 3v3a4 4 0 0 1-4 4 3 3 0 0 1-2.4-1.2L14 15h-4l-1.6 1.8A3 3 0 0 1 6 18a4 4 0 0 1-4-4v-3a3 3 0 0 1 3-3Z" />
          <path d="M8 11v3M6.5 12.5h3M15 12.5h.01M17.5 11h.01" />
        </svg>
      );
    case 'star':
      return (
        <svg {...p}>
          <path d="m12 3 2.6 5.5 6 .9-4.3 4.3 1 6.1L12 17l-5.4 2.8 1-6.1L3.4 9.4l6-.9L12 3Z" />
        </svg>
      );
    case 'user':
      return (
        <svg {...p}>
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21a8 8 0 0 1 16 0" />
        </svg>
      );
    case 'heart':
      return (
        <svg {...p}>
          <path d="M12 21s-7.5-4.6-9.5-9.5C1 8 3.5 4 7.5 4c2 0 3.5 1 4.5 2.5C13 5 14.5 4 16.5 4c4 0 6.5 4 5 7.5C19.5 16.4 12 21 12 21Z" />
        </svg>
      );
    case 'heart-fill':
      return (
        <svg {...{ ...p, fill: 'currentColor', stroke: 'none' }}>
          <path d="M12 21s-7.5-4.6-9.5-9.5C1 8 3.5 4 7.5 4c2 0 3.5 1 4.5 2.5C13 5 14.5 4 16.5 4c4 0 6.5 4 5 7.5C19.5 16.4 12 21 12 21Z" />
        </svg>
      );
    case 'next':
      return (
        <svg {...p}>
          <path d="m7 5 8 7-8 7M17 5v14" />
        </svg>
      );
    case 'plus':
      return (
        <svg {...p}>
          <path d="M12 5v14M5 12h14" />
        </svg>
      );
    case 'edit':
      return (
        <svg {...p}>
          <path d="M14 4l6 6L8 22H2v-6L14 4Z" />
          <path d="M13 5l6 6" />
        </svg>
      );
    case 'trash':
      return (
        <svg {...p}>
          <path d="M4 7h16M9 7V4h6v3M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" />
        </svg>
      );
    case 'settings':
      return (
        <svg {...p}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
        </svg>
      );
    case 'bolt':
      return (
        <svg {...p}>
          <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" />
        </svg>
      );
    case 'shield':
      return (
        <svg {...p}>
          <path d="M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5l-8-3Z" />
        </svg>
      );
    case 'flame':
      return (
        <svg {...p}>
          <path d="M12 2c1 4 4 5 4 10a4 4 0 0 1-8 0c0-2 1-3 1-5 0-1-1-2-1-3 1 1 2 0 4-2Z" />
        </svg>
      );
    case 'check':
      return (
        <svg {...p}>
          <path d="m4 12 5 5L20 6" />
        </svg>
      );
    case 'x':
      return (
        <svg {...p}>
          <path d="M6 6l12 12M18 6 6 18" />
        </svg>
      );
    case 'pin':
      return (
        <svg {...p}>
          <path d="M12 22s7-7 7-12a7 7 0 1 0-14 0c0 5 7 12 7 12Z" />
          <circle cx="12" cy="10" r="2.5" />
        </svg>
      );
    case 'mic':
      return (
        <svg {...p}>
          <rect x="9" y="3" width="6" height="12" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
        </svg>
      );
    case 'send':
      return (
        <svg {...p}>
          <path d="m22 2-9 20-3-9-9-3 21-8Z" />
        </svg>
      );
    case 'caret-right':
      return (
        <svg {...p}>
          <path d="m9 6 6 6-6 6" />
        </svg>
      );
    case 'caret-down':
      return (
        <svg {...p}>
          <path d="m6 9 6 6 6-6" />
        </svg>
      );
    case 'image':
      return (
        <svg {...p}>
          <rect x="3" y="3" width="18" height="18" rx="3" />
          <circle cx="9" cy="9" r="2" />
          <path d="m3 17 5-5 5 5 3-3 5 5" />
        </svg>
      );
    case 'globe':
      return (
        <svg {...p}>
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
        </svg>
      );
    case 'crown':
      return (
        <svg {...p}>
          <path d="M3 7l4 5 5-7 5 7 4-5-2 12H5L3 7Z" />
        </svg>
      );
    case 'logo':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="cmlg" x1="0" y1="0" x2="24" y2="24">
              <stop offset="0" stopColor="#FF4FD8" />
              <stop offset="0.5" stopColor="#8B5CFF" />
              <stop offset="1" stopColor="#168BFF" />
            </linearGradient>
          </defs>
          <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Z" fill="url(#cmlg)" />
          <path d="M12 8.5 8 11v2l4 2.5 4-2.5v-2l-4-2.5Z" fill="rgba(255,255,255,0.95)" />
        </svg>
      );
    default:
      return (
        <svg {...p}>
          <circle cx="12" cy="12" r="9" />
        </svg>
      );
  }
}

export const cls = (...xs) => xs.filter(Boolean).join(' ');
