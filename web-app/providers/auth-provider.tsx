import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';
import { useRef } from 'react';
import { useRouter } from 'next/router';
import { toast } from 'react-toastify';
import { postLogin, postRegister, getMe } from '@/utils/api/auth';
import { setEnsureUser, setOnAuthInvalid } from '@/utils/api/client';

type AuthProviderType = {
  user: AuthUserType;
  loading: boolean;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  registerWithEmail: (payload: {
    email: string;
    username: string;
    password: string;
    first_name: string;
    last_name: string;
    accept_terms: boolean;
  }) => Promise<void>;
  logOut: () => void;
};

export type AuthUserType = {
  id: number;
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
  is_superuser?: boolean;
} | null;

const AuthContext = createContext<AuthProviderType | undefined>(undefined);

export const AuthContextProvider = ({ children }: PropsWithChildren<{}>) => {
  const [user, setUser] = useState<AuthUserType>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const updateCurrentUser = (currentUser: AuthUserType) => {
    setUser(currentUser);
  };

  // Fetch current user from backend /me
  const hasFetchedMeRef = useRef(false);
  const fetchMe = async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('authToken') : null;
      if (!token) {
        updateCurrentUser(null);
        return;
      }
      const me = await getMe();
      updateCurrentUser(me);
    } catch (e) {
      // If /me fails, clear session
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      updateCurrentUser(null);
      if (!PUBLIC_ROUTES.includes(router.pathname)) {
        toast.warn('Session expired. Please sign in again.');
        router.replace('/users/login');
      }
    }
  };

  const signInWithEmail = async (email: string, password: string) => {
    try {
      const res: any = await postLogin({ email, password });
      const token = res?.access_token || res?.token || res?.data?.access_token;
      const refresh = res?.refresh_token || res?.data?.refresh_token;
      if (!token) throw new Error('Invalid login response');
      localStorage.setItem('authToken', token);
      if (refresh) localStorage.setItem('refreshToken', refresh);
      await fetchMe();
      router.push('/dashboard');
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Login failed';
      toast.error(msg);
      console.error('error at signInWithEmail ====> error', error);
    }
  };

  const registerWithEmail = async (payload: {
    email: string;
    username: string;
    password: string;
    first_name: string;
    last_name: string;
    accept_terms: boolean;
  }) => {
    try {
      await postRegister(payload);
      toast.success('Registration successful. Please log in.');
      router.push('/users/login?activeWizard=LOG_IN');
    } catch (error) {
      const msg = error instanceof Error ? error.message : (error as any)?.response?.data?.details || 'Registration failed';
      toast.error(msg);
      console.error('error at registerWithEmail ====> ', error);
    }
  };

  // Google sign-in removed for JWT-based auth.

  const logOut = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    updateCurrentUser(null);
    router.push('/users/login');
  };

  useEffect(() => {
    // Wire global axios hooks
    setOnAuthInvalid(() => {
      updateCurrentUser(null);
    });
    setEnsureUser(async () => {
      if (!hasFetchedMeRef.current) {
        hasFetchedMeRef.current = true;
        await fetchMe();
      }
    });

    // On mount, restore token and attempt to fetch /me (no forced redirect here; rely on route guards)
    const token = localStorage.getItem('authToken');
    if (token) {
      fetchMe().finally(() => {
        setLoading(false);
        checkPublicRoute();
      });
    } else {
      // No token: mark loading false and let checkPublicRoute decide based on PUBLIC_ROUTES
      setLoading(false);
      checkPublicRoute();
    }
    // Guard on route change
    const handleRouteChange = () => {
      checkPublicRoute();
    };
    router.events.on('routeChangeComplete', handleRouteChange);
    return () => {
      router.events.off('routeChangeComplete', handleRouteChange);
    };
  }, []);

  // Token refresh not implemented; rely on backend token lifetime.

  function scheduleTokenRefresh() {}

  const checkSessionExpired = () => {};

  const checkPublicRoute = () => {
    if (!PUBLIC_ROUTES.includes(router.pathname)) {
      if (!user && !loading) {
        router.replace('/users/login');
      }
    }
  };

  const contextValue = useMemo(
    () => ({
      user,
      loading,
      signInWithEmail,
      registerWithEmail,
      logOut,
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};

export const useUserAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useUserAuth must be used within AuthContextProvider');
  return ctx;
};

export const PUBLIC_ROUTES = ['/users/login', '/users/register'];
