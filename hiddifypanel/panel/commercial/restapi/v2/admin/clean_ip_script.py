"""The full clean IP test, served by the panel as one Python file (standard library only).

A browser can not send a chosen upload to an IP (it can not pick the TLS name for it), so the page's quick test misses
the ISPs that cut a connection after ~1.3 KB of upload. This script does the real test from the computer or phone
(Termux) it runs on: TLS to each Cloudflare IP with the CDN domain as SNI, then an upload of SIZE bytes; any HTTP
answer means the data got through. It then reports the working IPs to the panel, which saves them for the ISP the
report comes from. Placeholders (__X__) are filled in by CleanIpScriptApi.
"""

SCRIPT = r'''#!/usr/bin/env python3
# Hiddify clean IP test: run it with the VPN OFF, on the internet (ISP) you want IPs for.
import ipaddress, json, os, random, socket, ssl, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HOST = __HOST__
REPORT = __REPORT__
SIZE = __SIZE__
PER_RANGE = __PER_RANGE__
TIMEOUT = 5
WORKERS = 30
RANGES = __RANGES__
# REALITY SNIs (in use and spare): a TLS connection to this panel's server with each name, as a REALITY client opens it
SNIS = __SNIS__
SERVER_IP = __SERVER_IP__
CONTROL = __CONTROL__


def pick(cidr, n):
    net = ipaddress.ip_network(cidr)
    size = net.num_addresses - 2
    return {str(net.network_address + 1 + random.randrange(size)) for _ in range(min(n, size))}


def probe(ip):
    ctx = ssl.create_default_context()
    ctx.set_alpn_protocols(["http/1.1"])
    req = ("POST / HTTP/1.1\r\nHost: %s\r\nUser-Agent: Mozilla/5.0\r\nContent-Type: application/octet-stream\r\n"
           "Content-Length: %d\r\nConnection: close\r\n\r\n" % (HOST, SIZE)).encode() + os.urandom(SIZE)
    t0 = time.perf_counter()
    try:
        with socket.create_connection((ip, 443), timeout=TIMEOUT) as raw:
            with ctx.wrap_socket(raw, server_hostname=HOST) as s:
                s.settimeout(TIMEOUT)
                s.sendall(req)
                head = s.recv(4096)
        ms = round((time.perf_counter() - t0) * 1000)
        if not head.startswith(b"HTTP/"):
            return None
        colo = ""
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"cf-ray:"):
                colo = line.split(b"-")[-1].strip().decode(errors="replace")
        return {"ip": ip, "ms": ms, "colo": colo}
    except Exception:
        return None


def sni_ok(sni):
    """Whether a TLS handshake with this name gets through to the panel's server (SNI filtering cuts it)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for _ in range(2):
        try:
            with socket.create_connection((SERVER_IP, 443), timeout=6) as raw:
                with ctx.wrap_socket(raw, server_hostname=sni):
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def test_snis():
    if not SNIS or not SERVER_IP:
        return None, []
    if not sni_ok(CONTROL):
        print("\nREALITY SNIs: the server itself did not answer (with %s); SNIs not tested." % CONTROL)
        return False, []
    print("\nREALITY SNIs (as a REALITY client connects to the server):")
    out = []
    with ThreadPoolExecutor(8) as pool:
        for sni, ok in zip(SNIS, pool.map(sni_ok, SNIS)):
            out.append({"sni": sni, "ok": ok})
            print("  %-40s %s" % (sni, "ok" if ok else "FILTERED"))
    return True, out


def main():
    ips = sorted({ip for cidr in RANGES for ip in pick(cidr, PER_RANGE)})
    random.shuffle(ips)
    print("Hiddify clean IP test: %d Cloudflare IPs, %d-byte upload, via %s" % (len(ips), SIZE, HOST))
    print("Keep the VPN OFF: the test is for the internet this device is on.\n")
    found, done, lock = [], 0, threading.Lock()
    with ThreadPoolExecutor(WORKERS) as pool:
        for fut in as_completed([pool.submit(probe, ip) for ip in ips]):
            r = fut.result()
            with lock:
                done += 1
                if r:
                    found.append(r)
                sys.stdout.write("\r  tested %d/%d, working %d " % (done, len(ips), len(found)))
                sys.stdout.flush()
    found.sort(key=lambda r: r["ms"])
    print("\n")
    for r in found[:15]:
        print("  %-16s %5d ms  %s" % (r["ip"], r["ms"], r["colo"]))
    if not found:
        print("No IP passed. Is the VPN off? Try again later or on another network.")
    control, snis = test_snis()
    body = json.dumps({"ips": found[:200], "tested": len(ips), "size": SIZE, "sni_control": control, "snis": snis}).encode()
    req = urllib.request.Request(REPORT, data=body, method="POST", headers={"Content-Type": "application/json", "User-Agent": "hiddify-clean-ip"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read() or b"{}")
        print("\nSent to the panel. ISP: %s." % (out.get("short_name") or "?"))
        print(out.get("message") or "")
    except Exception as e:
        print("\nCould not send the result to the panel (%s)." % e)
        print("Copy the IPs above into the panel's Clean IP page by hand, or run this again.")


if __name__ == "__main__":
    main()
'''
