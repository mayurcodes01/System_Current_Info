"""
FullInfo.py

Comprehensive system information inspector with a GUI (CustomTkinter preferred).
- Shows OS, CPU, memory, disk, network, GPU, uptime, and top processes.
- Refresh button to update info.
- Export to text file (report).
"""

import threading
import time
import os
import platform
import sys
import socket
import uuid
import getpass
from datetime import datetime, timedelta

try:
    import psutil
except Exception:
    psutil = None

try:
    import cpuinfo
except Exception:
    cpuinfo = None

try:
    import GPUtil
except Exception:
    GPUtil = None

try:
    import customtkinter as ctk
    from tkinter import scrolledtext, filedialog, messagebox
    UI_FRAMEWORK = "custom"
except Exception:
    import tkinter as tk
    from tkinter import scrolledtext, filedialog, messagebox
    UI_FRAMEWORK = "tk"

def format_bytes(n):
    for unit in ['B','KB','MB','GB','TB','PB']:
        if abs(n) < 1024.0:
            return f"{n:3.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} PB"

def get_basic_info():
    info = {}
    info['username'] = getpass.getuser()
    info['hostname'] = socket.gethostname()
    try:
        info['fqdn'] = socket.getfqdn()
    except Exception:
        info['fqdn'] = "N/A"
    info['platform'] = platform.system()
    info['platform_release'] = platform.release()
    info['platform_version'] = platform.version()
    info['architecture'] = platform.machine()
    info['processor'] = platform.processor() or ("N/A" if not cpuinfo else cpuinfo.get_cpu_info().get('brand_raw','N/A'))
    info['python_version'] = sys.version.replace('\n',' ')
    info['boot_time'] = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S") if psutil else "N/A"
    return info

def get_uptime():
    if not psutil:
        return "N/A"
    boot = datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.now() - boot
    return str(delta).split('.')[0]  

def get_cpu_info():
    out = {}
    if cpuinfo:
        try:
            ci = cpuinfo.get_cpu_info()
            out['brand'] = ci.get('brand_raw','N/A')
            out['arch'] = ci.get('arch','N/A')
            out['bits'] = ci.get('bits','N/A')
            out['count_logical'] = psutil.cpu_count(logical=True) if psutil else "N/A"
            out['count_physical'] = psutil.cpu_count(logical=False) if psutil else "N/A"
        except Exception:
            out['brand'] = platform.processor()
    else:
        out['brand'] = platform.processor() or "N/A"
        out['count_logical'] = psutil.cpu_count(logical=True) if psutil else "N/A"
        out['count_physical'] = psutil.cpu_count(logical=False) if psutil else "N/A"

    if psutil:
        try:
            out['freq'] = psutil.cpu_freq().max if psutil.cpu_freq() else "N/A"
            out['usage_per_core'] = psutil.cpu_percent(interval=0.5, percpu=True)
            out['total_cpu_percent'] = psutil.cpu_percent(interval=0.1)
        except Exception:
            out['usage_per_core'] = []
            out['total_cpu_percent'] = "N/A"
    return out

def get_memory_info():
    if not psutil:
        return {}
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    return {
        "total": format_bytes(vm.total),
        "available": format_bytes(vm.available),
        "used": format_bytes(vm.used),
        "percent": f"{vm.percent}%",
        "swap_total": format_bytes(sm.total),
        "swap_used": format_bytes(sm.used),
        "swap_percent": f"{sm.percent}%"
    }

def get_disk_info():
    if not psutil:
        return {}
    parts = []
    for p in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(p.mountpoint)
            parts.append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "opts": p.opts,
                "total": format_bytes(usage.total),
                "used": format_bytes(usage.used),
                "free": format_bytes(usage.free),
                "percent": f"{usage.percent}%"
            })
        except PermissionError:
            parts.append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "opts": p.opts,
                "total": "Permission denied",
                "used": "Permission denied",
                "free": "Permission denied",
                "percent": "N/A"
            })
    disk_io = psutil.disk_io_counters() if psutil else None
    return {"partitions": parts, "disk_io": disk_io}

def get_network_info():
    net = {}
    try:
        hostname = socket.gethostname()
        net['hostname'] = hostname
        net['local_ip'] = socket.gethostbyname(hostname)
    except Exception:
        net['local_ip'] = "N/A"

    if psutil:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        nic_info = {}
        for nic, addr_list in addrs.items():
            nic_info[nic] = {"addresses": [], "isup": stats.get(nic).isup if nic in stats else "N/A"}
            for a in addr_list:
                nic_info[nic]["addresses"].append({
                    "family": str(a.family),
                    "address": a.address,
                    "netmask": a.netmask,
                    "broadcast": a.broadcast
                })
        net['nics'] = nic_info
        try:
            net_io = psutil.net_io_counters(pernic=False)
            net['bytes_sent'] = format_bytes(net_io.bytes_sent)
            net['bytes_recv'] = format_bytes(net_io.bytes_recv)
        except Exception:
            pass
    return net

