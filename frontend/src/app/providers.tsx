"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { createQueryClient } from "@/services/apiClient";
import { SesionHeartbeat } from "@/components/layout/SesionHeartbeat";
import { ToastProvider } from "@/components/ui/Toast";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <SesionHeartbeat />
        {children}
      </ToastProvider>
    </QueryClientProvider>
  );
}
