import { apiFetch } from "@/shared/lib/api-client";

export interface SubTeamSummary {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  role: string;
  member_count: number;
}

export interface SubTeamMemberInfo {
  user_id: string;
  display_name: string | null;
  email: string;
  role: string;
  joined_at: string;
}

export interface SubTeamDetail {
  id: string;
  org_id: string;
  org_name: string;
  name: string;
  description: string | null;
  my_role: string | null;
  member_count: number;
  members: SubTeamMemberInfo[];
}

export interface SubTeamInvitePreview {
  sub_team_id: string;
  sub_team_name: string;
  org_id: string;
  org_name: string;
  expires_at: string;
  seats_remaining: number;
}

export interface CreateSubTeamInviteResponse {
  invite_id: string;
  token: string;
  sub_team_id: string;
  sub_team_name: string;
  org_name: string;
  expires_at: string;
  join_path: string;
}

export function listSubTeams(token: string) {
  return apiFetch<SubTeamSummary[]>("/api/v1/sub-teams", { token });
}

export function createSubTeam(
  token: string,
  body: { name: string; description?: string },
) {
  return apiFetch<SubTeamSummary>("/api/v1/sub-teams", {
    token,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getSubTeam(token: string, id: string) {
  return apiFetch<SubTeamDetail>(`/api/v1/sub-teams/${id}`, { token });
}

export function createSubTeamInvite(token: string, id: string) {
  return apiFetch<CreateSubTeamInviteResponse>(`/api/v1/sub-teams/${id}/invites`, {
    token,
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function previewSubTeamInvite(tokenPath: string) {
  return apiFetch<SubTeamInvitePreview>(`/api/v1/join/sub-team/${tokenPath}`);
}

export function acceptSubTeamInvite(token: string, inviteToken: string) {
  return apiFetch<SubTeamSummary>(`/api/v1/join/sub-team/${inviteToken}`, {
    token,
    method: "POST",
  });
}

export function leaveSubTeam(token: string, id: string) {
  return apiFetch<void>(`/api/v1/sub-teams/${id}/leave`, {
    token,
    method: "POST",
  });
}

export function dissolveSubTeam(token: string, id: string) {
  return apiFetch<void>(`/api/v1/sub-teams/${id}`, {
    token,
    method: "DELETE",
  });
}

export function removeSubTeamMember(token: string, teamId: string, userId: string) {
  return apiFetch<void>(`/api/v1/sub-teams/${teamId}/members/${userId}`, {
    token,
    method: "DELETE",
  });
}
