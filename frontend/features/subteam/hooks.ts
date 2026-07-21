"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import {
  acceptSubTeamInvite,
  createSubTeam,
  createSubTeamInvite,
  dissolveSubTeam,
  getSubTeam,
  leaveSubTeam,
  listSubTeams,
  removeSubTeamMember,
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
  return useMutation({
    mutationFn: () => createSubTeamInvite(token!, teamId),
  });
}

export function useAcceptSubTeamInvite() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteToken: string) => acceptSubTeamInvite(token!, inviteToken),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sub-teams"] });
    },
  });
}

export function useLeaveSubTeam(teamId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => leaveSubTeam(token!, teamId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sub-teams"] });
    },
  });
}

export function useDissolveSubTeam(teamId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => dissolveSubTeam(token!, teamId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sub-teams"] });
    },
  });
}

export function useRemoveSubTeamMember(teamId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => removeSubTeamMember(token!, teamId, userId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sub-team", teamId] });
    },
  });
}
