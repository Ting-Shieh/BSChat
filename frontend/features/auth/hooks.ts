"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  acceptInvite,
  createInvite,
  createTeam,
  fetchAuthMode,
  fetchMe,
  forgotPassword,
  passwordLogin,
  registerAccount,
  resetPassword,
  updateSettings,
} from "./api";
import { useAuthStore } from "./store";

export interface SettingsPayload {
  auto_refresh_enabled?: boolean;
  auto_refresh_interval_days?: number;
  person_linkedin_auto_on_url?: boolean;
  search_precision?: "strict" | "balanced" | "exploratory";
}

export function useAuthMode() {
  return useQuery({
    queryKey: ["auth-mode"],
    queryFn: fetchAuthMode,
    staleTime: 60_000,
  });
}

export function useMe() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["me", token],
    queryFn: () => fetchMe(token!),
    enabled: !!token,
  });
}

function useTokenMutation<TArgs, TData>(
  mutationFn: (args: TArgs) => Promise<TData & { access_token?: string }>,
) {
  const setToken = useAuthStore((s) => s.setToken);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (data) => {
      if (data && typeof data === "object" && "access_token" in data && data.access_token) {
        setToken(data.access_token);
        queryClient.invalidateQueries({ queryKey: ["me"] });
      }
    },
  });
}

export function usePasswordLogin() {
  return useTokenMutation(passwordLogin);
}

export function useRegister() {
  return useTokenMutation(registerAccount);
}

export function useForgotPassword() {
  return useMutation({ mutationFn: (email: string) => forgotPassword(email) });
}

export function useResetPassword() {
  return useTokenMutation(resetPassword);
}

export function useCreateTeam() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; slug: string }) => createTeam(token!, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useCreateInvite() {
  const token = useAuthStore((s) => s.token);
  return useMutation({
    mutationFn: (body: { org_id: string; expires_days?: number; max_uses?: number }) =>
      createInvite(token!, body),
  });
}

export function useAcceptInvite() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inviteToken: string) => acceptInvite(token!, inviteToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useUpdateSettings() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SettingsPayload) => updateSettings(token!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useLogout() {
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();
  return async () => {
    logout();
    queryClient.clear();
  };
}
