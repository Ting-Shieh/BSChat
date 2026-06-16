"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createStub,
  deleteStub,
  fetchMyOrgs,
  fetchStubs,
  importStubsCsv,
  publishStub,
  unpublishStub,
  updateStub,
  type StubPayload,
  type StubUpdatePayload,
} from "./api";
import { useAuthStore } from "@/features/auth/store";

export function useMyOrgs() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["orgs", "mine", token],
    queryFn: () => fetchMyOrgs(token!),
    enabled: !!token,
  });
}

export function useOrgStubs(orgId: string | null, status?: string) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["org-stubs", orgId, status, token],
    queryFn: () => fetchStubs(token!, orgId!, status),
    enabled: !!token && !!orgId,
  });
}

export function useCreateStub(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StubPayload) => createStub(token!, orgId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org-stubs", orgId] }),
  });
}

export function usePublishStub(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stubId: string) => publishStub(token!, orgId, stubId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org-stubs", orgId] });
      qc.invalidateQueries({ queryKey: ["orgs", "mine"] });
    },
  });
}

export function useUnpublishStub(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stubId: string) => unpublishStub(token!, orgId, stubId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org-stubs", orgId] });
      qc.invalidateQueries({ queryKey: ["orgs", "mine"] });
    },
  });
}

export function useDeleteStub(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stubId: string) => deleteStub(token!, orgId, stubId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org-stubs", orgId] }),
  });
}

export function useUpdateStub(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ stubId, body }: { stubId: string; body: StubUpdatePayload }) =>
      updateStub(token!, orgId, stubId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org-stubs", orgId] });
      qc.invalidateQueries({ queryKey: ["orgs", "mine"] });
    },
  });
}

export function useImportStubsCsv(orgId: string) {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, autoPublish }: { file: File; autoPublish?: boolean }) =>
      importStubsCsv(token!, orgId, file, autoPublish),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org-stubs", orgId] });
      qc.invalidateQueries({ queryKey: ["orgs", "mine"] });
    },
  });
}
