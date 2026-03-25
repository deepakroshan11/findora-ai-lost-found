"""
FINDORA - Notification Engine v4
Gmail SMTP — Cloudinary images embedded as Base64
FIXES:
  - Strips spaces from GMAIL_APP_PASSWORD automatically
  - Full step-by-step debug logging so you can see exactly where it fails
  - Robust contact_info parsing (email | phone)
  - Fallback to direct Cloudinary URL if image download fails
"""

import os
import re
import smtplib
import ssl
import base64
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ───────────────────────────────────────────────────────────────
GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS", "").strip()
# CRITICAL: strip all whitespace — Render env vars sometimes have spaces
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
FROM_NAME      = os.getenv("FROM_NAME", "Findora").strip() or "Findora"
API_BASE       = os.getenv("API_BASE_URL", "http://localhost:8000").strip()
ENABLED        = bool(GMAIL_ADDRESS and GMAIL_APP_PASS)

# ── Startup diagnostics ───────────────────────────────────────────────────────
print("=" * 55)
print("📧 FINDORA EMAIL ENGINE — STARTUP CHECK")
print("=" * 55)
print(f"  GMAIL_ADDRESS   : {GMAIL_ADDRESS or '❌ NOT SET'}")
print(f"  GMAIL_APP_PASS  : {'✅ SET (' + str(len(GMAIL_APP_PASS)) + ' chars)' if GMAIL_APP_PASS else '❌ NOT SET'}")
print(f"  FROM_NAME       : {FROM_NAME}")
print(f"  EMAIL ENABLED   : {'✅ YES' if ENABLED else '❌ NO — emails will be skipped'}")
if GMAIL_APP_PASS and len(GMAIL_APP_PASS) != 16:
    print(f"  ⚠️  WARNING: App Password is {len(GMAIL_APP_PASS)} chars — should be exactly 16")
print("=" * 55)


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_contact(contact_info: str) -> Tuple[str, Optional[str]]:
    """Split 'email@x.com | +91 98765' into (email, phone_or_None)."""
    parts = [p.strip() for p in contact_info.split("|")]
    email = parts[0] if parts else ""
    phone = parts[1] if len(parts) > 1 and parts[1] else None
    return email, phone


def is_valid_email(s: str) -> bool:
    return bool(re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", s.strip()))


def load_image_from_url(url: str) -> Optional[Tuple[str, str, str]]:
    """
    Download image from a Cloudinary (or any https://) URL.
    Returns (cid, base64_data, mime_type) or None on failure.
    """
    if not url or not url.startswith("http"):
        return None

    ext = url.split("?")[0].split(".")[-1].lower()
    mime = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png",  "webp": "image/webp",
    }.get(ext, "image/jpeg")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Findora/4.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read()
        b64 = base64.b64encode(raw).decode("utf-8")
        # Safe CID: use last path segment without extension
        cid = re.sub(r"[^a-zA-Z0-9_]", "_", url.split("/")[-1].split("?")[0])
        print(f"   📥 Image downloaded OK ({len(raw)//1024}KB) cid={cid}")
        return cid, b64, mime
    except Exception as e:
        print(f"   ⚠️  Image download failed: {url[:70]}… — {e}")
        return None


# ── HTML Builders ─────────────────────────────────────────────────────────────

def _contact_box(other_label: str, contact_info: str) -> str:
    email, phone = parse_contact(contact_info)
    phone_row = ""
    if phone:
        phone_row = f"""
    <tr><td style="padding-top:8px;">
      <p style="margin:0 0 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.45);
                letter-spacing:.1em;text-transform:uppercase;">Mobile</p>
      <p style="margin:0;font-size:14px;font-weight:600;color:#fff;">{phone}</p>
    </td></tr>"""
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
<tr><td style="background:#1e3a5f;border-radius:9px;padding:13px 15px;">
  <p style="margin:0 0 8px;font-size:9px;font-weight:700;color:rgba(255,255,255,.55);
            letter-spacing:.1em;text-transform:uppercase;">Contact the {other_label} Person</p>
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td>
      <p style="margin:0 0 2px;font-size:9px;font-weight:700;color:rgba(255,255,255,.45);
                letter-spacing:.1em;text-transform:uppercase;">Email</p>
      <p style="margin:0;font-size:14px;font-weight:600;color:#7ab8ff;">{email}</p>
    </td></tr>{phone_row}
  </table>
