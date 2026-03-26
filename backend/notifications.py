"""
FINDORA - Notification Engine v7
Uses Brevo (formerly Sendinblue) HTTP API — works on Render free tier.

WHY v7: Resend requires a verified domain to send to other recipients.
        Brevo allows sending to ANY email address on free plan (300/day).
        Uses HTTPS REST API on port 443 — never blocked by Render free tier.
"""

import os, re, json
from datetime import datetime
from typing import Dict, Tuple, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY  = os.getenv("BREVO_API_KEY", "").strip()
GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS", "").strip()
FROM_NAME      = os.getenv("FROM_NAME", "Findora").strip() or "Findora"
FROM_EMAIL     = os.getenv("FROM_EMAIL", "adrdeepakroshan480@gmail.com").strip()
ENABLED        = bool(BREVO_API_KEY)

print("=" * 55)
print("📧 FINDORA EMAIL ENGINE v7 — BREVO API")
print("=" * 55)
print(f"  BREVO_API_KEY  : {'✅ SET (' + str(len(BREVO_API_KEY)) + ' chars)' if BREVO_API_KEY else '❌ NOT SET'}")
print(f"  FROM_EMAIL     : {FROM_EMAIL}")
print(f"  FROM_NAME      : {FROM_NAME}")
print(f"  EMAIL ENABLED  : {'✅ YES' if ENABLED else '❌ NO'}")
print("=" * 55)


def parse_contact(contact_info: str) -> Tuple[str, Optional[str]]:
    parts = [p.strip() for p in contact_info.split("|")]
    return parts[0] if parts else "", (parts[1] if len(parts) > 1 and parts[1] else None)

