"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import {
  acceptNotification,
  acceptSubTeamInvite,
  createSubTeam,
  createSubTeamInvite,
  dissolveSubTeam,
  getSubTeam,
  leaveSubTeam,
  listNotifications,
  listSubTeamInvites,
  listSubTeams,
  markNotificationRead,
  removeSubTeamMember,
  revokeSubTeamInvite,
} from "./api";

export function useSubTeams(enabled = true) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["sub-teams", token],
    queryFn: () => listSubTeams(token!),
    enabled: !!token && enabled,
  });
}

export function useSubTeam(id: string | undefined) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["sub-team", id, token],
    queryFn: () => getSubTeam(token!, id!),
    enabled: !!token && !!id,
  });
}

export function useSubTeamInvites(teamId: string | undefined, enabled: boolean) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["sub-team-invites", teamId, token],
    queryFn: () => listSubTeamInvites(token!, teamId!),
    enabled: !!token && !!teamId && enabled,
  });
}

export function useCreateSubTeam() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string }) =>
      createSubTeam(token!, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sub-teams"] });
    },
  });
}

export function useCreateSubTeamInvite(teamId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (email: string) => createSubTeamInvite(token!, teamId, { email }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["sub-team-invites", teamId] }),
        qc.invalidateQueries({ queryKey: ["notifications"] }),
      ]);
      await qc.refetchQueries({ queryKey: ["sub-team-invites", teamId] });
    },
  });
}

export function useRevokeSubTeamInvite(teamId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) => revokeSubTeamInvite(token!, inviteId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["sub-team-invites", teamId] });
      await qc.refetchQueries({ queryKey: ["sub-team-invites", teamId] });
    },
  });
}

export function useAcceptSubTeamInvite() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteToken: string) => acceptSubTeamInvite(token!, inviteToken),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["sub-teams"] }),
        qc.invalidateQueries({ queryKey: ["notifications"] }),
        qc.invalidateQueries({ queryKey: ["me"] }),
      ]);
    },
  });
}

export function useNotifications() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["notifications", token],
    queryFn: () => listNotifications(token!),
    enabled: !!token,
    refetchInterval: 60_000,
  });
}

export function useAcceptNotification() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => acceptNotification(token!, id),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["notifications"] }),
        qc.invalidateQueries({ queryKey: ["sub-teams"] }),
        qc.invalidateQueries({ queryKey: ["me"] }),
      ]);
      await qc.refetchQueries({ queryKey: ["notifications"] });
      await qc.refetchQueries({ queryKey: ["sub-teams"] });
    },
  });
}

export function useMarkNotificationRead() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => markNotificationRead(token!, id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["notifications"] });
      await qc.refetchQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useLeaveSubTeam(teamId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => leaveSubTeam(token!, teamId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["sub-teams"] });
      await qc.refetchQueries({ queryKey: ["sub-teams"] });
    },
  });
}

export function useDissolveSubTeam(teamId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => dissolveSubTeam(token!, teamId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["sub-teams"] });
      await qc.refetchQueries({ queryKey: ["sub-teams"] });
    },
  });
}

export function useRemoveSubTeamMember(teamId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => removeSubTeamMember(token!, teamId, userId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["sub-team", teamId] });
      await qc.refetchQueries({ queryKey: ["sub-team", teamId] });
    },
  });
}