</td></tr></table>"""


def _item_card(label: str, item: Dict, border: str, bg: str, cid: Optional[str]) -> str:
    def trunc(t, n=120):
        return (t[:n] + "…") if len(t) > n else t

    img_html = ""
    if cid:
        img_html = f"""
    <tr><td style="padding-top:10px;">
      <img src="cid:{cid}" alt="{item.get('title','')}"
        style="width:100%;max-height:220px;object-fit:cover;border-radius:7px;display:block;" />
    </td></tr>"""
    elif item.get("image_path", "").startswith("http"):
        img_html = f"""
    <tr><td style="padding-top:10px;">
      <img src="{item['image_path']}" alt="{item.get('title','')}"
        style="width:100%;max-height:220px;object-fit:cover;border-radius:7px;display:block;" />
    </td></tr>"""

    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
<tr><td style="background:{bg};border-radius:9px;overflow:hidden;border-left:3px solid {border};">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:13px 15px;">
    <tr><td>
      <p style="margin:0 0 4px;font-size:9px;font-weight:700;color:#7a8eaa;
                letter-spacing:.1em;text-transform:uppercase;">{label}</p>
      <p style="margin:0 0 3px;font-size:14px;font-weight:600;color:#0f172a;">
        {item.get('title','—')}</p>
      <p style="margin:0 0 4px;font-size:12px;color:#5c718a;line-height:1.5;">
        {trunc(item.get('description',''))}</p>
      <p style="margin:0;font-size:11px;color:#7a8eaa;">📍 {item.get('location','—')}</p>
    </td></tr>
    {img_html}
  </table>
</td></tr></table>"""


