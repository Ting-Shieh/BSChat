"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { devLogin, fetchMe, switchPlan } from "./api";
import type { PlanTier } from "@/shared/types/auth";
import { useAuthStore } from "./store";

export function useMe() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["me", token],
    queryFn: () => fetchMe(token!),
    enabled: !!token,
  });
}

export function useDevLogin() {
  const setToken = useAuthStore((s) => s.setToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: devLogin,
    onSuccess: (data) => {
      setToken(data.access_token);
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useSwitchPlan() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tier: PlanTier) => switchPlan(token!, tier),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      queryClient.invalidateQueries({ queryKey: ["contact"] });
    },
  });
}

export function useLogout() {
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();
  return () => {
    logout();
    queryClient.clear();
  };
}