def is_valid_email(s: str) -> bool:
    return bool(re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", s.strip()))


def _item_card(label, item, border, bg, img_url):
    def trunc(t, n=120): return (t[:n] + "…") if len(t) > n else t
    img_html = f"""
    <tr><td style="padding-top:10px;">
      <img src="{img_url}" alt="{item.get('title','')}"
        style="width:100%;max-height:220px;object-fit:cover;border-radius:7px;display:block;"/>
    </td></tr>""" if img_url and img_url.startswith("http") else ""

    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
<tr><td style="background:{bg};border-radius:9px;overflow:hidden;border-left:3px solid {border};">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:13px 15px;">
    <tr><td>
      <p style="margin:0 0 4px;font-size:9px;font-weight:700;color:#7a8eaa;letter-spacing:.1em;text-transform:uppercase;">{label}</p>
      <p style="margin:0 0 3px;font-size:14px;font-weight:600;color:#0f172a;">{item.get('title','—')}</p>
      <p style="margin:0 0 4px;font-size:12px;color:#5c718a;line-height:1.5;">{trunc(item.get('description',''))}</p>
      <p style="margin:0;font-size:11px;color:#7a8eaa;">📍 {item.get('location','—')}</p>
    </td></tr>{img_html}
  </table>
</td></tr></table>"""


def _build_html(recipient_role, recipient_item, matched_item, confidence):
    role_label  = "Lost"  if recipient_role == "lost" else "Found"
    other_label = "Found" if recipient_role == "lost" else "Lost"
    action_text = "may have been found" if recipient_role == "lost" else "may belong to someone"
    pct         = round(confidence * 100, 1)
    bar_color   = "#1a4d33" if confidence >= 0.9 else "#1e3a5f"
    now         = datetime.now().strftime("%d %b %Y, %I:%M %p")

    your_card    = _item_card(f"Your {role_label} Item",     recipient_item, "#c5d0e0", "#f0f2f5", recipient_item.get("image_path",""))
    matched_card = _item_card(f"Matched {other_label} Item", matched_item,   "#1e3a5f", "#eef1f7", matched_item.get("image_path",""))

    o_email, o_phone = parse_contact(matched_item.get("contact_info",""))
    phone_row = f"""<tr><td style="padding-top:8px;">
      <p style="margin:0 0 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.45);letter-spacing:.1em;text-transform:uppercase;">Mobile</p>
      <p style="margin:0;font-size:14px;font-weight:600;color:#fff;">{o_phone}</p>
    </td></tr>""" if o_phone else ""

    contact_box = f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
<tr><td style="background:#1e3a5f;border-radius:9px;padding:13px 15px;">
  <p style="margin:0 0 8px;font-size:9px;font-weight:700;color:rgba(255,255,255,.55);letter-spacing:.1em;text-transform:uppercase;">Contact the {other_label} Person</p>
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td>
      <p style="margin:0 0 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.45);letter-spacing:.1em;text-transform:uppercase;">Email</p>
      <p style="margin:0;font-size:14px;font-weight:600;color:#7ab8ff;">{o_email}</p>
    </td></tr>{phone_row}
  </table>
</td></tr></table>"""

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Findora Match Alert</title></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:32px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:14px;overflow:hidden;border:1px solid #dde3ed;max-width:560px;">
  <tr><td style="background:#1e3a5f;padding:22px 26px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:34px;height:34px;background:rgba(255,255,255,0.12);border-radius:8px;text-align:center;vertical-align:middle;font-size:16px;">🔍</td>
      <td style="padding-left:10px;">
        <p style="margin:0;font-size:18px;font-style:italic;color:#fff;font-family:Georgia,serif;">Findora</p>
        <p style="margin:0;font-size:9px;color:rgba(255,255,255,0.55);letter-spacing:.1em;text-transform:uppercase;">AI Lost &amp; Found</p>
      </td>
    </tr></table>
  </td></tr>
  <tr><td style="background:#e8f2ec;padding:11px 26px;border-bottom:1px solid #b8ddc8;">
    <p style="margin:0;font-size:12.5px;font-weight:600;color:#1a4d33;">✓&nbsp; AI Match Detected — {pct}% Confidence</p>
  </td></tr>
  <tr><td style="padding:24px 26px;">
    <p style="margin:0 0 5px;font-size:10px;font-weight:700;color:#7a8eaa;letter-spacing:.1em;text-transform:uppercase;">Match Alert</p>
    <p style="margin:0 0 14px;font-size:22px;font-style:italic;color:#0f172a;font-family:Georgia,serif;">Your {role_label} item {action_text}</p>
    <p style="margin:0 0 20px;font-size:13px;color:#5c718a;line-height:1.65;">Our AI found a potential match. Compare the details below and contact the other party to confirm.</p>
    {your_card}{matched_card}
    <p style="margin:0 0 6px;font-size:11.5px;font-weight:600;color:#2d4460;">Match Confidence: {pct}%</p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
    <tr><td style="background:#eef1f7;border-radius:4px;height:6px;">
      <table width="{round(pct)}%" cellpadding="0" cellspacing="0">
      <tr><td style="background:{bar_color};border-radius:4px;height:6px;"></td></tr>
      </table>
    </td></tr></table>
    {contact_box}
    <p style="margin:0;font-size:12px;color:#7a8eaa;line-height:1.65;">Reach out directly to confirm. If this is not your item, please ignore this email.</p>
  </td></tr>
  <tr><td style="background:#1e3a5f;padding:16px 26px;text-align:center;">
    <p style="margin:0 0 3px;font-size:14px;font-style:italic;color:#fff;font-family:Georgia,serif;">Findora</p>
    <p style="margin:0 0 4px;font-size:10px;color:#7a9bbf;">Intelligent Lost &amp; Found — Powered by AI</p>
    <p style="margin:0;font-size:10px;color:#4a6a8a;">Sent on {now}</p>
  </td></tr>
</table></td></tr></table></body></html>"""


def _build_text(recipient_role, recipient_item, matched_item, confidence):
    pct = round(confidence * 100, 1)
    rl  = "Lost"  if recipient_role == "lost" else "Found"
    ol  = "Found" if recipient_role == "lost" else "Lost"
    email, phone = parse_contact(matched_item.get("contact_info",""))
    return f"""FINDORA — AI Match Alert ({pct}%)
Your {rl} item '{recipient_item.get('title')}' may have been matched.

YOUR {rl.upper()} ITEM
  Title    : {recipient_item.get('title')}
  Desc     : {recipient_item.get('description','')}
  Location : {recipient_item.get('location','')}

MATCHED {ol.upper()} ITEM
  Title    : {matched_item.get('title')}
  Desc     : {matched_item.get('description','')}
  Location : {matched_item.get('location','')}

CONTACT THE {ol.upper()} PERSON
  Email    : {email}
  {"Mobile : " + phone if phone else ""}

— Findora AI Lost & Found"""


def send_email(to_address, recipient_role, recipient_item, matched_item, confidence) -> bool:
    print(f"\n📤 send_email() → {to_address}")

    if not ENABLED:
        print("   ❌ BREVO_API_KEY not set")
        return False

    if not is_valid_email(to_address):
        print(f"   ❌ Invalid address: '{to_address}'")
        return False

    try:
        rl      = "Lost" if recipient_role == "lost" else "Found"
        subject = f"Findora — Your {rl} item may have been matched ({round(confidence*100)}%)"

        payload = {
            "sender":      {"name": FROM_NAME, "email": FROM_EMAIL},
            "to":          [{"email": to_address}],
            "subject":     subject,
            "htmlContent": _build_html(recipient_role, recipient_item, matched_item, confidence),
            "textContent": _build_text(recipient_role, recipient_item, matched_item, confidence),
        }

        # Add reply-to if Gmail configured
        if GMAIL_ADDRESS and is_valid_email(GMAIL_ADDRESS):
            payload["replyTo"] = {"email": GMAIL_ADDRESS}

        data = json.dumps(payload).encode("utf-8")
        req  = Request(
            "https://api.brevo.com/v3/smtp/email",
            data    = data,
            method  = "POST",
            headers = {
                "accept":       "application/json",
                "content-type": "application/json",
                "api-key":      BREVO_API_KEY,
            },
        )

        print("   🔌 Calling Brevo API...")
        with urlopen(req, timeout=15) as resp:
            body   = json.loads(resp.read().decode())
            msg_id = body.get("messageId", "?")
            print(f"   ✅ Delivered → {to_address} (messageId={msg_id})")
            return True

    except URLError as e:
        print(f"   ❌ Brevo API error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def notify_match(lost_item: Dict, found_item: Dict, confidence: float) -> None:
    pct = round(confidence * 100)
    print(f"\n{'='*55}\n📣  notify_match() — {pct}%")
    print(f"    Lost : {lost_item.get('title')} | {lost_item.get('contact_info','')}")
    print(f"    Found: {found_item.get('title')} | {found_item.get('contact_info','')}")
    print(f"{'='*55}")

    for role, item, other in [("lost", lost_item, found_item),
                               ("found", found_item, lost_item)]:
        ci = item.get("contact_info", "").strip()
        if ci:
            email, _ = parse_contact(ci)
            if is_valid_email(email):
                send_email(email, role, item, other, confidence)
            else:
                print(f"   ⚠️  Invalid {role} email: '{email}'")
        else:
            print(f"   ⚠️  {role} item has no contact_info")

    print(f"{'='*55}\n")


if __name__ == "__main__":
    print("\n🧪 Smoke test...")
    notify_match(
        {"title": "Black Samsung S23", "description": "Lost at bus stop",
         "location": "Central Bus Station", "contact_info": "adrdeepakroshan480@gmail.com", "image_path": ""},
        {"title": "Samsung Phone Found", "description": "Found near bus station",
         "location": "Central Bus Station", "contact_info": "adrdeepakroshan480@gmail.com", "image_path": ""},
        0.92,
    )