def get_gpu_info():
    info = []
    if GPUtil:
        try:
            gpus = GPUtil.getGPUs()
            for g in gpus:
                info.append({
                    "id": g.id,
                    "name": g.name,
                    "load": f"{g.load*100:.1f}%",
                    "memory_total": f"{g.memoryTotal}MB",
                    "memory_used": f"{g.memoryUsed}MB",
                    "temperature": f"{g.temperature} °C"
                })
        except Exception:
            pass
    return info

def get_top_processes(limit=8):
    result = []
    if not psutil:
        return result
    try:
        procs = []
        for p in psutil.process_iter(['pid','name','username','cpu_percent','memory_percent']):
            procs.append(p.info)
        procs_sorted = sorted(procs, key=lambda p: (p.get('cpu_percent',0) or 0), reverse=True)
        for p in procs_sorted[:limit]:
            result.append(p)
    except Exception:
        pass
    return result

def gather_all_info():
    """Collect everything in a dict."""
    data = {}
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data['basic'] = get_basic_info()
    data['uptime'] = get_uptime()
    data['cpu'] = get_cpu_info()
    data['memory'] = get_memory_info()
    data['disk'] = get_disk_info()
    data['network'] = get_network_info()
    data['gpu'] = get_gpu_info()
    data['top_processes'] = get_top_processes()
    return data

def pretty_print(info_dict):
    """Turn gathered info into a nicely formatted string report."""
    lines = []
    append = lines.append
    append(f"SYSTEM REPORT - Generated: {info_dict.get('timestamp','N/A')}")
    append("="*80)
    b = info_dict.get('basic',{})
    append("Basic Info:")
    append(f"  User: {b.get('username','N/A')}")
    append(f"  Hostname: {b.get('hostname','N/A')} (FQDN: {b.get('fqdn','N/A')})")
    append(f"  Platform: {b.get('platform','N/A')} {b.get('platform_release','')} {b.get('platform_version','')}")
    append(f"  Architecture: {b.get('architecture','N/A')}")
    append(f"  Processor: {b.get('processor','N/A')}")
    append(f"  Python: {b.get('python_version','N/A')}")
    append(f"  Boot Time: {b.get('boot_time','N/A')} (Uptime: {info_dict.get('uptime','N/A')})")
    append("")

    append("CPU:")
    cpu = info_dict.get('cpu',{})
    append(f"  Brand: {cpu.get('brand','N/A')}")
    append(f"  Logical cores: {cpu.get('count_logical','N/A')}, Physical cores: {cpu.get('count_physical','N/A')}")
    append(f"  Frequency (max MHz): {cpu.get('freq','N/A')}")
    append(f"  Total CPU%: {cpu.get('total_cpu_percent','N/A')}")
    if cpu.get('usage_per_core'):
        append(f"  Per-core usage: {', '.join(f'{u}%' for u in cpu['usage_per_core'])}")
    append("")

    append("Memory:")
    mem = info_dict.get('memory',{})
    for k,v in mem.items():
        append(f"  {k.replace('_',' ').title()}: {v}")
    append("")

    append("Disk Partitions:")
    for p in info_dict.get('disk',{}).get('partitions',[]):
        append(f"  Device: {p['device']} Mount: {p['mountpoint']} Type: {p['fstype']}")
        append(f"    Total: {p['total']} Used: {p['used']} Free: {p['free']} Usage: {p['percent']}")
    append("")

    append("Network:")
    net = info_dict.get('network',{})
    append(f"  Local IP: {net.get('local_ip','N/A')} Hostname: {net.get('hostname','N/A')}")
    nics = net.get('nics',{})
    for nic, nd in nics.items():
        append(f"  NIC: {nic} Up: {nd.get('isup')}")
        for a in nd.get('addresses',[]):
            append(f"    {a.get('family')}: {a.get('address')} Netmask: {a.get('netmask')} Broadcast: {a.get('broadcast')}")
    append(f"  Bytes Sent: {net.get('bytes_sent','N/A')} Bytes Recv: {net.get('bytes_recv','N/A')}")
    append("")

    append("GPU(s):")
    gpus = info_dict.get('gpu',[])
    if not gpus:
        append("  No GPU info or GPUtil not installed.")
    else:
        for g in gpus:
            append(f"  {g['name']} (id={g['id']}) Load: {g['load']} Mem: {g['memory_used']}/{g['memory_total']} Temp: {g['temperature']}")
    append("")

    append("Top Processes (by CPU):")
    for p in info_dict.get('top_processes',[]):
        append(f"  PID {p.get('pid')} {p.get('name')} user={p.get('username')} CPU%={p.get('cpu_percent')} MEM%={p.get('memory_percent')}")
    append("="*80)
    return "\n".join(lines)

