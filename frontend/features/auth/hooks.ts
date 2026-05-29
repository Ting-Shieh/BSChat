"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { devLogin, fetchMe } from "./api";
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

export function useLogout() {
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();
  return () => {
    logout();
    queryClient.clear();
  };
}
