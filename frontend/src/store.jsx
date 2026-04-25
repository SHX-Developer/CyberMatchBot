import { createContext, useContext, useEffect, useReducer } from 'react';
import { getMe, listMyGameProfiles } from './api.js';

const STORAGE_KEY = 'cyber-mate-state-v2';

const initialState = {
  user: null,
  onboardingDraft: {},
  profiles: [],
  createDraft: null,
  status: 'loading', // 'loading' | 'ready' | 'error'
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_STATUS':
      return { ...state, status: action.status, error: action.error ?? null };
    case 'HYDRATE':
      return {
        ...state,
        user: action.user,
        profiles: action.profiles ?? [],
        status: 'ready',
        error: null,
      };
    case 'SET_ONBOARDING_DRAFT':
      return { ...state, onboardingDraft: { ...state.onboardingDraft, ...action.payload } };
    case 'COMPLETE_REGISTRATION':
      return {
        ...state,
        user: action.user,
        onboardingDraft: {},
      };
    case 'UPDATE_USER':
      return {
        ...state,
        user: state.user ? { ...state.user, ...action.patch } : action.patch,
      };
    case 'CLEAR_USER':
      return { ...state, user: null, profiles: [], onboardingDraft: {}, createDraft: null };
    case 'SET_CREATE_DRAFT':
      return {
        ...state,
        createDraft: { ...(state.createDraft || {}), ...action.payload },
      };
    case 'CLEAR_CREATE_DRAFT':
      return { ...state, createDraft: null };
    case 'SET_PROFILES':
      return { ...state, profiles: action.profiles };
    case 'ADD_PROFILE':
      return {
        ...state,
        profiles: [action.payload, ...state.profiles.filter((p) => p.id !== action.payload.id)],
        createDraft: null,
      };
    case 'UPDATE_PROFILE':
      return {
        ...state,
        profiles: state.profiles.map((p) =>
          p.id === action.id ? { ...p, ...action.patch } : p,
        ),
      };
    case 'DELETE_PROFILE':
      return { ...state, profiles: state.profiles.filter((p) => p.id !== action.id) };
    case 'RESET':
      return { ...initialState, status: 'ready' };
    default:
      return state;
  }
}

const StoreCtx = createContext(null);

function loadInitialState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      // status всегда 'loading' при старте — мы перепроверим у сервера.
      return { ...initialState, ...parsed, status: 'loading', error: null };
    }
  } catch (e) {
    // ignore
  }
  return initialState;
}

const PERSISTED_KEYS = ['onboardingDraft', 'createDraft'];

function persist(state) {
  try {
    const subset = {};
    for (const k of PERSISTED_KEYS) subset[k] = state[k];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(subset));
  } catch (e) {
    // ignore
  }
}

export function StoreProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, undefined, loadInitialState);

  // Гидрация из API при старте.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await getMe();
        if (cancelled) return;
        const user = me.is_registered ? { ...me.user, is_registered: true } : null;
        let profiles = [];
        if (me.is_registered) {
          try {
            const list = await listMyGameProfiles();
            profiles = list.items || [];
          } catch (e) {
            profiles = [];
          }
        }
        if (cancelled) return;
        dispatch({ type: 'HYDRATE', user, profiles });
      } catch (e) {
        if (cancelled) return;
        dispatch({ type: 'SET_STATUS', status: 'error', error: e.message || 'Unknown error' });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Лёгкая персистация черновиков.
  useEffect(() => {
    persist(state);
  }, [state.onboardingDraft, state.createDraft]);

  return <StoreCtx.Provider value={{ state, dispatch }}>{children}</StoreCtx.Provider>;
}

export function useStore() {
  const ctx = useContext(StoreCtx);
  if (!ctx) throw new Error('useStore must be used within StoreProvider');
  return ctx;
}

export function resumeOnboardingStep(draft) {
  if (!draft.language) return 'onb-language';
  if (!draft.birth_date) return 'onb-birth';
  if (!draft.gender) return 'onb-gender';
  if (!draft.nickname) return 'onb-nickname';
  return 'onb-done';
}
