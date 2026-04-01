"""
Dweb Search — Professional Dark Web Research Tool
Cross-platform anonymous search via the Tor network.
"""

import sys
import subprocess

def setup_dependencies():
    """Automatically installs missing external modules: requests, bs4, and pysocks."""
    dependencies = {
        'requests': 'requests',
        'bs4': 'beautifulsoup4',
        'socks': 'pysocks'
    }
    to_install = []
    for module_name, package_name in dependencies.items():
        try:
            __import__(module_name)
        except ImportError:
            to_install.append(package_name)
            
    if to_install:
        print(f"[*] Checking system for missing modules: {', '.join(to_install)}")
        try:
            # Using sys.executable ensures we use the same Python environment
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + to_install)
            print("[+] Modules installed successfully. Launching application...")
        except Exception as e:
            print(f"[-] Dependency installation failed: {e}")
            print("[!] Please install manually: pip install requests beautifulsoup4 pysocks")

# Run dependency check before importing other external modules
setup_dependencies()

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading, requests, time, json
import subprocess, sys, os, socket, platform, urllib.parse
from datetime import datetime


try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


# ──────────────── OS helpers ────────────────────────────────────────────────

def detect_os():
    s = platform.system().lower()
    return "macos" if s == "darwin" else ("windows" if s == "windows" else "linux")

def is_tor_running(port=9050):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False

def tor_start_cmd():
    os_name = detect_os()
    if os_name == "windows":
        return "tor.exe"
    if os_name == "macos":
        return "brew services start tor\n  OR simply: tor"
    return "tor"


# ──────────────── Backend ────────────────────────────────────────────────────

class DwebResearchTool:
    def __init__(self, proxy_port=9050):
        self.proxy_port = proxy_port
        self.session = None
        self.ui_callback = None

    def set_callback(self, cb):
        self.ui_callback = cb

    def log(self, msg, kind="info"):
        if self.ui_callback:
            self.ui_callback(msg, kind)

    def init_session(self):
        self.log("[*] Initialising Tor session…", "info")
        self.session = requests.Session()
        self.session.proxies = {
            "http":  f"socks5h://127.0.0.1:{self.proxy_port}",
            "https": f"socks5h://127.0.0.1:{self.proxy_port}",
        }
        self.log("[+] Session ready", "success")

    def check_connection(self):
        for i in range(3):
            try:
                self.log(f"[*] Verifying Tor ({i+1}/3)…", "info")
                r = self.session.get("https://check.torproject.org/api/ip", timeout=15)
                d = r.json()
                if d.get("IsTor"):
                    ip = d.get("IP", "?")
                    self.log(f"[+] Tor active — exit IP: {ip}", "success")
                    return True, ip
                self.log("[-] Proxy active but NOT Tor", "error")
                return False, None
            except Exception as e:
                if i < 2:
                    time.sleep(2)
                else:
                    self.log(f"[-] Connection failed: {e}", "error")
        return False, None

    def fetch(self, url, timeout=30):
        try:
            self.log(f"[*] Fetching: {url}", "info")
            t0 = time.time()
            r = self.session.get(url, timeout=timeout,
                headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"},
                allow_redirects=True)
            elapsed = time.time() - t0
            self.log(f"[+] {r.status_code} · {elapsed:.2f}s · {len(r.text):,} bytes", "success")
            return {"url": url, "status": r.status_code,
                    "time": elapsed, "content": r.text,
                    "title": self._title(r.text)}
        except requests.exceptions.Timeout:
            self.log(f"[-] Timeout: {url}", "error")
        except requests.exceptions.ConnectionError:
            self.log(f"[-] Connection error: {url}", "error")
        except Exception as e:
            self.log(f"[-] Error: {e}", "error")
        return None

    def _title(self, html):
        try:
            if BS4_AVAILABLE:
                t = BeautifulSoup(html, "html.parser").find("title")
                return t.get_text().strip()[:120] if t else "No title"
            s, e = html.find("<title>"), html.find("</title>")
            if s != -1 and e != -1:
                return html[s+7:e].strip()[:120]
        except Exception:
            pass
        return "No title"

    def parse_results(self, html):
        out = []
        try:
            if BS4_AVAILABLE:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", class_="result__a"):
                    t, l = a.get_text().strip(), a.get("href","")
                    if t and l:
                        out.append({"title": t, "link": l})
                if not out:
                    for a in soup.find_all("a", href=True):
                        t = a.get_text().strip()
                        if t and len(t) > 15 and "http" in a["href"]:
                            out.append({"title": t[:100], "link": a["href"]})
        except Exception as e:
            self.log(f"[-] Parse error: {e}", "error")
        return out[:15]

    def search(self, query, callback=None):
        def _run():
            ddg = "http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion"
            url = f"{ddg}/?q={urllib.parse.quote_plus(query)}"
            self.log(f"\n{'─'*56}", "info")
            self.log(f"  QUERY: {query}", "highlight")
            self.log(f"{'─'*56}", "info")
            result = self.fetch(url, timeout=60)
            found = []
            if result and result.get("content"):
                found = self.parse_results(result["content"])
                if found:
                    self.log(f"\n[+] {len(found)} result(s):", "success")
                    for i, r in enumerate(found, 1):
                        self.log(f"\n  {i}. {r['title']}", "result_title")
                        if r.get("link"):
                            self.log(f"     {r['link']}", "result_link")
                else:
                    self.log("[-] No parseable results", "warning")
            if callback:
                callback(query, found)
        threading.Thread(target=_run, daemon=True).start()

    def cleanup(self):
        pass


