"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext } from "react";

import { fetchMe, logout as logoutRequest, type Usuario } from "@/services/authApi";

interface AuthContextValue {
  usuario: Usuario | null | undefined;
  isLoading: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const { data: usuario, isLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchMe,
    staleTime: 60_000,
    retry: false,
  });

  async function logout() {
    await logoutRequest();
    queryClient.setQueryData(["auth", "me"], null);
  }

  return (
    <AuthContext.Provider value={{ usuario, isLoading, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