def _build_html(
    recipient_role: str,
    recipient_item: Dict,
    matched_item: Dict,
    confidence: float,
    r_cid: Optional[str],
    m_cid: Optional[str],
) -> str:
    role_label  = "Lost"  if recipient_role == "lost"  else "Found"
    other_label = "Found" if recipient_role == "lost"  else "Lost"
    action_text = "may have been found" if recipient_role == "lost" else "may belong to someone"
    pct         = round(confidence * 100, 1)
    bar_color   = "#1a4d33" if confidence >= 0.9 else "#1e3a5f"
    bar_width   = round(pct)
    now         = datetime.now().strftime("%d %b %Y, %I:%M %p")

    your_card    = _item_card(f"Your {role_label} Item",     recipient_item, "#c5d0e0", "#f0f2f5", r_cid)
    matched_card = _item_card(f"Matched {other_label} Item", matched_item,   "#1e3a5f", "#eef1f7", m_cid)
    contact_box  = _contact_box(other_label, matched_item.get("contact_info", "—"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Findora Match Alert</title>
</head>
<body style="margin:0;padding:0;background:#f0f2f5;
             font-family:'Helvetica Neue',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#f0f2f5;padding:32px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:14px;overflow:hidden;
              border:1px solid #dde3ed;max-width:560px;">

  <!-- HEADER -->
  <tr><td style="background:#1e3a5f;padding:22px 26px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:34px;height:34px;background:rgba(255,255,255,0.12);
                 border-radius:8px;text-align:center;vertical-align:middle;
                 font-size:16px;">🔍</td>
      <td style="padding-left:10px;">
        <p style="margin:0;font-size:18px;font-style:italic;color:#fff;
                  font-family:Georgia,serif;">Findora</p>
        <p style="margin:0;font-size:9px;color:rgba(255,255,255,0.55);
                  letter-spacing:.1em;text-transform:uppercase;">AI Lost &amp; Found</p>
      </td>
    </tr></table>
  </td></tr>

  <!-- BANNER -->
  <tr><td style="background:#e8f2ec;padding:11px 26px;
                 border-bottom:1px solid #b8ddc8;">
    <p style="margin:0;font-size:12.5px;font-weight:600;color:#1a4d33;">
      ✓&nbsp; AI Match Detected — {pct}% Confidence</p>
  </td></tr>

  <!-- BODY -->
  <tr><td style="padding:24px 26px;">
    <p style="margin:0 0 5px;font-size:10px;font-weight:700;color:#7a8eaa;
              letter-spacing:.1em;text-transform:uppercase;">Match Alert</p>
    <p style="margin:0 0 14px;font-size:22px;font-style:italic;color:#0f172a;
              font-family:Georgia,serif;">
      Your {role_label} item {action_text}</p>
    <p style="margin:0 0 20px;font-size:13px;color:#5c718a;line-height:1.65;">
      Our AI found a potential match. Compare the details below and contact
      the other party to confirm.</p>

    {your_card}
    {matched_card}

    <p style="margin:0 0 6px;font-size:11.5px;font-weight:600;color:#2d4460;">
      Match Confidence: {pct}%</p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
    <tr><td style="background:#eef1f7;border-radius:4px;height:6px;">
      <table width="{bar_width}%" cellpadding="0" cellspacing="0">
      <tr><td style="background:{bar_color};border-radius:4px;height:6px;"></td></tr>
      </table>
    </td></tr></table>

    {contact_box}

    <p style="margin:0;font-size:12px;color:#7a8eaa;line-height:1.65;">
      Reach out directly to confirm. If this is not your item, please ignore
      this email.</p>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="background:#1e3a5f;padding:16px 26px;text-align:center;">
    <p style="margin:0 0 3px;font-size:14px;font-style:italic;color:#fff;
              font-family:Georgia,serif;">Findora</p>
    <p style="margin:0 0 4px;font-size:10px;color:#7a9bbf;">
      Intelligent Lost &amp; Found — Powered by AI</p>
    <p style="margin:0;font-size:10px;color:#4a6a8a;">Sent on {now}</p>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""


def _build_text(
    recipient_role: str,
    recipient_item: Dict,
    matched_item: Dict,
    confidence: float,
) -> str:
    pct  = round(confidence * 100, 1)
    rl   = "Lost"  if recipient_role == "lost" else "Found"
    ol   = "Found" if recipient_role == "lost" else "Lost"
    email, phone = parse_contact(matched_item.get("contact_info", ""))
    phone_line = f"Mobile : {phone}" if phone else ""
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
  Email  : {email}
  {phone_line}

— Findora AI Lost & Found
"""


# ── Core send function ────────────────────────────────────────────────────────

def send_email(
    to_address: str,
    recipient_role: str,
    recipient_item: Dict,
    matched_item: Dict,
    confidence: float,
) -> bool:
    print(f"\n📤 send_email() called → {to_address}")

    # ── Pre-flight checks ─────────────────────────────────────────────────
    if not ENABLED:
        print("   ❌ EMAIL DISABLED — GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set in env")
        print("      Fix: add these vars in Render → Environment → Edit")
        return False

    if not is_valid_email(to_address):
        print(f"   ❌ Invalid recipient address: '{to_address}'")
        return False

    if len(GMAIL_APP_PASS) != 16:
        print(f"   ⚠️  GMAIL_APP_PASSWORD is {len(GMAIL_APP_PASS)} chars "
              f"(should be 16). Check for spaces or truncation in Render env vars.")

    rl      = "Lost" if recipient_role == "lost" else "Found"
    subject = (f"Findora — Your {rl} item may have been matched "
               f"({round(confidence * 100)}%)")

    # ── Download images from Cloudinary ──────────────────────────────────
    print("   📥 Downloading item images...")
    r_img = load_image_from_url(recipient_item.get("image_path", ""))
    m_img = load_image_from_url(matched_item.get("image_path", ""))
    r_cid = r_img[0] if r_img else None
    m_cid = m_img[0] if m_img else None
    print(f"   Images ready — recipient: {bool(r_cid)}, matched: {bool(m_cid)}")

    # ── Build message ─────────────────────────────────────────────────────
    try:
        msg            = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = f"{FROM_NAME} <{GMAIL_ADDRESS}>"
        msg["To"]      = to_address

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(
            _build_text(recipient_role, recipient_item, matched_item, confidence),
            "plain",
        ))
        alt.attach(MIMEText(
            _build_html(recipient_role, recipient_item, matched_item,
                        confidence, r_cid, m_cid),
            "html",
        ))
        msg.attach(alt)

        # Embed images
        for img_data in [r_img, m_img]:
            if img_data:
                cid, b64data, mime_type = img_data
                img_bytes = base64.b64decode(b64data)
                mime_img  = MIMEImage(img_bytes, _subtype=mime_type.split("/")[1])
                mime_img.add_header("Content-ID",          f"<{cid}>")
                mime_img.add_header("Content-Disposition", "inline")
                msg.attach(mime_img)

        # ── SMTP send ─────────────────────────────────────────────────────
        print(f"   🔌 Connecting smtp.gmail.com:465...")
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as smtp:
            print(f"   🔑 Logging in as {GMAIL_ADDRESS}...")
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            print(f"   📨 Sending to {to_address}...")
            smtp.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())

        print(f"   ✅ Email delivered → {to_address} "
              f"(images embedded: {bool(r_cid or m_cid)})")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"   ❌ Gmail auth FAILED: {e}")
        print("      Causes:")
        print("      1. GMAIL_APP_PASSWORD has spaces — must be 16 chars, no spaces")
        print("      2. 2-Step Verification not enabled on Google account")
        print("      3. App Password revoked — generate a new one at:")
        print("         https://myaccount.google.com/apppasswords")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        print(f"   ❌ Recipient refused: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"   ❌ SMTP error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error sending email: {e}")
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def notify_match(lost_item: Dict, found_item: Dict, confidence: float) -> None:
    """
    Send match notification emails to both the lost-item reporter
    and the found-item reporter.
    """
    pct = round(confidence * 100)
    print(f"\n{'='*55}")
    print(f"📣  notify_match() — {pct}% confidence")
    print(f"    Lost : {lost_item.get('title')} | {lost_item.get('contact_info','')}")
    print(f"    Found: {found_item.get('title')} | {found_item.get('contact_info','')}")
    print(f"{'='*55}")

    # ── Notify lost-item owner ─────────────────────────────────────────────
    lc = lost_item.get("contact_info", "").strip()
    if lc:
        lost_email, _ = parse_contact(lc)
        if is_valid_email(lost_email):
            send_email(lost_email, "lost", lost_item, found_item, confidence)
        else:
            print(f"   ⚠️  Invalid lost-item email: '{lost_email}'")
    else:
        print("   ⚠️  Lost item has no contact_info")

    # ── Notify found-item owner ────────────────────────────────────────────
    fc = found_item.get("contact_info", "").strip()
    if fc:
        found_email, _ = parse_contact(fc)
        if is_valid_email(found_email):
            send_email(found_email, "found", found_item, lost_item, confidence)
        else:
            print(f"   ⚠️  Invalid found-item email: '{found_email}'")
    else:
        print("   ⚠️  Found item has no contact_info")

    print(f"{'='*55}\n")


# ── Quick smoke-test (run: python notifications.py) ───────────────────────────
if __name__ == "__main__":
    print("\n🧪 Running smoke test...")
    test_lost = {
        "title":        "Black Samsung Galaxy S23",
        "description":  "Lost my black Samsung phone at the bus stop",
        "location":     "Central Bus Station",
        "contact_info": "adrdeepakroshan480@gmail.com | +91 9876543210",
        "image_path":   "",
    }
    test_found = {
        "title":        "Samsung Phone Found",
        "description":  "Found a Samsung Galaxy phone near bus station",
        "location":     "Central Bus Station",
        "contact_info": "adrdeepakroshan480@gmail.com",
        "image_path":   "",
    }
    notify_match(test_lost, test_found, 0.92)