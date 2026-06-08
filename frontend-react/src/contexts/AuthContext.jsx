import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { tokenStore } from "../api/client.js";
import { authApi } from "../api/auth.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(true);

  useEffect(() => {
    const token = tokenStore.get();
    if (!token) {
      setBootstrapping(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        tokenStore.clear();
        setUser(null);
      })
      .finally(() => setBootstrapping(false));
  }, []);

  const signin = useCallback(async (email, password) => {
    const data = await authApi.signin(email, password);
    tokenStore.set(data.access_token);
    setUser({ user_id: data.user_id, email: data.email });
    return data;
  }, []);

  const signup = useCallback(async (email, password) => {
    const data = await authApi.signup(email, password);
    tokenStore.set(data.access_token);
    setUser({ user_id: data.user_id, email: data.email });
    return data;
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, bootstrapping, signin, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
};
