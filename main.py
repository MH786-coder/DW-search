import requests
import time
import json
import subprocess
import sys
import os
import signal

class DarkWebResearchTool:
    def __init__(self, proxy_port=9050):
        self.proxy_port = proxy_port
        self.tor_process = None
        self.check_and_setup_tor()
        self.session = self._create_tor_session()
        
    def check_and_setup_tor(self):
        print("[*] Checking Tor installation...")
        
        if not self._check_tor_installed():
            print("[*] Tor not found. Installing...")
            self._install_tor()
        
        if not self._check_tor_running():
            print("[*] Tor not running. Starting...")
            self._start_tor()
        
        print("[*] Waiting for Tor to initialize...")
        time.sleep(10)
    
    def _check_tor_installed(self):
        try:
            result = subprocess.run(["which", "tor"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _install_tor(self):
        try:
            if os.path.exists("/etc/debian_version"):
                subprocess.run(["sudo", "apt", "update"], check=True)
                subprocess.run(["sudo", "apt", "install", "-y", "tor"], check=True)
            elif os.path.exists("/etc/redhat-release"):
                subprocess.run(["sudo", "yum", "install", "-y", "tor"], check=True)
            elif os.path.exists("/etc/arch-release"):
                subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "tor"], check=True)
            else:
                print("[!] Unsupported Linux distribution. Please install Tor manually:")
                print("    sudo apt install tor  (Debian/Ubuntu)")
                print("    sudo yum install tor  (RHEL/CentOS)")
                print("    sudo pacman -S tor    (Arch)")
                sys.exit(1)
            print("[+] Tor installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"[!] Failed to install Tor: {e}")
            sys.exit(1)
    
    def _check_tor_running(self):
        try:
            result = subprocess.run(["pgrep", "tor"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _start_tor(self):
        try:
            self.tor_process = subprocess.Popen(
                ["tor"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            print("[+] Tor process started")
        except Exception as e:
            print(f"[!] Failed to start Tor: {e}")
            print("[*] Trying to start Tor service...")
            try:
                subprocess.run(["sudo", "systemctl", "start", "tor"], check=True)
                print("[+] Tor service started")
            except:
                print("[!] Could not start Tor. Please start manually:")
                print("    sudo systemctl start tor")
                sys.exit(1)
    
    def _create_tor_session(self):
        session = requests.Session()
        session.proxies = {
            'http': f'socks5h://127.0.0.1:{self.proxy_port}',
            'https': f'socks5h://127.0.0.1:{self.proxy_port}'
        }
        return session
    
    def check_tor_connection(self):
        max_retries = 5
        for i in range(max_retries):
            try:
                print(f"[*] Connection attempt {i+1}/{max_retries}...")
                response = self.session.get('https://check.torproject.org/api/ip', timeout=15)
                data = response.json()
                if data.get('IsTor'):
                    print(f"[+] Connected to Tor. IP: {data.get('IP')}")
                    return True
                else:
                    print("[-] Not using Tor")
                    return False
            except Exception as e:
                if i < max_retries - 1:
                    print(f"[-] Attempt {i+1} failed, retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    print(f"[-] Tor connection failed: {e}")
                    return False
        return False
    
    def search_onion_site(self, onion_url, timeout=30):
        try:
            print(f"\n[*] Accessing: {onion_url}")
            start_time = time.time()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'
            }
            
            response = self.session.get(
                onion_url, 
                timeout=timeout, 
                headers=headers,
                allow_redirects=True
            )
            
            elapsed = time.time() - start_time
            
            print(f"[+] Response time: {elapsed:.2f}s")
            print(f"[+] Status code: {response.status_code}")
            print(f"[+] Content size: {len(response.text)} bytes")
            
            return {
                'url': onion_url,
                'status_code': response.status_code,
                'response_time': elapsed,
                'title': self._extract_title(response.text)
            }
            
        except requests.exceptions.Timeout:
            print(f"[-] Timeout accessing {onion_url}")
        except requests.exceptions.ConnectionError:
            print(f"[-] Connection error to {onion_url}")
        except Exception as e:
            print(f"[-] Error: {e}")
        
        return None
    
    def _extract_title(self, html):
        try:
            start = html.find('<title>')
            end = html.find('</title>')
            if start != -1 and end != -1:
                return html[start+7:end].strip()[:100]
        except:
            pass
        return "No title found"
    
    def search_archives(self, search_term):
        research_sites = [
            'http://darkzzx4avcsuofgfez5zq75cqc4mprjvfqy2vhldwks4fkbbgaoaeqd.onion',
            'http://danielas3rtn54uwmofdo3qx2lvbcmjyqblixr5o6bh35r3u76bwi5aad.onion',
        ]
        
        results = []
        for site in research_sites:
            print(f"\n[*] Searching on: {site}")
            search_url = f"{site}/search?q={search_term}"
            result = self.search_onion_site(search_url, timeout=45)
            if result:
                results.append(result)
            
            time.sleep(5)
        
        return results
    
    def cleanup(self):
        if self.tor_process:
            print("\n[*] Stopping Tor process...")
            os.killpg(os.getpgid(self.tor_process.pid), signal.SIGTERM)

if __name__ == "__main__":
    print("="*60)
    print("           Dark Web Research Tool - Linux")
    print("="*60)
    
    researcher = None
    try:
        researcher = DarkWebResearchTool(proxy_port=9050)
        
        if not researcher.check_tor_connection():
            print("\n[-] Failed to connect to Tor network")
            print("[*] Troubleshooting tips:")
            print("    1. Check if Tor is installed: which tor")
            print("    2. Check if port 9050 is open: netstat -tln | grep 9050")
            print("    3. Try starting Tor manually: sudo systemctl start tor")
            print("    4. Check Tor logs: sudo journalctl -u tor")
            sys.exit(1)
        
        print("\n[*] Testing connection to public research sites...")
        
        ddg_result = researcher.search_onion_site('http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion')
        
        if ddg_result:
            print(f"\n[+] Successfully accessed research site")
            print(json.dumps(ddg_result, indent=2))
        
        print("\n" + "="*60)
        
    except KeyboardInterrupt:
        print("\n\n[*] Interrupted by user")
    finally:
        if researcher:
            researcher.cleanup()