"""Everything this server can tell about itself, for the "Server" tab of the IP sheet: the CPU (model, maker,
generation and micro-architecture, clocks, cores, caches, instruction sets), memory, disks, the system (OS, kernel,
virtualisation, the machine's maker and BIOS) and the network (cards, kernel tuning).

Read without root (the panel runs as its own user) from ``/proc``, ``/sys``, ``lscpu`` and ``lsblk``. Labels are
translated by the page: each row is ``{"key", "value"}``, values are already formatted (units, not words). What does not
change is kept ``_STATIC_SECONDS``; clocks, load, memory use and uptime are read on every call.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import time
from typing import Any

import psutil

_STATIC_SECONDS = 600
_static: tuple[float, dict] | None = None

# Instruction sets worth knowing about on a proxy server (crypto speed, vector units, virtualisation)
_FEATURES = [
    ("aes", "AES-NI"),
    ("sha_ni", "SHA-NI"),
    ("pclmulqdq", "PCLMUL"),
    ("vaes", "VAES"),
    ("avx", "AVX"),
    ("avx2", "AVX2"),
    ("avx512f", "AVX-512"),
    ("fma", "FMA3"),
    ("bmi2", "BMI2"),
    ("sse4_2", "SSE4.2"),
    ("rdrand", "RDRAND"),
    ("rdseed", "RDSEED"),
    ("vmx", "VT-x"),
    ("svm", "AMD-V"),
    ("nx", "NX"),
    ("hypervisor", "Hypervisor"),
    # ARM
    ("asimd", "NEON"),
    ("sha2", "SHA2"),
    ("pmull", "PMULL"),
    ("sve", "SVE"),
]


# --------------------------------------------------------------------------- small readers


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""


def _run(*cmd: str, timeout: float = 4) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _size(n: float | int | None, binary: bool = True) -> str:
    if not n:
        return ""
    step, units = (1024, ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]) if binary else (1000, ["B", "KB", "MB", "GB", "TB", "PB"])
    n = float(n)
    for unit in units:
        if n < step or unit == units[-1]:
            return f"{n:.0f} {unit}" if n >= 100 or unit == "B" else f"{n:.1f} {unit}".replace(".0 ", " ")
        n /= step
    return ""


def _mhz(v: float | None) -> str:
    if not v or v <= 0:
        return ""
    return f"{v / 1000:.2f} GHz" if v >= 1000 else f"{v:.0f} MHz"


def _duration(seconds: float) -> str:
    seconds = int(seconds)
    d, rest = divmod(seconds, 86400)
    h, rest = divmod(rest, 3600)
    m = rest // 60
    return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"


def _row(key: str, value: Any, mono: bool = False) -> dict | None:
    value = "" if value is None else str(value).strip()
    return {"key": key, "value": value, "mono": mono} if value else None


def _section(key: str, *rows: dict | None) -> dict:
    return {"key": key, "rows": [r for r in rows if r]}


# --------------------------------------------------------------------------- CPU


def _cpuinfo() -> dict[str, str]:
    """The first processor's fields of /proc/cpuinfo (ARM: its own field names)."""
    out: dict[str, str] = {}
    for line in _read("/proc/cpuinfo").splitlines():
        if not line.strip():
            if out:
                break
            continue
        k, _, v = line.partition(":")
        out.setdefault(k.strip().lower(), v.strip())
    return out


def _lscpu() -> dict[str, str]:
    raw = _run("lscpu", "-J")
    out: dict[str, str] = {}
    try:
        def walk(items):
            for item in items:
                out[item["field"].rstrip(":").strip()] = (item.get("data") or "").strip()
                walk(item.get("children") or [])

        walk(json.loads(raw).get("lscpu", []))
    except (ValueError, KeyError, TypeError, AttributeError):
        for line in _run("lscpu").splitlines():
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


