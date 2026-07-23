"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import {
  acceptEnterpriseInvite,
  createEnterpriseInvite,
  createEnterpriseInviteBatch,
  fetchMyPublicIdentities,
  listEnterpriseInvites,
  listEnterpriseMembers,
  listMyEnterpriseApplications,
  removeEnterpriseMember,
  regenerateEnterpriseInviteLink,
  revokeEnterpriseInvite,
  submitEnterpriseApplication,
  transferEnterpriseAdmin,
  updateMyPublicIdentity,
} from "./api";

export function useMyEnterpriseApplications() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["enterprise-applications", token],
    queryFn: () => listMyEnterpriseApplications(token!),
    enabled: !!token,
  });
}

export function useSubmitEnterpriseApplication() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      company_name: string;
      contact_email: string;
      slug_requested?: string;
      estimated_seats?: number;
      note?: string;
    }) => submitEnterpriseApplication(token!, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enterprise-applications"] }),
  });
}

export function useAcceptEnterpriseInvite() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteToken: string) => acceptEnterpriseInvite(token!, inviteToken),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["me"] }),
        qc.invalidateQueries({ queryKey: ["enterprise-members"] }),
        qc.invalidateQueries({ queryKey: ["enterprise-invites"] }),
      ]);
    },
  });
}

export function useEnterpriseMembers(orgId: string | null) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["enterprise-members", orgId, token],
    queryFn: () => listEnterpriseMembers(token!, orgId!),
    enabled: !!token && !!orgId,
  });
}

export function useEnterpriseInvites(orgId: string | null) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["enterprise-invites", orgId, token],
    queryFn: () => listEnterpriseInvites(token!, orgId!),
    enabled: !!token && !!orgId,
  });
}

export function useCreateEnterpriseInvite(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; expires_days?: number }) =>
      createEnterpriseInvite(token!, orgId, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["enterprise-invites", orgId] });
      await qc.refetchQueries({ queryKey: ["enterprise-invites", orgId] });
    },
  });
}

export function useCreateEnterpriseInviteBatch(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { emails: string[]; expires_days?: number }) =>
      createEnterpriseInviteBatch(token!, orgId, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["enterprise-invites", orgId] });
      await qc.refetchQueries({ queryKey: ["enterprise-invites", orgId] });
    },
  });
}

export function useMyPublicIdentities() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["my-public-identity", token],
    queryFn: () => fetchMyPublicIdentities(token!),
    enabled: !!token,
  });
}

export function useUpdateMyPublicIdentity() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      orgId,
      body,
    }: {
      orgId: string;
      body: { external_card_url: string; title?: string | null; display_name?: string | null };
    }) => updateMyPublicIdentity(token!, orgId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-public-identity"] });
      qc.invalidateQueries({ queryKey: ["org-stubs"] });
    },
  });
}

export function useRemoveEnterpriseMember(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => removeEnterpriseMember(token!, orgId, userId),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["enterprise-members", orgId] }),
        qc.invalidateQueries({ queryKey: ["enterprise-invites", orgId] }),
        qc.invalidateQueries({ queryKey: ["me"] }),
      ]);
      await qc.refetchQueries({ queryKey: ["enterprise-members", orgId] });
    },
  });
}

export function useRevokeEnterpriseInvite(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) => revokeEnterpriseInvite(token!, inviteId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["enterprise-invites", orgId] });
      await qc.refetchQueries({ queryKey: ["enterprise-invites", orgId] });
    },
  });
}

export function useRegenerateEnterpriseInviteLink(orgId: string) {
  const token = useAuthStore((s) => s.token);
  return useMutation({
    mutationFn: (inviteId: string) => regenerateEnterpriseInviteLink(token!, inviteId),
  });
}

export function useTransferEnterpriseAdmin(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (newAdminUserId: string) =>
      transferEnterpriseAdmin(token!, orgId, newAdminUserId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["enterprise-members", orgId] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