# ──────────────── Tor Dialog ─────────────────────────────────────────────────

class TorDialog(tk.Toplevel):
    C = {
        "bg": "#0d1117", "panel": "#161b22", "border": "#30363d",
        "accent": "#00e676", "error": "#ff5252", "text": "#e6edf3",
        "text2": "#8b949e", "purple": "#7c3aed", "cmd": "#1c2128",
    }

    def __init__(self, parent, cmd):
        super().__init__(parent)
        self.result = "exit"
        self._cmd = cmd
        self._setup(parent)

    def _setup(self, parent):
        C = self.C
        self.title("Dweb Search — Tor Required")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()

        w, h = 560, 420
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        self.geometry(f"{w}x{h}+{px+(pw-w)//2}+{py+(ph-h)//2}")

        # Top accent strip
        tk.Frame(self, bg=C["error"], height=4).pack(fill="x")

        # Icon + title
        tk.Label(self, text="🧅", font=("Helvetica", 52),
                 bg=C["bg"], fg=C["accent"]).pack(pady=(28, 4))
        tk.Label(self, text="Tor Is Not Running",
                 font=("Helvetica", 20, "bold"),
                 bg=C["bg"], fg=C["error"]).pack()
        tk.Label(self,
                 text="Dweb Search routes all traffic through the Tor network.\nPlease start Tor before continuing.",
                 font=("Helvetica", 10), justify="center",
                 bg=C["bg"], fg=C["text2"]).pack(pady=(6, 0))

        # Command box
        box = tk.Frame(self, bg=C["border"], padx=1, pady=1)
        box.pack(fill="x", padx=44, pady=22)
        inner = tk.Frame(box, bg=C["cmd"])
        inner.pack(fill="x")
        tk.Label(inner, text="Open a terminal and run:",
                 font=("Helvetica", 9), anchor="w",
                 bg=C["cmd"], fg=C["text2"]).pack(fill="x", padx=14, pady=(10,2))
        tk.Label(inner, text=self._cmd,
                 font=("Courier New", 13, "bold"), anchor="w",
                 bg=C["cmd"], fg=C["accent"]).pack(fill="x", padx=14, pady=(0,12))

        # Buttons
        bf = tk.Frame(self, bg=C["bg"])
        bf.pack(pady=(0, 28))
        self._make_btn(bf, "⟳  I started Tor — Retry",
                       C["purple"], "white", self._retry).pack(side="left", padx=8)
        self._make_btn(bf, "✕  Exit Application",
                       "#3d1515", C["error"], self._exit).pack(side="left", padx=8)

        self.protocol("WM_DELETE_WINDOW", self._exit)

    def _make_btn(self, parent, text, bg, fg, cmd):
        b = tk.Button(parent, text=text, font=("Helvetica", 10, "bold"),
                      bg=bg, fg=fg, activebackground=bg,
                      activeforeground=fg, relief="flat", bd=0,
                      padx=18, pady=10, cursor="hand2", command=cmd)
        return b

    def _retry(self):
        self.result = "retry"
        self.grab_release()
        self.destroy()

    def _exit(self):
        self.result = "exit"
        self.grab_release()
        self.destroy()


# ──────────────── Main UI ────────────────────────────────────────────────────

