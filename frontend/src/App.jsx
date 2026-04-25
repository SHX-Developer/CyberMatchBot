import { useEffect, useState } from 'react';
import { HomeScreen } from './screens/HomeScreen.jsx';
import { SearchScreen } from './screens/SearchScreen.jsx';
import { PlayerDetailScreen } from './screens/PlayerDetailScreen.jsx';
import { MyProfilesScreen } from './screens/MyProfilesScreen.jsx';
import { ChatsScreen } from './screens/ChatsScreen.jsx';
import { ChatScreen } from './screens/ChatScreen.jsx';
import { ActivityScreen } from './screens/ActivityScreen.jsx';
import { ProfileScreen } from './screens/ProfileScreen.jsx';
import { LanguageScreen } from './screens/onboarding/LanguageScreen.jsx';
import { BirthDateScreen } from './screens/onboarding/BirthDateScreen.jsx';
import { GenderScreen } from './screens/onboarding/GenderScreen.jsx';
import { NicknameScreen } from './screens/onboarding/NicknameScreen.jsx';
import { RegisteredScreen } from './screens/onboarding/RegisteredScreen.jsx';
import { CreateGameScreen } from './screens/create/CreateGameScreen.jsx';
import { CreateGameDataScreen } from './screens/create/CreateGameDataScreen.jsx';
import { CreatePreferencesScreen } from './screens/create/CreatePreferencesScreen.jsx';
import { CreateAboutScreen } from './screens/create/CreateAboutScreen.jsx';
import { CreateScreenshotScreen } from './screens/create/CreateScreenshotScreen.jsx';
import { CreatePreviewScreen } from './screens/create/CreatePreviewScreen.jsx';
import { ProfileEditScreen } from './screens/profile/ProfileEditScreen.jsx';
import { LanguageSettingsScreen } from './screens/profile/LanguageSettingsScreen.jsx';
import { SecurityScreen } from './screens/profile/SecurityScreen.jsx';
import { MyProfileCardScreen } from './screens/profile/MyProfileCardScreen.jsx';
import { ActivityListScreen } from './screens/activity/ActivityListScreen.jsx';
import { initTelegram, setBackButton } from './telegram.js';
import { resumeOnboardingStep, useStore } from './store.jsx';

const TAB_SCREENS = ['search', 'chats', 'profiles', 'activity', 'profile'];

const BACK_TARGETS = {
  detail: 'search',
  chat: 'chats',
  // create flow
  'create-game': 'profiles',
  'create-data': 'create-game',
  'create-prefs': 'create-data',
  'create-about': 'create-prefs',
  'create-shot': 'create-about',
  'create-preview': 'create-shot',
  // profile flow
  'profile-edit': 'profile',
  'profile-language': 'profile',
  'profile-security': 'profile',
  'my-card': 'profiles',
  // activity
  'activity-list': 'activity',
  // onboarding
  'onb-birth': 'onb-language',
  'onb-gender': 'onb-birth',
  'onb-nickname': 'onb-gender',
};

const ONBOARDING_SCREENS = new Set([
  'onb-language',
  'onb-birth',
  'onb-gender',
  'onb-nickname',
  'onb-done',
]);

function pickInitialScreen(state) {
  if (!state.user?.is_registered) {
    return resumeOnboardingStep(state.onboardingDraft);
  }
  return 'home';
}

