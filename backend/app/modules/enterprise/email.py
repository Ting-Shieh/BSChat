"""Enterprise invitation email rendering and Resend delivery."""

from __future__ import annotations

from datetime import datetime
from html import escape

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings


def render_enterprise_invite_email(
    *,
    org_name: str,
    inviter_name: str,
    join_url: str,
    expires_at: datetime,
) -> tuple[str, str, str]:
    """Return subject, HTML, and plain-text bodies."""
    safe_org = escape(org_name)
    safe_inviter = escape(inviter_name)
    safe_url = escape(join_url, quote=True)
    expiry = expires_at.strftime("%Y/%m/%d")
    subject = f"{org_name} 邀請你加入 BSChat"
    html = f"""\
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(subject)}</title>
</head>
<body style="margin:0;background:#f3f6f5;color:#18332f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans TC',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f6f5;">
    <tr><td align="center" style="padding:40px 16px;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #dce6e3;border-radius:18px;overflow:hidden;">
        <tr><td style="height:6px;background:#0f766e;"></td></tr>
        <tr><td style="padding:36px 36px 12px;">
          <div style="font-size:13px;font-weight:700;letter-spacing:.12em;color:#0f766e;">BSCHAT · 企業邀請</div>
          <h1 style="margin:18px 0 12px;font-size:28px;line-height:1.3;color:#102a26;">加入 {safe_org}</h1>
          <p style="margin:0;font-size:16px;line-height:1.75;color:#4b635f;">
            {safe_inviter} 邀請你加入 <strong style="color:#18332f;">{safe_org}</strong> 的企業租戶。
            完成註冊或登入後，你將取得企業成員權限。
          </p>
        </td></tr>
        <tr><td style="padding:20px 36px 32px;">
          <a href="{safe_url}" style="display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;font-size:16px;font-weight:700;padding:14px 24px;border-radius:10px;">接受企業邀請</a>
          <p style="margin:24px 0 6px;font-size:13px;line-height:1.6;color:#6b7f7b;">邀請連結有效至 {expiry}，且僅限收到此信的 Email 使用。</p>
          <p style="margin:0;font-size:12px;line-height:1.6;color:#879995;">若按鈕無法開啟，請複製以下連結：</p>
          <p style="margin:6px 0 0;font-size:12px;line-height:1.6;word-break:break-all;color:#0f766e;">{safe_url}</p>
        </td></tr>
        <tr><td style="border-top:1px solid #e6eeec;padding:20px 36px;font-size:12px;line-height:1.6;color:#879995;">
          若你不認識邀請人或未預期收到此信，請直接忽略；帳號不會因此自動加入企業。
        </td></tr>
      </table>
      <p style="margin:18px 0 0;font-size:12px;color:#91a19e;">BSChat · 在需要的時刻找到對的人</p>
    </td></tr>
  </table>
</body>
</html>"""
    text = (
        f"{org_name} 邀請你加入 BSChat\n\n"
        f"{inviter_name} 邀請你加入 {org_name} 的企業租戶。\n"
        "完成註冊或登入後，你將取得企業成員權限。\n\n"
        f"接受邀請：{join_url}\n\n"
        f"邀請連結有效至 {expiry}，且僅限收到此信的 Email 使用。\n"
        "若你不認識邀請人或未預期收到此信，請直接忽略。"
    )
    return subject, html, text


async def send_enterprise_invite_email(
    *,
    to_email: str,
    org_name: str,
    inviter_name: str,
    join_url: str,
    expires_at: datetime,
) -> bool:
    """Send through Resend; return False when email is not configured."""
    settings = get_settings()
    if not settings.resend_api_key:
        return False

    subject, html, text = render_enterprise_invite_email(
        org_name=org_name,
        inviter_name=inviter_name,
        join_url=join_url,
        expires_at=expires_at,
    )
    from_addr = settings.resend_from_email or "BSChat <onboarding@resend.dev>"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": from_addr,
                "to": [to_email],
                "subject": subject,
                "html": html,
                "text": text,
            },
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="EMAIL_SEND_FAILED",
        )
    return True
