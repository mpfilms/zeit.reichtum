#!/usr/bin/env python3
"""Prüft die Meta-Zugangsdaten aus .env, ohne etwas zu posten (nur Lesezugriffe).

    python3 scripts/meta_check.py

Gibt nie einen Token aus. Nur Standardbibliothek.
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "v25.0"
GRAPH = f"https://graph.facebook.com/{VERSION}"
NEEDED = ["pages_manage_posts", "pages_read_engagement", "pages_show_list",
          "instagram_basic", "instagram_content_publish"]


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line.strip())
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env


ENV = load_env()
SECRETS = [v for k, v in ENV.items() if v and ("TOKEN" in k or "SECRET" in k or "KEY" in k)]


def redact(text):
    for s in SECRETS:
        text = text.replace(s, "<geheim>")
    return text


def get(path, token, **params):
    params["access_token"] = token
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
        except Exception:
            err = {"message": f"HTTP {e.code}"}
        return None, redact(f"{err.get('message', '?')} (Code {err.get('code', '?')})")
    except Exception as e:
        return None, redact(f"Keine Verbindung zu Meta: {type(e).__name__}: {e}")


def main():
    token = ENV.get("META_SYSTEM_TOKEN", "")
    page_id, ig_id = ENV.get("FB_PAGE_ID", ""), ENV.get("IG_USER_ID", "")
    problems = []
    if not token:
        sys.exit("META_SYSTEM_TOKEN fehlt in .env")

    print("1) Token prüfen")
    d, err = get("debug_token", token, input_token=token)
    if err:
        print("   ✗", err)
        problems.append("Token nicht prüfbar")
    else:
        info = d.get("data", {})
        valid = info.get("is_valid")
        exp = info.get("expires_at", 0)
        print("   gültig:", valid, "| Typ:", info.get("type"), "| läuft ab:", "nie" if exp == 0 else exp)
        scopes = set(info.get("scopes", []))
        missing = [s for s in NEEDED if s not in scopes]
        print("   fehlende Berechtigungen:", ", ".join(missing) or "keine")
        if not valid:
            problems.append("Token ungültig")
        if missing:
            problems.append("Berechtigungen fehlen: " + ", ".join(missing))

    print("2) Facebook-Seite lesen")
    d, err = get(page_id, token, fields="name,access_token,instagram_business_account")
    if err:
        print("   ✗", err)
        problems.append("Seite nicht lesbar (Seite dem Systemnutzer zuweisen?)")
    else:
        print("   Seite:", d.get("name"), "| Seiten-Token erhalten:", bool(d.get("access_token")))
        linked = (d.get("instagram_business_account") or {}).get("id")
        print("   mit Seite verknüpfter Instagram-Account:", linked or "keiner")
        if not d.get("access_token"):
            problems.append("Kein Seiten-Token (Systemnutzer braucht volle Kontrolle über die Seite)")
        if linked and linked != ig_id:
            problems.append(f"IG_USER_ID ({ig_id}) weicht vom verknüpften Account ({linked}) ab")

    print("3) Instagram-Account lesen")
    d, err = get(ig_id, token, fields="username,name")
    if err:
        print("   ✗", err)
        problems.append("Instagram-Account nicht lesbar (dem Systemnutzer zuweisen?)")
    else:
        print("   Account: @" + str(d.get("username")))

    print()
    if problems:
        print("ERGEBNIS: Noch nicht fertig:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("ERGEBNIS: Alles in Ordnung. Posten kann getestet werden.")


if __name__ == "__main__":
    main()