# Intel family 6 model numbers → micro-architecture (the server and desktop lines seen on VPS hosts)
_INTEL_MODELS = {
    0x1A: "Nehalem", 0x2C: "Westmere", 0x2F: "Westmere-EX", 0x2A: "Sandy Bridge", 0x2D: "Sandy Bridge-EP",
    0x3A: "Ivy Bridge", 0x3E: "Ivy Bridge-EP", 0x3C: "Haswell", 0x3F: "Haswell-EP", 0x45: "Haswell", 0x46: "Haswell",
    0x3D: "Broadwell", 0x47: "Broadwell", 0x4F: "Broadwell-EP", 0x56: "Broadwell-DE", 0x4E: "Skylake", 0x5E: "Skylake",
    0x55: "Skylake-SP", 0x8E: "Kaby Lake", 0x9E: "Coffee Lake", 0xA5: "Comet Lake", 0xA6: "Comet Lake", 0x7D: "Ice Lake",
    0x7E: "Ice Lake", 0x6A: "Ice Lake-SP", 0x6C: "Ice Lake-D", 0x8C: "Tiger Lake", 0x8D: "Tiger Lake", 0xA7: "Rocket Lake",
    0x97: "Alder Lake", 0x9A: "Alder Lake", 0xB7: "Raptor Lake", 0xBA: "Raptor Lake", 0xBF: "Raptor Lake",
    0x8F: "Sapphire Rapids", 0xCF: "Emerald Rapids", 0xAD: "Granite Rapids", 0xAE: "Granite Rapids", 0xAF: "Sierra Forest",
    0xAA: "Meteor Lake", 0xC5: "Arrow Lake", 0xC6: "Arrow Lake", 0xBD: "Lunar Lake", 0x5C: "Apollo Lake", 0x7A: "Gemini Lake",
    0x86: "Snow Ridge", 0x96: "Elkhart Lake",
}
_XEON_SCALABLE_GEN = {"1": ("Skylake-SP", "1st Gen Xeon Scalable"), "2": ("Cascade Lake", "2nd Gen Xeon Scalable"),
                      "3": ("Ice Lake-SP", "3rd Gen Xeon Scalable"), "4": ("Sapphire Rapids", "4th Gen Xeon Scalable"),
                      "5": ("Emerald Rapids", "5th Gen Xeon Scalable"), "6": ("Granite Rapids", "Xeon 6")}
_XEON_E5_GEN = {"": ("Sandy Bridge-EP", "Xeon E5/E7 v1"), "2": ("Ivy Bridge-EP", "Xeon E5/E7 v2"), "3": ("Haswell-EP", "Xeon E5/E7 v3"),
                "4": ("Broadwell-EP", "Xeon E5/E7 v4")}
_EPYC_GEN = {"1": ("Zen", "1st Gen EPYC (Naples)"), "2": ("Zen 2", "2nd Gen EPYC (Rome)"), "3": ("Zen 3", "3rd Gen EPYC (Milan)"),
             "4": ("Zen 4", "4th Gen EPYC (Genoa)"), "5": ("Zen 5", "5th Gen EPYC (Turin)")}
_RYZEN_GEN = {"1": "Zen", "2": "Zen+", "3": "Zen 2", "4": "Zen 2", "5": "Zen 3", "7": "Zen 4", "8": "Zen 4", "9": "Zen 5"}
_ORD = {1: "1st", 2: "2nd", 3: "3rd"}
# The CPU models QEMU/KVM copies, by their names
_QEMU_MODELS = {
    "nehalem": ("Nehalem", ""), "westmere": ("Westmere", ""), "sandybridge": ("Sandy Bridge", "Xeon E5 v1 era"),
    "ivybridge": ("Ivy Bridge", "Xeon E5 v2 era"), "haswell": ("Haswell", "Xeon E5 v3 era"), "broadwell": ("Broadwell", "Xeon E5 v4 era"),
    "skylake": ("Skylake-SP", "1st Gen Xeon Scalable"), "cascadelake": ("Cascade Lake", "2nd Gen Xeon Scalable"),
    "cooperlake": ("Cooper Lake", "3rd Gen Xeon Scalable"), "icelake": ("Ice Lake-SP", "3rd Gen Xeon Scalable"),
    "sapphirerapids": ("Sapphire Rapids", "4th Gen Xeon Scalable"), "emeraldrapids": ("Emerald Rapids", "5th Gen Xeon Scalable"),
    "graniterapids": ("Granite Rapids", "Xeon 6"), "naples": ("Zen", "1st Gen EPYC (Naples)"), "rome": ("Zen 2", "2nd Gen EPYC (Rome)"),
    "milan": ("Zen 3", "3rd Gen EPYC (Milan)"), "genoa": ("Zen 4", "4th Gen EPYC (Genoa)"), "turin": ("Zen 5", "5th Gen EPYC (Turin)"),
}