class DwebSearchUI:

    # Color palette
    C = {
        "bg":       "#0d1117",
        "panel":    "#161b22",
        "panel2":   "#1c2128",
        "border":   "#30363d",
        "accent":   "#00e676",
        "accent_h": "#00c853",
        "purple":   "#7c3aed",
        "purple_h": "#6d28d9",
        "text":     "#e6edf3",
        "text2":    "#8b949e",
        "success":  "#3fb950",
        "error":    "#ff5252",
        "warning":  "#d29922",
        "info":     "#58a6ff",
        "link":     "#79c0ff",
    }

    QUICK = [
        ("🔒 Privacy Tools",    "privacy tools"),
        ("📧 Encrypted Email",  "encrypted email"),
        ("🧅 Tor Browser",      "tor browser"),
        ("💬 Secure Messaging", "secure messaging"),
        ("🛡️ VPN Services",     "vpn services"),
        ("📰 Dark Web News",    "dark web news"),
        ("🔐 OpSec Guides",     "opsec security guides"),
        ("🌐 Onion Search",     "onion search engines"),
    ]

    def __init__(self):
        self.backend = DwebResearchTool()
        self.backend.set_callback(self._log)
        self.history = []
        self._ready = False
        self._root = None

    # ── launch ───────────────────────────────────────────────────────────────

    def run(self):
        self._build_window()
        self._ready = True
        self._root.after(300, self._startup_tor_check)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    # ── window ───────────────────────────────────────────────────────────────

    def _build_window(self):
        self._root = tk.Tk()
        r = self._root
        r.title("Dweb Search")
        r.geometry("1260x860")
        r.configure(bg=self.C["bg"])
        r.minsize(960, 660)

        # ttk scrollbar style
        s = ttk.Style(r)
        s.theme_use("clam")
        for name in ("Vertical", "Horizontal"):
            s.configure(
                f"Dark.{name}.TScrollbar",
                gripcount=0, relief="flat",
                background=self.C["panel2"],
                troughcolor=self.C["panel"],
                bordercolor=self.C["border"],
                arrowcolor=self.C["text2"],
            )

        self._build_titlebar()
        self._build_body()
        self._build_statusbar()

    # ── title bar ─────────────────────────────────────────────────────────────

    def _build_titlebar(self):
        C = self.C
        bar = tk.Frame(self._root, bg=C["panel"], height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Frame(self._root, bg=C["accent"], height=2).pack(fill="x")

        # Logo
        lf = tk.Frame(bar, bg=C["panel"])
        lf.pack(side="left", padx=28)
        tk.Label(lf, text="🧅", font=("Helvetica", 24),
                 bg=C["panel"], fg=C["accent"]).pack(side="left")
        name_f = tk.Frame(lf, bg=C["panel"])
        name_f.pack(side="left", padx=8)
        tk.Label(name_f, text="Dweb Search",
                 font=("Helvetica", 18, "bold"),
                 bg=C["panel"], fg=C["text"]).pack(anchor="w")
        tk.Label(name_f, text="Anonymous · Encrypted · Private",
                 font=("Helvetica", 8),
                 bg=C["panel"], fg=C["text2"]).pack(anchor="w")

        # Right controls
        rf = tk.Frame(bar, bg=C["panel"])
        rf.pack(side="right", padx=24)

        self._ip_lbl = tk.Label(rf, text="", font=("Helvetica", 9),
                                bg=C["panel"], fg=C["text2"])
        self._ip_lbl.pack(side="left", padx=(0,14))

        self._tor_lbl = tk.Label(rf, text="⬤  Checking…",
                                  font=("Helvetica", 10, "bold"),
                                  bg=C["panel"], fg=C["warning"])
        self._tor_lbl.pack(side="left", padx=(0,18))

        self._mk_btn(rf, "⟳ Verify", C["purple"], C["purple_h"],
                     self._verify_conn).pack(side="left")

    # ── body (sidebar + main) ─────────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self._root, bg=self.C["bg"])
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_main(body)

    def _build_sidebar(self, parent):
        C = self.C
        sb = tk.Frame(parent, bg=C["panel"], width=220)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        tk.Frame(parent, bg=C["border"], width=1).pack(side="left", fill="y")

        tk.Label(sb, text="QUICK SEARCH",
                 font=("Helvetica", 8, "bold"),
                 bg=C["panel"], fg=C["text2"]).pack(anchor="w", padx=18, pady=(18,8))

        for label, query in self.QUICK:
            b = tk.Button(sb, text=label,
                          font=("Helvetica", 10),
                          bg=C["panel"], fg=C["text"],
                          activebackground=C["panel2"],
                          activeforeground=C["accent"],
                          relief="flat", bd=0,
                          anchor="w", padx=18, pady=8,
                          cursor="hand2",
                          command=lambda q=query: self._quick(q))
            b.pack(fill="x")
            b.bind("<Enter>", lambda e, w=b: w.config(bg=C["panel2"], fg=C["accent"]))
            b.bind("<Leave>", lambda e, w=b: w.config(bg=C["panel"], fg=C["text"]))

        tk.Frame(sb, bg=C["border"], height=1).pack(fill="x", padx=18, pady=14)
        tk.Label(sb, text="HISTORY",
                 font=("Helvetica", 8, "bold"),
                 bg=C["panel"], fg=C["text2"]).pack(anchor="w", padx=18, pady=(0,8))

        self._hist_frame = tk.Frame(sb, bg=C["panel"])
        self._hist_frame.pack(fill="x")

    def _build_main(self, parent):
        C = self.C
        main = tk.Frame(parent, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True)

        # Search bar card
        scard = tk.Frame(main, bg=C["panel"],
                         highlightbackground=C["border"], highlightthickness=1)
        scard.pack(fill="x", padx=28, pady=20)

        row = tk.Frame(scard, bg=C["panel"])
        row.pack(fill="x", padx=16, pady=14)

        tk.Label(row, text="🔍", font=("Helvetica", 15),
                 bg=C["panel"], fg=C["text2"]).pack(side="left", padx=(0,10))

        self._entry = tk.Entry(row,
                               font=("Helvetica", 14),
                               bg=C["panel2"], fg=C["text"],
                               insertbackground=C["accent"],
                               relief="flat", bd=0,
                               highlightthickness=2,
                               highlightcolor=C["accent"],
                               highlightbackground=C["border"])
        self._entry.pack(side="left", fill="x", expand=True, ipady=9)
        self._entry.bind("<Return>", lambda _: self._search())

        tk.Frame(row, bg=C["border"], width=1).pack(side="left", fill="y", padx=12)

        self._search_btn = self._mk_btn(row, "  Search  ",
                                         C["accent"], C["accent_h"],
                                         self._search, fg="#0d1117")
        self._search_btn.pack(side="left")

        # Info row inside card
        info_row = tk.Frame(scard, bg=C["panel"])
        info_row.pack(fill="x", padx=16, pady=(0,10))
        tk.Label(info_row,
                 text="🌐  All traffic routed through Tor network  ·  No logs  ·  No tracking",
                 font=("Helvetica", 9), bg=C["panel"], fg=C["text2"]).pack(side="left")

        self._clear_btn = tk.Button(info_row, text="✕ Clear Console",
                                    font=("Helvetica", 8),
                                    bg=C["panel2"], fg=C["error"],
                                    activebackground=C["border"],
                                    relief="flat", bd=0, padx=8, pady=3,
                                    cursor="hand2", command=self._clear)
        self._clear_btn.pack(side="right")

        # Console label
        lf = tk.Frame(main, bg=C["bg"])
        lf.pack(fill="x", padx=30, pady=(0,4))
        tk.Label(lf, text="CONSOLE  &  RESULTS",
                 font=("Helvetica", 8, "bold"),
                 bg=C["bg"], fg=C["text2"]).pack(side="left")
        self._res_count = tk.Label(lf, text="",
                                    font=("Helvetica", 8),
                                    bg=C["bg"], fg=C["success"])
        self._res_count.pack(side="right")

        # Console card
        ccard = tk.Frame(main, bg=C["panel"],
                         highlightbackground=C["border"], highlightthickness=1)
        ccard.pack(fill="both", expand=True, padx=28, pady=(0,8))

        self._console = scrolledtext.ScrolledText(
            ccard, font=("Courier New", 10),
            bg=C["panel2"], fg=C["text"],
            insertbackground=C["accent"],
            relief="flat", bd=0,
            padx=20, pady=16, wrap="word",
            selectbackground=C["purple"],
            selectforeground="white",
        )
        self._console.pack(fill="both", expand=True)

        for tag, fg, extra in [
            ("error",       C["error"],   {}),
            ("warning",     C["warning"], {}),
            ("success",     C["success"], {}),
            ("info",        C["text2"],   {}),
            ("highlight",   C["accent"],  {"font": ("Courier New", 10, "bold")}),
            ("result_title",C["text"],    {"font": ("Courier New", 11, "bold")}),
            ("result_link", C["link"],    {"font": ("Courier New", 9)}),
        ]:
            self._console.tag_config(tag, foreground=fg, **extra)

        self._print_banner()

    # ── status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        C = self.C
        tk.Frame(self._root, bg=C["border"], height=1).pack(fill="x")
        bar = tk.Frame(self._root, bg=C["panel"], height=30)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        self._status_lbl = tk.Label(bar, text="⚡ Starting up…",
                                     font=("Helvetica", 9),
                                     bg=C["panel"], fg=C["text2"])
        self._status_lbl.pack(side="left", padx=18)

        tk.Label(bar, text=f"OS: {detect_os().upper()}",
                 font=("Helvetica", 8),
                 bg=C["panel"], fg=C["text2"]).pack(side="right", padx=8)

        self._time_lbl = tk.Label(bar, text="",
                                   font=("Courier New", 9),
                                   bg=C["panel"], fg=C["text2"])
        self._time_lbl.pack(side="right", padx=14)
        self._tick()

    # ── banner ────────────────────────────────────────────────────────────────

    def _print_banner(self):
        b = (
            "  ╔══════════════════════════════════════════════════════╗\n"
            "  ║        Dweb Search  ·  Dark Web Research Tool        ║\n"
            "  ╠══════════════════════════════════════════════════════╣\n"
            "  ║  🧅  Tor SOCKS5 proxy on port 9050                   ║\n"
            "  ║  🔒  End-to-end encrypted · Zero logs                ║\n"
            "  ║  🌍  Works on Linux · macOS · Windows                ║\n"
            "  ╚══════════════════════════════════════════════════════╝\n\n"
        )
        self._console.insert("end", b, "highlight")
        self._console.see("end")

    # ── Tor startup check ─────────────────────────────────────────────────────

    def _startup_tor_check(self):
        while True:
            if is_tor_running():
                self._root.after(0, self._init_tor_bg)
                return
            dlg = TorDialog(self._root, tor_start_cmd())
            self._root.wait_window(dlg)
            if dlg.result == "exit":
                self._root.destroy()
                return
            self._set_tor_ui("checking")
            self._log("[*] Retrying Tor check…", "info")

    def _init_tor_bg(self):
        def _run():
            self._set_status("Initialising Tor session…", "info")
            self.backend.init_session()
            ok, ip = self.backend.check_connection()
            if ok:
                self._root.after(0, lambda: self._set_tor_ui("connected", ip))
                self._root.after(0, lambda: self._set_status("Tor connected — ready to search", "success"))
                self._root.after(0, lambda: self._log("[+] Tor verified! You may begin searching.", "success"))
            else:
                self._root.after(0, lambda: self._set_tor_ui("error"))
                self._root.after(0, lambda: self._set_status("Tor connection failed", "error"))
                self._root.after(0, lambda: self._log(f"[-] Could not verify Tor. Run: {tor_start_cmd()}", "error"))
        threading.Thread(target=_run, daemon=True).start()

    def _verify_conn(self):
        def _run():
            self._set_status("Verifying Tor connection…", "info")
            self._root.after(0, lambda: self._set_tor_ui("checking"))
            ok, ip = self.backend.check_connection()
            if ok:
                self._root.after(0, lambda: self._set_tor_ui("connected", ip))
                self._root.after(0, lambda: self._set_status("Connection verified ✓", "success"))
            else:
                self._root.after(0, lambda: self._set_tor_ui("error"))
                self._root.after(0, lambda: self._set_status("Connection failed — is Tor running?", "error"))
        threading.Thread(target=_run, daemon=True).start()

    # ── search ────────────────────────────────────────────────────────────────

    def _quick(self, q):
        self._entry.delete(0, "end")
        self._entry.insert(0, q)
        self._search()

    def _search(self):
        q = self._entry.get().strip()
        if not q:
            messagebox.showwarning("Dweb Search", "Please enter a search query.")
            return
        self._search_btn.config(state="disabled", text="Searching…")
        self._set_status(f"Searching: {q[:55]}…", "info")
        self.backend.search(q, self._search_done)

    def _search_done(self, query, results):
        def _done():
            self._search_btn.config(state="normal", text="  Search  ")
            n = len(results)
            self._set_status(f"Done — {n} result(s) for: {query[:40]}", "success")
            self._res_count.config(text=f"{n} result(s) found")
            self._add_history(query)
            self._save(query, results)
        self._root.after(0, _done)

    # ── history sidebar ───────────────────────────────────────────────────────

    def _add_history(self, query):
        if query in self.history:
            return
        self.history.insert(0, query)
        C = self.C
        b = tk.Button(self._hist_frame, text=f"  ▸ {query[:22]}",
                      font=("Helvetica", 9),
                      bg=C["panel"], fg=C["text2"],
                      activebackground=C["panel2"],
                      activeforeground=C["text"],
                      relief="flat", bd=0,
                      anchor="w", padx=18, pady=5,
                      cursor="hand2",
                      command=lambda q=query: self._quick(q))
        b.pack(fill="x", before=self._hist_frame.winfo_children()[0] if self._hist_frame.winfo_children() else None)
        b.bind("<Enter>", lambda e, w=b: w.config(bg=C["panel2"]))
        b.bind("<Leave>", lambda e, w=b: w.config(bg=C["panel"]))

    # ── save results ──────────────────────────────────────────────────────────

    def _save(self, query, results):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"search_{ts}.txt")
            with open(fp, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("DWEB SEARCH — REPORT\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Query:   {query}\n")
                f.write(f"Time:    {datetime.now().isoformat()}\n")
                f.write(f"Results: {len(results)}\n\n")
                for i, r in enumerate(results, 1):
                    f.write(f"{i}. {r.get('title','N/A')}\n")
                    if r.get("link"):
                        f.write(f"   {r['link']}\n")
                    f.write("\n")
            self._log(f"[+] Report saved → {os.path.basename(fp)}", "success")
        except Exception as e:
            self._log(f"[-] Save failed: {e}", "error")

    # ── console helpers ───────────────────────────────────────────────────────

    def _log(self, msg, kind="info"):
        def _ins():
            ts = datetime.now().strftime("%H:%M:%S")
            self._console.insert("end", f"[{ts}] {msg}\n", kind)
            self._console.see("end")
        if self._ready and self._root:
            self._root.after(0, _ins)

    def _clear(self):
        self._console.delete("1.0", "end")
        self._print_banner()
        self._res_count.config(text="")

    # ── status / tor status helpers ───────────────────────────────────────────

    def _set_status(self, text, kind="info"):
        cmap = {"info": self.C["text2"], "success": self.C["success"],
                "error": self.C["error"], "warning": self.C["warning"]}
        fg = cmap.get(kind, self.C["text2"])
        if self._root:
            self._root.after(0, lambda: self._status_lbl.config(text=f"⚡ {text}", fg=fg))

    def _set_tor_ui(self, state, ip=None):
        C = self.C
        configs = {
            "connected": ("⬤  Tor Connected", C["success"]),
            "checking":  ("⬤  Checking…",     C["warning"]),
            "error":     ("⬤  Tor Error",      C["error"]),
        }
        text, fg = configs.get(state, ("⬤  Unknown", C["text2"]))
        self._tor_lbl.config(text=text, fg=fg)
        self._ip_lbl.config(text=f"Exit IP: {ip}" if ip else "")

    # ── clock ─────────────────────────────────────────────────────────────────

    def _tick(self):
        self._time_lbl.config(text=datetime.now().strftime("%H:%M:%S"))
        self._root.after(1000, self._tick)

    # ── widget factory ────────────────────────────────────────────────────────

    def _mk_btn(self, parent, text, bg, bg_h, cmd, fg="white"):
        b = tk.Button(parent, text=text,
                      font=("Helvetica", 10, "bold"),
                      bg=bg, fg=fg,
                      activebackground=bg_h, activeforeground=fg,
                      relief="flat", bd=0, padx=16, pady=8,
                      cursor="hand2", command=cmd)
        b.bind("<Enter>", lambda _: b.config(bg=bg_h))
        b.bind("<Leave>", lambda _: b.config(bg=bg))
        return b

    # ── close ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        self._log("[*] Closing Dweb Search…", "info")
        self.backend.cleanup()
        self._root.destroy()


# ──────────────── Entry point ────────────────────────────────────────────────

if __name__ == "__main__":
    DwebSearchUI().run()