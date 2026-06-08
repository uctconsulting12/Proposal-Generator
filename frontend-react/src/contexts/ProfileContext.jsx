import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { profileApi } from "../api/profile.js";
import { useAuth } from "./AuthContext.jsx";

const ProfileContext = createContext(null);

const EMPTY_PROFILE = {
  company_name: "",
  company_intro: "",
  intro_verbatim: false,
  signature: "",
  accent_color: "#0f766e",
  template_id: "modern",
  has_logo: false,
  logo_mime: "",
  logo_updated_at: "",
  updated_at: "",
};

export function ProfileProvider({ children }) {
  const { user } = useAuth();
  const [profile, setProfile] = useState(EMPTY_PROFILE);
  const [loading, setLoading] = useState(false);
  const [logoUrl, setLogoUrl] = useState("");
  const logoUrlRef = useRef("");

  const revokeLogo = useCallback(() => {
    if (logoUrlRef.current) {
      URL.revokeObjectURL(logoUrlRef.current);
      logoUrlRef.current = "";
    }
    setLogoUrl("");
  }, []);

  const refreshLogo = useCallback(async (profileSnapshot) => {
    revokeLogo();
    if (!profileSnapshot?.has_logo) return;
    try {
      const url = await profileApi.fetchLogoObjectUrl();
      if (url) {
        logoUrlRef.current = url;
        setLogoUrl(url);
      }
    } catch {
      /* non-fatal */
    }
  }, [revokeLogo]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await profileApi.get();
      setProfile({ ...EMPTY_PROFILE, ...data });
      await refreshLogo(data);
      return data;
    } finally {
      setLoading(false);
    }
  }, [refreshLogo]);

  const save = useCallback(async (patch) => {
    const data = await profileApi.update(patch);
    setProfile({ ...EMPTY_PROFILE, ...data });
    return data;
  }, []);

  const uploadLogo = useCallback(async (file) => {
    const data = await profileApi.uploadLogo(file);
    setProfile({ ...EMPTY_PROFILE, ...data });
    await refreshLogo(data);
    return data;
  }, [refreshLogo]);

  const removeLogo = useCallback(async () => {
    const data = await profileApi.deleteLogo();
    setProfile({ ...EMPTY_PROFILE, ...data });
    revokeLogo();
    return data;
  }, [revokeLogo]);

  useEffect(() => {
    if (!user) {
      revokeLogo();
      setProfile(EMPTY_PROFILE);
      return;
    }
    refresh().catch(() => {
      /* surfaced where needed */
    });
  }, [user, refresh, revokeLogo]);

  // Final teardown to avoid leaking the blob URL when the app unmounts.
  useEffect(() => () => revokeLogo(), [revokeLogo]);

  const value = useMemo(
    () => ({
      profile,
      logoUrl,
      loading,
      refresh,
      save,
      uploadLogo,
      removeLogo,
    }),
    [profile, logoUrl, loading, refresh, save, uploadLogo, removeLogo]
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export const useProfile = () => {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error("useProfile must be inside ProfileProvider");
  return ctx;
};
