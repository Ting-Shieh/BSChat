"""Sub-team invitation email."""

from __future__ import annotations

from datetime import datetime
from html import escape

from app.core.email import send_email


def render_sub_team_invite_email(
    *,
    org_name: str,
    team_name: str,
    inviter_name: str,
    join_url: str,
    expires_at: datetime,
) -> tuple[str, str, str]:
    safe_org = escape(org_name)
    safe_team = escape(team_name)
    safe_inviter = escape(inviter_name)
    safe_url = escape(join_url, quote=True)
    expiry = expires_at.strftime("%Y/%m/%d")
    subject = f"{team_name}｜{org_name} 邀請你加入子團隊"
    html = f"""\
<!doctype html>
<html lang="zh-Hant">
<body style="margin:0;background:#f3f6f5;color:#18332f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans TC',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f6f5;">
    <tr><td align="center" style="padding:40px 16px;">
      <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border:1px solid #dce6e3;border-radius:18px;">
        <tr><td style="height:6px;background:#0f4c5c;"></td></tr>
        <tr><td style="padding:36px 36px 12px;">
          <div style="font-size:13px;font-weight:700;letter-spacing:.12em;color:#0f4c5c;">BSCHAT · 子團隊邀請</div>
          <h1 style="margin:18px 0 12px;font-size:26px;line-height:1.3;">加入 {safe_team}</h1>
          <p style="margin:0;font-size:16px;line-height:1.75;color:#4b635f;">
            {safe_inviter} 邀請你加入 <strong>{safe_org}</strong> 的子團隊 <strong>{safe_team}</strong>。
            加入後可與同隊共享名片庫。
          </p>
        </td></tr>
        <tr><td style="padding:20px 36px 32px;">
          <a href="{safe_url}" style="display:inline-block;background:#0f4c5c;color:#ffffff;text-decoration:none;font-size:16px;font-weight:700;padding:14px 24px;border-radius:10px;">接受邀請</a>
          <p style="margin:24px 0 0;font-size:13px;color:#6b7f7b;">有效至 {expiry}。也可在 BSChat App「我的」站內通知接受。</p>
          <p style="margin:8px 0 0;font-size:12px;word-break:break-all;color:#0f4c5c;">{safe_url}</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    text = (
        f"{inviter_name} 邀請你加入 {org_name} 的子團隊「{team_name}」。\n\n"
        f"接受邀請：{join_url}\n\n"
        f"有效至 {expiry}。也可在 BSChat App 站內通知接受。"
    )
    return subject, html, text


async def send_sub_team_invite_email(
    *,
    to_email: str,
    org_name: str,
    team_name: str,
    inviter_name: str,
    join_url: str,
    expires_at: datetime,
) -> bool:
    subject, html, text = render_sub_team_invite_email(
        org_name=org_name,
        team_name=team_name,
        inviter_name=inviter_name,
        join_url=join_url,
        expires_at=expires_at,
    )
    return await send_email(to_email=to_email, subject=subject, html=html, text=text)
