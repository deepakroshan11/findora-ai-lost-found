"""
FINDORA - Notification Engine
Uses Gmail SMTP — sends to ANY email worldwide, free forever.
Handles contact_info format: "email" or "email | phone"
"""

import os
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASSWORD", "")
FROM_NAME      = os.getenv("FROM_NAME", "Findora")
ENABLED        = bool(GMAIL_ADDRESS and GMAIL_APP_PASS)


# ─── Parse contact_info → (email, phone|None) ─────────────────────────
def parse_contact(contact_info: str) -> Tuple[str, Optional[str]]:
    """
    Parses contact_info stored as:
      "user@email.com"              → ("user@email.com", None)
      "user@email.com | +91 98765"  → ("user@email.com", "+91 98765")
    """
    parts = [p.strip() for p in contact_info.split("|")]
    email = parts[0] if parts else ""
    phone = parts[1] if len(parts) > 1 and parts[1] else None
    return email, phone


def is_valid_email(s: str) -> bool:
    return bool(re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", s.strip()))


# ─── Build contact box HTML (shows email + phone if available) ────────
def build_contact_box(other_label: str, contact_info: str) -> str:
    email, phone = parse_contact(contact_info)
    phone_row = ""
    if phone:
        phone_row = f"""
    <tr><td style="padding:6px 0 0;">
      <p style="margin:0 0 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.45);letter-spacing:.1em;text-transform:uppercase;">Mobile</p>
      <p style="margin:0;font-size:14px;font-weight:600;color:#fff;">{phone}</p>
    </td></tr>"""

    return f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
  <tr><td style="background:#1e3a5f;border-radius:9px;padding:13px 15px;">
    <p style="margin:0 0 6px;font-size:9px;font-weight:700;color:rgba(255,255,255,.55);letter-spacing:.1em;text-transform:uppercase;">Contact the {other_label} Person</p>
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding-bottom:{'6px' if phone else '0'};">
        <p style="margin:0 0 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.45);letter-spacing:.1em;text-transform:uppercase;">Email</p>
        <p style="margin:0;font-size:14px;font-weight:600;color:#fff;">{email}</p>
      </td></tr>{phone_row}
    </table>
  </td></tr></table>"""


# ─── HTML email template ──────────────────────────────────────────────
def build_html(recipient_role, recipient_item, matched_item, confidence):
    role_label  = "Lost"  if recipient_role == "lost"  else "Found"
    other_label = "Found" if recipient_role == "lost"  else "Lost"
    action_text = "may have been found" if recipient_role == "lost" else "may belong to someone"
    pct         = round(confidence * 100, 1)
    bar_color   = "#1a4d33" if confidence >= 0.9 else "#1e3a5f"
    bar_width   = round(pct)
    now         = datetime.now().strftime("%d %b %Y, %I:%M %p")

    def trunc(t, n=120):
        return (t[:n] + "...") if len(t) > n else t

    contact_box = build_contact_box(other_label, matched_item.get("contact_info", "—"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Findora Match Alert</title></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:32px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:14px;overflow:hidden;border:1px solid #dde3ed;max-width:560px;">

<tr><td style="background:#1e3a5f;padding:22px 26px;">
  <table cellpadding="0" cellspacing="0"><tr>
    <td style="width:34px;height:34px;background:rgba(255,255,255,0.12);border-radius:8px;text-align:center;vertical-align:middle;font-size:16px;">&#128269;</td>
    <td style="padding-left:10px;">
      <p style="margin:0;font-size:18px;font-style:italic;color:#fff;font-family:Georgia,serif;">Findora</p>
      <p style="margin:0;font-size:9px;color:rgba(255,255,255,0.55);letter-spacing:.1em;text-transform:uppercase;">AI Lost &amp; Found</p>
    </td>
  </tr></table>
</td></tr>

<tr><td style="background:#e8f2ec;padding:11px 26px;border-bottom:1px solid #b8ddc8;">
  <p style="margin:0;font-size:12.5px;font-weight:600;color:#1a4d33;">&#10003;&nbsp; AI Match Detected — {pct}% Confidence</p>
</td></tr>

<tr><td style="padding:24px 26px;">
  <p style="margin:0 0 5px;font-size:10px;font-weight:700;color:#7a8eaa;letter-spacing:.1em;text-transform:uppercase;">Match Alert</p>
  <p style="margin:0 0 14px;font-size:22px;font-style:italic;color:#0f172a;font-family:Georgia,serif;">Your {role_label} item {action_text}</p>
  <p style="margin:0 0 20px;font-size:13px;color:#5c718a;line-height:1.65;">Our AI found a potential match. Review the details and contact the other party to confirm.</p>

  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
  <tr><td style="background:#f0f2f5;border-radius:9px;padding:13px 15px;">
    <p style="margin:0 0 4px;font-size:9px;font-weight:700;color:#7a8eaa;letter-spacing:.1em;text-transform:uppercase;">Your {role_label} Item</p>
    <p style="margin:0 0 3px;font-size:14px;font-weight:600;color:#0f172a;">{recipient_item.get('title','—')}</p>
    <p style="margin:0 0 4px;font-size:12px;color:#5c718a;line-height:1.5;">{trunc(recipient_item.get('description',''))}</p>
    <p style="margin:0;font-size:11px;color:#7a8eaa;">&#128205; {recipient_item.get('location','—')}</p>
  </td></tr></table>

  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
  <tr><td style="background:#eef1f7;border-radius:9px;padding:13px 15px;border-left:3px solid #1e3a5f;">
    <p style="margin:0 0 4px;font-size:9px;font-weight:700;color:#7a8eaa;letter-spacing:.1em;text-transform:uppercase;">Matched {other_label} Item</p>
    <p style="margin:0 0 3px;font-size:14px;font-weight:600;color:#0f172a;">{matched_item.get('title','—')}</p>
    <p style="margin:0 0 4px;font-size:12px;color:#5c718a;line-height:1.5;">{trunc(matched_item.get('description',''))}</p>
    <p style="margin:0;font-size:11px;color:#7a8eaa;">&#128205; {matched_item.get('location','—')}</p>
  </td></tr></table>

  <p style="margin:0 0 6px;font-size:11.5px;font-weight:600;color:#2d4460;">Match Confidence: {pct}%</p>
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
  <tr><td style="background:#eef1f7;border-radius:4px;height:6px;">
    <table width="{bar_width}%" cellpadding="0" cellspacing="0">
    <tr><td style="background:{bar_color};border-radius:4px;height:6px;"></td></tr>
    </table>
  </td></tr></table>

  {contact_box}

  <p style="margin:0;font-size:12px;color:#7a8eaa;line-height:1.65;">Reach out directly to confirm. If this is not your item, ignore this email.</p>
</td></tr>

<tr><td style="background:#1e3a5f;padding:16px 26px;text-align:center;">
  <p style="margin:0 0 3px;font-size:14px;font-style:italic;color:#fff;font-family:Georgia,serif;">Findora</p>
  <p style="margin:0 0 4px;font-size:10px;color:#7a9bbf;">Intelligent Lost &amp; Found — Powered by AI</p>
  <p style="margin:0;font-size:10px;color:#4a6a8a;">Sent on {now}</p>
</td></tr>

</table>
</td></tr></table>
</body></html>"""


def build_text(recipient_role, recipient_item, matched_item, confidence):
    pct   = round(confidence * 100, 1)
    rl    = "Lost"  if recipient_role == "lost" else "Found"
    ol    = "Found" if recipient_role == "lost" else "Lost"
    email, phone = parse_contact(matched_item.get("contact_info", ""))
    phone_line = f"Mobile : {phone}" if phone else ""
    return f"""FINDORA — AI Match Alert ({pct}%)

Your {rl} item '{recipient_item.get('title')}' may have been matched.

YOUR ITEM: {recipient_item.get('title')}
{recipient_item.get('description','')}
Location: {recipient_item.get('location','')}

MATCHED {ol.upper()} ITEM: {matched_item.get('title')}
{matched_item.get('description','')}
Location: {matched_item.get('location','')}

CONTACT THE {ol.upper()} PERSON:
Email  : {email}
{phone_line}

— Findora AI Lost & Found
"""


# ─── Send via Gmail SMTP ──────────────────────────────────────────────
def send_email(to_address, recipient_role, recipient_item, matched_item, confidence):
    if not ENABLED:
        print("   ⚠️  Gmail not configured — set GMAIL_ADDRESS + GMAIL_APP_PASSWORD in .env")
        return False

    rl      = "Lost" if recipient_role == "lost" else "Found"
    subject = f"Findora — Your {rl} item may have been matched ({round(confidence*100)}%)"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{FROM_NAME} <{GMAIL_ADDRESS}>"
        msg["To"]      = to_address

        msg.attach(MIMEText(build_text(recipient_role, recipient_item, matched_item, confidence), "plain"))
        msg.attach(MIMEText(build_html(recipient_role, recipient_item, matched_item, confidence), "html"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            smtp.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())

        print(f"   📧 Email sent → {to_address}")
        return True

    except Exception as e:
        print(f"   ❌ Email failed → {to_address}: {e}")
        return False


# ─── Main entry — called by agent ────────────────────────────────────
def notify_match(lost_item: Dict, found_item: Dict, confidence: float):
    print(f"\n   📣 Notifying users ({round(confidence*100)}% match)...")

    lc = lost_item.get("contact_info", "").strip()
    fc = found_item.get("contact_info", "").strip()

    if lc:
        lost_email, _ = parse_contact(lc)
        if is_valid_email(lost_email):
            print(f"   → Lost user  : {lost_email}")
            send_email(lost_email, "lost", lost_item, found_item, confidence)
        else:
            print(f"   ⚠️  Invalid lost email: {lost_email}")
    else:
        print("   ⚠️  Lost item has no contact info")

    if fc:
        found_email, _ = parse_contact(fc)
        if is_valid_email(found_email):
            print(f"   → Found user : {found_email}")
            send_email(found_email, "found", found_item, lost_item, confidence)
        else:
            print(f"   ⚠️  Invalid found email: {found_email}")
    else:
        print("   ⚠️  Found item has no contact info")