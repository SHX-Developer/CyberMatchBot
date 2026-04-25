// Конфиг игр для мастера создания анкеты.

// Маппинг ключей мастера → значение enum GameCode на бэке.
export const GAME_BACKEND_CODE = {
  mlbb: 'mlbb',
  genshin: 'genshin_impact',
  pubg: 'pubg_mobile',
  valorant: 'valorant',
  magic_chess: 'magic_chess',
  honkai: 'honkai_star_rail',
  zzz: 'zenless_zone_zero',
  csgo: 'cs_go',
};

// Обратный маппинг.
export const GAME_KEY_FROM_CODE = {
  mlbb: 'mlbb',
  genshin_impact: 'genshin',
  pubg_mobile: 'pubg',
  valorant: 'valorant',
  magic_chess: 'magic_chess',
  honkai_star_rail: 'honkai',
  zenless_zone_zero: 'zzz',
  cs_go: 'csgo',
};

const MLBB_RANKS = [
  'Warrior',
  'Elite',
  'Master',
  'Grandmaster',
  'Epic',
  'Legend',
  'Mythic',
  'Mythical Honor',
  'Mythical Glory',
  'Mythical Immortal',
];

const MLBB_ROLES = [
  'Линия золота',
  'Средняя линия',
  'Линия опыта',
  'Лесник',
  'Роумер',
  'На всех линиях',
];

const MAGIC_CHESS_RANKS = [
  'Grandmaster',
  'Epic',
  'Legend',
  'Mythic',
  'Mythical Honor',
  'Mythical Glory',
];

// Magic Chess — auto chess, ролей нет, но мастер требует main_role.
// Делаем стилевые варианты.
const MAGIC_CHESS_ROLES = [
  'Стратег',
  'Агрессор',
  'Защитник',
  'Универсал',
  'Любая синергия',
];

const HSR_RANKS = ['TL 30', 'TL 40', 'TL 50', 'TL 60', 'TL 70+', 'EQ 6'];
const HSR_ROLES = ['DPS', 'Sub-DPS', 'Healer', 'Support', 'Shield'];

const ZZZ_RANKS = ['IK 30', 'IK 40', 'IK 50', 'IK 55+'];
const ZZZ_ROLES = ['Attack', 'Anomaly', 'Stun', 'Defense', 'Support'];

const CSGO_RANKS = [
  'Silver',
  'Gold Nova',
  'Master Guardian',
  'DMG',
  'Legendary Eagle',
  'Supreme',
  'Global Elite',
];
const CSGO_ROLES = ['Entry', 'AWPer', 'Support', 'IGL', 'Lurker', 'Rifler'];

const REGIONS = ['UZ', 'RU', 'KZ', 'BY', 'UA', 'EU', 'NA', 'SEA'];
const GENSHIN_REGIONS = ['Europe', 'America', 'Asia', 'TW/HK/MO'];
const HOYO_REGIONS = ['Europe', 'America', 'Asia', 'TW/HK/MO'];

export const GAME_OPTIONS = {
  mlbb: {
    code: 'mlbb',
    name: 'Mobile Legends',
    enabled: true,
    placeholders: {
      nick: 'например, agrokid',
      gameId: '1296290718',
      serverId: '15720',
    },
    ranks: MLBB_RANKS,
    roles: MLBB_ROLES,
    regions: REGIONS,
    showServerId: true,
  },
  magic_chess: {
    code: 'magic_chess',
    name: 'Magic Chess',
    enabled: true,
    placeholders: {
      nick: 'ваш ник в Magic Chess',
      gameId: '1296290718',
      serverId: '15720',
    },
    ranks: MAGIC_CHESS_RANKS,
    roles: MAGIC_CHESS_ROLES,
    regions: REGIONS,
    showServerId: true,
  },
  pubg: {
    code: 'pubg_mobile',
    name: 'PUBG Mobile',
    enabled: true,
    placeholders: {
      nick: 'ваш игровой ник',
      gameId: '5012345678',
      serverId: '',
    },
    ranks: ['Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Crown', 'Ace', 'Conqueror'],
    roles: ['Assault', 'Sniper', 'Support', 'Scout'],
    regions: REGIONS,
    showServerId: false,
  },
  genshin: {
    code: 'genshin_impact',
    name: 'Genshin Impact',
    enabled: true,
    placeholders: {
      nick: 'ваш UID-ник',
      gameId: '700123456',
      serverId: '',
    },
    ranks: ['AR 30', 'AR 40', 'AR 50', 'AR 55', 'AR 56', 'AR 57', 'AR 58', 'AR 59', 'AR 60'],
    roles: ['DPS', 'Sub-DPS', 'Healer', 'Support'],
    regions: GENSHIN_REGIONS,
    showServerId: false,
  },
  honkai: {
    code: 'honkai_star_rail',
    name: 'Honkai Star Rail',
    enabled: true,
    placeholders: {
      nick: 'ваш игровой ник',
      gameId: '800123456',
      serverId: '',
    },
    ranks: HSR_RANKS,
    roles: HSR_ROLES,
    regions: HOYO_REGIONS,
    showServerId: false,
  },
  zzz: {
    code: 'zenless_zone_zero',
    name: 'Zenless Zone Zero',
    enabled: true,
    placeholders: {
      nick: 'ваш ник',
      gameId: '900123456',
      serverId: '',
    },
    ranks: ZZZ_RANKS,
    roles: ZZZ_ROLES,
    regions: HOYO_REGIONS,
    showServerId: false,
  },
  csgo: {
    code: 'cs_go',
    name: 'CS:GO',
    enabled: true,
    placeholders: {
      nick: 'Steam-ник',
      gameId: 'steamID',
      serverId: '',
    },
    ranks: CSGO_RANKS,
    roles: CSGO_ROLES,
    regions: REGIONS,
    showServerId: false,
  },
};

export const ABOUT_TEMPLATES = [
  'Ищу тиммейта для рейтинга',
  'Играю спокойно, без токсичности',
  'Нужна команда на вечер',
  'Могу играть с микрофоном',
];

export const LOOKING_FOR = [
  { code: 'ranked', label: 'Для рейтинга' },
  { code: 'classic', label: 'Для классики' },
  { code: 'tournament', label: 'Для турниров' },
  { code: 'casual', label: 'Просто поиграть' },
  { code: 'chat', label: 'Общение' },
];

export const PLAY_STYLES = [
  { code: 'calm', label: 'Спокойный' },
  { code: 'serious', label: 'Серьёзный' },
  { code: 'aggressive', label: 'Агрессивный' },
  { code: 'fun', label: 'Фан' },
  { code: 'any', label: 'Не важно' },
];

export const MICROPHONE = [
  { code: 'yes', label: 'Есть' },
  { code: 'no', label: 'Нет' },
  { code: 'any', label: 'Не важно' },
];

export const PLAY_TIME = [
  { code: 'morning', label: 'Утром' },
  { code: 'afternoon', label: 'Днём' },
  { code: 'evening', label: 'Вечером' },
  { code: 'night', label: 'Ночью' },
  { code: 'mixed', label: 'По-разному' },
];
