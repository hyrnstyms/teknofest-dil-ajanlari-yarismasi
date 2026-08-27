import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { CurrentUser } from "../types/case";
import { authApi } from "../services/authApi";
const KEY = "evrag:demo-auth:v1";
interface AuthValue { user: CurrentUser | null; token: string | null; loading: boolean; login: (key: string) => Promise<void>; logout: () => void }
const Context = createContext<AuthValue | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) { const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(KEY)); const [user, setUser] = useState<CurrentUser | null>(null); const [loading, setLoading] = useState(Boolean(token)); useEffect(() => { if (!token) { setLoading(false); return; } void authApi.me(token).then(setUser).catch(() => { sessionStorage.removeItem(KEY); setToken(null); }).finally(() => setLoading(false)); }, [token]); const value = useMemo<AuthValue>(() => ({ user, token, loading, login: async (key) => { const session = await authApi.login(key); sessionStorage.setItem(KEY, session.access_token); setToken(session.access_token); setUser(session.user); }, logout: () => { sessionStorage.removeItem(KEY); setToken(null); setUser(null); } }), [user, token, loading]); return <Context.Provider value={value}>{children}</Context.Provider>; }
export function useAuth() { const value = useContext(Context); if (!value) throw new Error("AuthProvider bulunamadı."); return value; }
