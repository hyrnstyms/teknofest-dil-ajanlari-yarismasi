import type { AuthSession, CurrentUser } from "../types/case";
import { caseRequest } from "./caseHttp";
export const authApi = { login: (userKey: string) => caseRequest<AuthSession>("/api/auth/demo-login", undefined, { method: "POST", body: JSON.stringify({ user_key: userKey }) }), me: (token: string) => caseRequest<CurrentUser>("/api/auth/me", token) };