class SystemInfoGUI:
    def __init__(self, root):
        self.root = root
        self.data_text_widget = None
        self.status_var = None
        self._setup_ui()
        self.refresh_info_async()

    def _setup_ui(self):
        if UI_FRAMEWORK == "custom":
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")
            self.root.geometry("1000x720")
            self.root.title("FullInfo by Mayur Dhole.")
            top = ctk.CTkFrame(self.root, corner_radius=8)
            top.pack(fill="x", padx=12, pady=12)
            title = ctk.CTkLabel(top, text="Full system info.", font=("Helvetica", 20, "bold"))
            title.pack(side="left", padx=12, pady=8)
            btn_refresh = ctk.CTkButton(top, text="Refresh", command=self.refresh_info_async)
            btn_refresh.pack(side="right", padx=8)
            btn_export = ctk.CTkButton(top, text="Export Report", command=self.export_report)
            btn_export.pack(side="right", padx=8)

            self.status_var = ctk.StringVar(value="Ready")
            status_lbl = ctk.CTkLabel(self.root, textvariable=self.status_var, anchor="w", fg_color=None)
            status_lbl.pack(fill="x", padx=12)

            self.data_text_widget = scrolledtext.ScrolledText(self.root, width=120, height=36, font=("Consolas",10))
            self.data_text_widget.pack(padx=12, pady=12, fill="both", expand=True)
            self.data_text_widget.configure(state='disabled')
        else:
            self.root.geometry("1000x720")
            self.root.title("FullInfo by Mayur Dhole.")
            frame = tk.Frame(self.root)
            frame.pack(fill="x", padx=10, pady=10)
            title = tk.Label(frame, text="FullInfo", font=("Helvetica", 20, "bold"))
            title.pack(side="left")
            btn_refresh = tk.Button(frame, text="Refresh", command=self.refresh_info_async)
            btn_refresh.pack(side="right", padx=6)
            btn_export = tk.Button(frame, text="Export Report", command=self.export_report)
            btn_export.pack(side="right", padx=6)

            self.status_var = tk.StringVar(value="Ready")
            status_lbl = tk.Label(self.root, textvariable=self.status_var, anchor="w")
            status_lbl.pack(fill="x", padx=12)

            self.data_text_widget = scrolledtext.ScrolledText(self.root, width=120, height=36, font=("Consolas",10))
            self.data_text_widget.pack(padx=12, pady=12, fill="both", expand=True)
            self.data_text_widget.configure(state='disabled')

    def refresh_info_async(self):
        t = threading.Thread(target=self._refresh_info)
        t.daemon = True
        t.start()

    def _refresh_info(self):
        try:
            self._set_status("Collecting system information...")
            info = gather_all_info()
            text = pretty_print(info)
            self._set_text(text)
            self._set_status(f"Last updated: {info.get('timestamp')}")
            self.latest_report = text
        except Exception as e:
            self._set_status(f"Error: {e}")

    def _set_text(self, txt):
        self.data_text_widget.configure(state='normal')
        self.data_text_widget.delete('1.0', 'end')
        self.data_text_widget.insert('1.0', txt)
        self.data_text_widget.configure(state='disabled')

    def _set_status(self, s):
        try:
            if UI_FRAMEWORK == "custom":
                self.status_var.set(s)
            else:
                self.status_var.set(s)
        except Exception:
            pass

    def export_report(self):
        try:
            default_name = f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=default_name,
                                                filetypes=[("Text files","*.txt"),("All files","*.*")])
            if not file:
                return
            if not hasattr(self, 'latest_report') or not self.latest_report:
                info = gather_all_info()
                self.latest_report = pretty_print(info)
            with open(file, 'w', encoding='utf-8') as f:
                f.write(self.latest_report)
            messagebox.showinfo("Exported", f"Report saved to: {file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

if __name__ == "__main__":
    if UI_FRAMEWORK == "custom":
        root = ctk.CTk()
    else:
        root = tk.Tk()
    app = SystemInfoGUI(root)
    root.mainloop()