def _amd_by_family(family: int, model: int) -> tuple[str, str]:
    if family == 0x17:
        if model <= 0x0F:
            return "Zen", "1st Gen (Naples / Summit Ridge)"
        if model <= 0x2F:
            return "Zen+", "Zen+ (Pinnacle Ridge)"
        return "Zen 2", "2nd Gen EPYC (Rome) / Ryzen 3000"
    if family == 0x19:
        if model <= 0x0F or 0x20 <= model <= 0x5F:
            return "Zen 3", "3rd Gen EPYC (Milan) / Ryzen 5000"
        return "Zen 4", "4th Gen EPYC (Genoa) / Ryzen 7000"
    if family == 0x1A:
        return "Zen 5", "5th Gen EPYC (Turin) / Ryzen 9000"
    return {0x15: ("Bulldozer family", ""), 0x16: ("Jaguar", ""), 0x10: ("K10", "")}.get(family, ("", ""))


def cpu_generation(name: str, family: int | None, model: int | None, stepping: int | None) -> tuple[str, str]:
    """(micro-architecture, generation) from the model name, else from the family/model numbers."""
    n = name or ""
    # QEMU names the CPU model it copies: "Intel Xeon Processor (Cascadelake)", "AMD EPYC-Rome Processor"
    m = re.search(r"\(([A-Za-z]+)|EPYC-([A-Za-z]+)", n)
    if m:
        code = (m.group(1) or m.group(2) or "").lower()
        if code in _QEMU_MODELS:
            return _QEMU_MODELS[code]
    m = re.search(r"Xeon.*?(Platinum|Gold|Silver|Bronze)\s+(\d)(\d)\d\d", n, re.I)
    if m:
        return _XEON_SCALABLE_GEN.get(m.group(3), ("", ""))
    m = re.search(r"Xeon\s*(?:\(R\)\s*)?(?:CPU\s+)?E[57]-\d{4}\w?\s*(?:v(\d))?", n, re.I)
    if m:
        return _XEON_E5_GEN.get(m.group(1) or "", ("", ""))
    m = re.search(r"Xeon.*?\b(6\d{3}[A-Z]?)\b", n)
    if m and "xeon 6" in n.lower():
        return "Granite Rapids / Sierra Forest", "Xeon 6"
    m = re.search(r"Xeon.*?\bD-(\d)\d{3}", n)
    if m:
        return {"1": ("Broadwell-DE", "Xeon D-1500"), "2": ("Skylake-D", "Xeon D-2100")}.get(m.group(1), ("", ""))
    m = re.search(r"EPYC\s+(?:Embedded\s+)?\d{3}(\d)", n, re.I)
    if m:
        return _EPYC_GEN.get(m.group(1), ("", ""))
    m = re.search(r"Core\(?T?M?\)?\s*i[3579]-(\d{4,5})", n, re.I)
    if m:
        digits = m.group(1)
        gen = int(digits[:2]) if len(digits) == 5 else int(digits[0])
        arch = _INTEL_MODELS.get(model or -1, "") if (family or 0) == 6 else ""
        return arch, f"{_ORD.get(gen, f'{gen}th')} Gen Intel Core"
    m = re.search(r"Ryzen\s+(?:Threadripper\s+)?\d\s+(?:PRO\s+)?(\d)\d{3}", n, re.I) or re.search(r"Threadripper\s+(?:PRO\s+)?(\d)\d{3}", n, re.I)
    if m:
        arch = _RYZEN_GEN.get(m.group(1), "")
        return arch, f"Ryzen {m.group(1)}000 series"
    lower = n.lower()
    if "amd" in lower or "epyc" in lower or "ryzen" in lower:
        if family:
            return _amd_by_family(family, model or 0)
    if (family or 0) == 6 and model in _INTEL_MODELS:
        arch = _INTEL_MODELS[model]
        if model == 0x55 and stepping is not None:
            arch = "Cooper Lake" if stepping >= 10 else "Cascade Lake" if stepping >= 5 else "Skylake-SP"
        return arch, ""
    if family in (0x17, 0x19, 0x1A):
        return _amd_by_family(family, model or 0)
    return "", ""


def _int(v: str | None, base: int = 10) -> int | None:
    try:
        return int(str(v).strip(), base)
    except (TypeError, ValueError):
        return None