function LoadingScreen({ message = 'Загрузка…' }) {
  return (
    <div
      style={{
        height: '100%',
        display: 'grid',
        placeItems: 'center',
        background: '#07000F',
        color: 'var(--t-2)',
        fontSize: 14,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
        <span
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            border: '3px solid rgba(255,255,255,0.12)',
            borderTopColor: 'var(--accent)',
            animation: 'cm-spin 700ms linear infinite',
          }}
        />
        <span>{message}</span>
        <style>{`@keyframes cm-spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    </div>
  );
}

function ErrorScreen({ message }) {
  return (
    <div
      style={{
        height: '100%',
        display: 'grid',
        placeItems: 'center',
        background: '#07000F',
        color: '#FF6961',
        padding: 24,
        textAlign: 'center',
      }}
    >
      <div>
        <div style={{ fontWeight: 800, fontSize: 18, marginBottom: 8, color: '#fff' }}>
          Сервер недоступен
        </div>
        <div style={{ fontSize: 13, color: 'var(--t-2)', maxWidth: 320 }}>
          {message || 'Не удалось связаться с API. Попробуйте позже.'}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const { state } = useStore();
  const [screen, setScreen] = useState(null);
  const [activePlayer, setActivePlayer] = useState(null);
  const [activeMyProfile, setActiveMyProfile] = useState(null);
  const [activeChat, setActiveChat] = useState(null);
  const [activeActivitySection, setActiveActivitySection] = useState('liked_by');

  useEffect(() => {
    initTelegram();
  }, []);

  // После завершения гидратации выставляем initial screen.
  useEffect(() => {
    if (state.status === 'ready' && screen === null) {
      setScreen(pickInitialScreen(state));
    }
  }, [state.status, state.user, state.onboardingDraft, screen]);

  // Гейт: если пользователь не зарегистрирован — нельзя выйти за пределы онбординга.
  // Если зарегистрирован — нельзя застрять на онбординге.
  useEffect(() => {
    if (state.status !== 'ready' || !screen) return;
    if (!state.user?.is_registered) {
      if (!ONBOARDING_SCREENS.has(screen)) {
        setScreen(resumeOnboardingStep(state.onboardingDraft));
      }
    } else if (ONBOARDING_SCREENS.has(screen) && screen !== 'onb-done') {
      setScreen('home');
    }
  }, [state.status, state.user, state.onboardingDraft, screen]);

  const go = (target, payload) => {
    if (target === 'detail' && payload) setActivePlayer(payload);
    if (target === 'my-card' && payload) setActiveMyProfile(payload);
    if (target === 'chat' && payload) setActiveChat(payload);
    if (target === 'activity-list' && payload) setActiveActivitySection(payload);
    setScreen(target);
  };

  const openChat = (chatPayload) => {
    setActiveChat(chatPayload);
    setScreen('chat');
  };

  useEffect(() => {
    const back = BACK_TARGETS[screen];
    if (!back) return setBackButton(false);
    return setBackButton(true, () => setScreen(back));
  }, [screen]);

  const renderScreen = () => {
    switch (screen) {
      case 'onb-language':
        return <LanguageScreen go={go} />;
      case 'onb-birth':
        return <BirthDateScreen go={go} />;
      case 'onb-gender':
        return <GenderScreen go={go} />;
      case 'onb-nickname':
        return <NicknameScreen go={go} />;
      case 'onb-done':
        return <RegisteredScreen go={go} />;

      case 'create-game':
        return <CreateGameScreen go={go} />;
      case 'create-data':
        return <CreateGameDataScreen go={go} />;
      case 'create-prefs':
        return <CreatePreferencesScreen go={go} />;
      case 'create-about':
        return <CreateAboutScreen go={go} />;
      case 'create-shot':
        return <CreateScreenshotScreen go={go} />;
      case 'create-preview':
        return <CreatePreviewScreen go={go} />;

      case 'home':
        return <HomeScreen go={go} />;
      case 'search':
        return (
          <SearchScreen
            go={go}
            onOpenChat={openChat}
            onHome={() => setScreen('home')}
          />
        );
      case 'detail':
        return <PlayerDetailScreen go={go} player={activePlayer} />;
      case 'profiles':
        return <MyProfilesScreen go={go} onHome={() => setScreen('home')} />;
      case 'chats':
        return <ChatsScreen go={go} onOpenChat={openChat} onHome={() => setScreen('home')} />;
      case 'chat':
        return <ChatScreen go={go} activeChat={activeChat} />;
      case 'activity':
        return (
          <ActivityScreen
            go={go}
            onOpenList={(section) => {
              setActiveActivitySection(section);
              setScreen('activity-list');
            }}
            onOpenChat={openChat}
            onHome={() => setScreen('home')}
          />
        );
      case 'activity-list':
        return (
          <ActivityListScreen
            go={go}
            section={activeActivitySection}
            onOpenChat={openChat}
          />
        );
      case 'profile':
        return <ProfileScreen go={go} onHome={() => setScreen('home')} />;
      case 'profile-edit':
        return <ProfileEditScreen go={go} />;
      case 'profile-language':
        return <LanguageSettingsScreen go={go} />;
      case 'profile-security':
        return <SecurityScreen go={go} />;
      case 'my-card': {
        const fresh = activeMyProfile
          ? state.profiles.find((p) => p.id === activeMyProfile.id) || activeMyProfile
          : null;
        return <MyProfileCardScreen go={go} profile={fresh} />;
      }
      default:
        return <HomeScreen go={go} />;
    }
  };

  if (state.status === 'loading') {
    return (
      <div className="app-shell">
        <LoadingScreen />
      </div>
    );
  }
  if (state.status === 'error') {
    return (
      <div className="app-shell">
        <ErrorScreen message={state.error} />
      </div>
    );
  }
  if (!screen) {
    return (
      <div className="app-shell">
        <LoadingScreen />
      </div>
    );
  }

  return <div className="app-shell">{renderScreen()}</div>;
}
