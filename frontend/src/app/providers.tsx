"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { createQueryClient } from "@/services/apiClient";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { AuthProvider } from "@/components/auth/AuthContext";
import { SesionHeartbeat } from "@/components/layout/SesionHeartbeat";
import { ToastProvider } from "@/components/ui/Toast";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <AuthGuard>
            <SesionHeartbeat />
            {children}
          </AuthGuard>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