def _cpu_static() -> tuple[dict, list[str]]:
    info, ls = _cpuinfo(), _lscpu()
    name = ls.get("Model name") or info.get("model name") or info.get("cpu model") or info.get("hardware") or platform.processor()
    vendor = ls.get("Vendor ID") or info.get("vendor_id") or ""
    family, model, stepping = _int(ls.get("CPU family") or info.get("cpu family")), _int(ls.get("Model") or info.get("model")), _int(ls.get("Stepping") or info.get("stepping"))
    arch_name, generation = cpu_generation(name, family, model, stepping)
    flags = set((ls.get("Flags") or info.get("flags") or info.get("features") or "").split())
    virtual = bool(re.search(r"QEMU|Virtual|KVM|Common", name, re.I))
    base = re.search(r"@\s*([\d.]+)\s*GHz", name or "")
    base_mhz = float(base.group(1)) * 1000 if base else _int(_read("/sys/devices/system/cpu/cpu0/cpufreq/base_frequency")) and _int(_read("/sys/devices/system/cpu/cpu0/cpufreq/base_frequency")) / 1000
    max_mhz = float(ls.get("CPU max MHz") or 0) or (psutil.cpu_freq().max if psutil.cpu_freq() else 0)
    min_mhz = float(ls.get("CPU min MHz") or 0)
    sockets = _int(ls.get("Socket(s)")) or 1
    cores = psutil.cpu_count(logical=False) or (sockets * (_int(ls.get("Core(s) per socket")) or 1))
    threads = psutil.cpu_count(logical=True) or 1
    fms = " · ".join(x for x in [f"Family {family}" if family is not None else "", f"Model {model}" if model is not None else "", f"Stepping {stepping}" if stepping is not None else ""] if x)
    vendor_name = {"GenuineIntel": "Intel", "AuthenticAMD": "AMD", "HygonGenuine": "Hygon", "CentaurHauls": "Centaur / Zhaoxin"}.get(vendor, vendor)
    if "AMD" in (name or "") and vendor_name == "Intel":
        vendor_name = "AMD (the hypervisor reports Intel)"
    cpu = {
        "name": name,
        "vendor": vendor_name or ls.get("Vendor ID", ""),
        "microarch": arch_name,
        "generation": generation,
        "virtual": virtual,
        "cores": cores,
        "threads": threads,
        "sockets": sockets,
        "base_mhz": base_mhz or 0,
        "max_mhz": max_mhz or 0,
        "rows": [
            _row("model", name),
            _row("vendor", vendor_name),
            _row("microarch", arch_name),
            _row("generation", generation),
            _row("familyModel", fms, True),
            _row("architecture", ls.get("Architecture") or platform.machine(), True),
            _row("opModes", ls.get("CPU op-mode(s)")),
            _row("sockets", sockets),
            _row("cores", cores),
            _row("threads", threads),
            _row("threadsPerCore", ls.get("Thread(s) per core")),
            _row("baseClock", _mhz(base_mhz)),
            _row("maxClock", _mhz(max_mhz)),
            _row("minClock", _mhz(min_mhz)),
            _row("bogomips", ls.get("BogoMIPS") or info.get("bogomips"), True),
            _row("l1d", ls.get("L1d cache") or ls.get("L1d")),
            _row("l1i", ls.get("L1i cache") or ls.get("L1i")),
            _row("l2", ls.get("L2 cache") or ls.get("L2")),
            _row("l3", ls.get("L3 cache") or ls.get("L3")),
            _row("numa", ls.get("NUMA node(s)")),
            _row("addressSizes", ls.get("Address sizes") or info.get("address sizes"), True),
            _row("byteOrder", ls.get("Byte Order")),
            _row("microcode", info.get("microcode"), True),
            _row("hypervisor", ls.get("Hypervisor vendor")),
            _row("virtType", ls.get("Virtualization type")),
            _row("governor", _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"), True),
            _row("cpuDriver", _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"), True),
            _row("vulnerable", _vulnerabilities()),
        ],
    }
    features = [label for flag, label in _FEATURES if flag in flags]
    return cpu, features


def _vulnerabilities() -> str:
    """How many of the kernel's listed CPU flaws are open (not mitigated) on this CPU."""
    base = "/sys/devices/system/cpu/vulnerabilities"
    try:
        names = os.listdir(base)
    except OSError:
        return ""
    open_ = [n for n in names if _read(f"{base}/{n}").lower().startswith("vulnerable")]
    return f"{len(open_)} / {len(names)}" + (f" ({', '.join(sorted(open_))})" if open_ else "")


# --------------------------------------------------------------------------- the rest of the machine


def _os_release() -> dict[str, str]:
    out = {}
    for line in _read("/etc/os-release").splitlines():
        k, _, v = line.partition("=")
        out[k] = v.strip().strip('"')
    return out


def _dmi(name: str) -> str:
    v = _read(f"/sys/class/dmi/id/{name}")
    return "" if v.lower() in ("", "not specified", "to be filled by o.e.m.", "default string", "none") else v


def _disks() -> list[dict | None]:
    raw = _run("lsblk", "-J", "-b", "-d", "-o", "NAME,TYPE,SIZE,ROTA,TRAN,MODEL,VENDOR")
    rows: list[dict | None] = []
    try:
        devices = json.loads(raw).get("blockdevices", [])
    except ValueError:
        devices = []
    for d in devices:
        if d.get("type") != "disk" or str(d.get("name", "")).startswith(("loop", "ram", "zram")):
            continue
        name = str(d.get("name"))
        rota = str(d.get("rota")).lower() in ("1", "true")
        tran = (d.get("tran") or "").strip()
        kind = "NVMe SSD" if name.startswith("nvme") or tran == "nvme" else ("HDD" if rota else "SSD")
        if tran == "virtio" or name.startswith("vd"):
            kind = f"{kind} (virtio)" if not rota else "Virtual disk (virtio)"
        scheduler = re.search(r"\[(\w[\w-]*)\]", _read(f"/sys/block/{name}/queue/scheduler"))
        model = " ".join(x for x in [(d.get("vendor") or "").strip(), (d.get("model") or "").strip()] if x)
        parts = [_size(d.get("size"), binary=False), kind, model, f"scheduler {scheduler.group(1)}" if scheduler else ""]
        rows.append({"key": "disk", "label": name, "value": " · ".join(p for p in parts if p), "mono": False})
    return rows


def _root_fs() -> list[dict | None]:
    try:
        usage = psutil.disk_usage("/")
    except OSError:
        return []
    fstype, device = "", ""
    for p in psutil.disk_partitions(all=False):
        if p.mountpoint == "/":
            fstype, device = p.fstype, p.device
    return [
        _row("rootFs", " · ".join(x for x in [fstype, device] if x), True),
        _row("rootSize", _size(usage.total, binary=False)),
        _row("rootUsed", f"{_size(usage.used, binary=False)} ({usage.percent:.0f}%)"),
        _row("rootFree", _size(usage.free, binary=False)),
    ]


def _nics() -> list[dict | None]:
    rows: list[dict | None] = []
    stats = psutil.net_if_stats()
    for name, st in sorted(stats.items()):
        if name == "lo" or not st.isup or name.startswith(("docker", "veth", "br-", "tun", "wg", "hiddify")):
            continue
        driver = os.path.basename(os.path.realpath(f"/sys/class/net/{name}/device/driver")) if os.path.exists(f"/sys/class/net/{name}/device/driver") else ""
        speed = f"{st.speed / 1000:g} Gb/s" if st.speed and st.speed >= 1000 else (f"{st.speed} Mb/s" if st.speed else "")
        duplex = {psutil.NIC_DUPLEX_FULL: "full duplex", psutil.NIC_DUPLEX_HALF: "half duplex"}.get(st.duplex, "")
        queues = len([q for q in os.listdir(f"/sys/class/net/{name}/queues") if q.startswith("rx-")]) if os.path.isdir(f"/sys/class/net/{name}/queues") else 0
        parts = [speed, duplex, f"MTU {st.mtu}", driver, f"{queues} queues" if queues > 1 else ""]
        rows.append({"key": "nic", "label": name, "value": " · ".join(p for p in parts if p), "mono": False})
    return rows


def _sysctl(name: str) -> str:
    return _read("/proc/sys/" + name.replace(".", "/"))


def _static_part() -> dict:
    cpu, features = _cpu_static()
    rel = _os_release()
    uname = platform.uname()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    hugepage = re.search(r"Hugepagesize:\s*(\d+)\s*kB", _read("/proc/meminfo"))
    virt = _run("systemd-detect-virt") or ""
    container = _run("systemd-detect-virt", "--container")
    systemd = _run("systemctl", "--version").splitlines()[:1]
    maker = " ".join(x for x in [_dmi("sys_vendor"), _dmi("product_name"), _dmi("product_version")] if x)
    board = " ".join(x for x in [_dmi("board_vendor"), _dmi("board_name")] if x)
    bios = " · ".join(x for x in [_dmi("bios_vendor"), _dmi("bios_version"), _dmi("bios_date")] if x)
    return {
        "cpu": cpu,
        "features": features,
        "memory_total": mem.total,
        "sections": [
            _section("cpu", *cpu["rows"]),
            _section(
                "memory",
                _row("ramTotal", _size(mem.total)),
                _row("swapTotal", _size(swap.total) or "0"),
                _row("hugepage", f"{hugepage.group(1)} kB" if hugepage else ""),
                _row("swappiness", _sysctl("vm.swappiness")),
                _row("overcommit", _sysctl("vm.overcommit_memory")),
            ),
            _section("storage", *_disks(), *_root_fs()),
            _section(
                "system",
                _row("os", rel.get("PRETTY_NAME") or f"{uname.system} {uname.release}"),
                _row("kernel", uname.release, True),
                _row("kernelBuild", uname.version, True),
                _row("machine", uname.machine, True),
                _row("virtualization", virt if virt and virt != "none" else "none (bare metal)"),
                _row("container", container if container and container != "none" else ""),
                _row("maker", maker),
                _row("board", board),
                _row("bios", bios),
                _row("init", systemd[0] if systemd else "", True),
                _row("python", platform.python_version(), True),
            ),
            _section(
                "network",
                *_nics(),
                _row("congestion", _sysctl("net.ipv4.tcp_congestion_control"), True),
                _row("qdisc", _sysctl("net.core.default_qdisc"), True),
                _row("availableCc", _sysctl("net.ipv4.tcp_available_congestion_control"), True),
                _row("tcpFastOpen", _sysctl("net.ipv4.tcp_fastopen"), True),
                _row("ipForward", _sysctl("net.ipv4.ip_forward"), True),
                _row("ipv6Disabled", _sysctl("net.ipv6.conf.all.disable_ipv6"), True),
                _row("somaxconn", _sysctl("net.core.somaxconn"), True),
                _row("rmemMax", _size(_int(_sysctl("net.core.rmem_max")))),
                _row("wmemMax", _size(_int(_sysctl("net.core.wmem_max")))),
                _row("conntrackMax", _sysctl("net.netfilter.nf_conntrack_max"), True),
                _row("fileMax", _sysctl("fs.file-max"), True),
            ),
        ],
    }


def collect() -> dict:
    """This server's specs: the parts that do not change (kept a while) and the live ones (read now)."""
    global _static
    now = time.time()
    if _static is None or now - _static[0] > _STATIC_SECONDS:
        _static = (now, _static_part())
    static = _static[1]
    freq = psutil.cpu_freq()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
    boot = psutil.boot_time()
    cur_mhz = freq.current if freq else 0
    live = _section(
        "live",
        _row("curClock", _mhz(cur_mhz)),
        _row("cpuUse", f"{psutil.cpu_percent(interval=0.3):.0f}%"),
        _row("load", " · ".join(f"{x:.2f}" for x in load), True),
        _row("ramUsed", f"{_size(mem.total - mem.available)} / {_size(mem.total)} ({mem.percent:.0f}%)"),
        _row("swapUsed", f"{_size(swap.used) or '0'} ({swap.percent:.0f}%)" if swap.total else ""),
        _row("processes", len(psutil.pids())),
        _row("uptime", _duration(now - boot)),
        _row("bootTime", time.strftime("%Y-%m-%d %H:%M", time.localtime(boot)), True),
        _row("timezone", time.strftime("%Z (UTC%z)"), True),
    )
    cpu = static["cpu"]
    return {
        "ok": True,
        "summary": {
            "name": cpu["name"],
            "vendor": cpu["vendor"],
            "microarch": cpu["microarch"],
            "generation": cpu["generation"],
            "virtual": cpu["virtual"],
            "cores": cpu["cores"],
            "threads": cpu["threads"],
            "sockets": cpu["sockets"],
            "max_clock": _mhz(cpu["max_mhz"] or cpu["base_mhz"] or cur_mhz),
            "ram": _size(static["memory_total"]),
            "disk": _size(psutil.disk_usage("/").total, binary=False),
            "uptime": _duration(now - boot),
        },
        "features": static["features"],
        "sections": [live, *static["sections"]],
        "collected_at": int(now),
    }
