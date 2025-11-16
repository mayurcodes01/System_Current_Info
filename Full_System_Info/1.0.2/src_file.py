"""
FullInfo.py

Modern dark dashboard UI for system inspection using CustomTkinter (preferred) with Tkinter fallback.
Features:
- Sidebar navigation and cards for quick stats
- Tabbed/stacked main area for detailed text report and charts
- Matplotlib charts for CPU and memory
- Refresh button (async) and Export report
- Auto-detects optional libs: psutil, cpuinfo, GPUtil, customtkinter, matplotlib

Run: pip install psutil py-cpuinfo gputil customtkinter matplotlib

Author: Mayur
"""

import threading
import time
import os
import platform
import sys
import socket
import getpass
from datetime import datetime

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

USE_CUSTOM = True
try:
    import customtkinter as ctk
    from tkinter import scrolledtext, filedialog, messagebox
except Exception:
    USE_CUSTOM = False
    import tkinter as ctk  
    from tkinter import scrolledtext, filedialog, messagebox

try:
    import matplotlib
    matplotlib.use('Agg')  
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except Exception:
    HAS_MPL = False

def format_bytes(n):
    try:
        n = float(n)
    except Exception:
        return str(n)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(n) < 1024.0:
            return f"{n:3.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} PB"


def get_basic_info():
    b = {}
    b['user'] = getpass.getuser()
    b['hostname'] = socket.gethostname()
    b['platform'] = platform.system()
    b['release'] = platform.release()
    b['version'] = platform.version()
    b['arch'] = platform.machine()
    b['python'] = sys.version.replace('\n',' ')
    try:
        b['processor'] = (cpuinfo.get_cpu_info().get('brand_raw') if cpuinfo else platform.processor()) or 'N/A'
    except Exception:
        b['processor'] = platform.processor() or 'N/A'
    try:
        b['boot_time'] = datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S') if psutil else 'N/A'
    except Exception:
        b['boot_time'] = 'N/A'
    return b


def get_uptime():
    if not psutil:
        return 'N/A'
    try:
        boot = datetime.fromtimestamp(psutil.boot_time())
        return str(datetime.now() - boot).split('.')[0]
    except Exception:
        return 'N/A'


def get_cpu():
    out = {}
    try:
        out['logical'] = psutil.cpu_count(logical=True) if psutil else 'N/A'
        out['physical'] = psutil.cpu_count(logical=False) if psutil else 'N/A'
        out['freq'] = psutil.cpu_freq().max if psutil and psutil.cpu_freq() else 'N/A'
        out['total_percent'] = psutil.cpu_percent(interval=0.1) if psutil else 'N/A'
        out['per_core'] = psutil.cpu_percent(interval=0.1, percpu=True) if psutil else []
    except Exception:
        out['per_core'] = []
    return out


def get_memory():
    if not psutil:
        return {}
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    return {
        'total': format_bytes(vm.total),
        'used': format_bytes(vm.used),
        'available': format_bytes(vm.available),
        'percent': f"{vm.percent}%",
        'swap_total': format_bytes(sm.total),
        'swap_used': format_bytes(sm.used),
        'swap_percent': f"{sm.percent}%"
    }


def get_disks():
    if not psutil:
        return []
    parts = []
    for p in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(p.mountpoint)
            parts.append({'device': p.device, 'mount': p.mountpoint, 'fstype': p.fstype,
                          'total': format_bytes(u.total), 'used': format_bytes(u.used), 'free': format_bytes(u.free), 'percent': f"{u.percent}%"})
        except PermissionError:
            parts.append({'device': p.device, 'mount': p.mountpoint, 'fstype': p.fstype, 'total': 'Denied'})
    return parts


def get_network():
    net = {}
    try:
        net['local_ip'] = socket.gethostbyname(socket.gethostname())
    except Exception:
        net['local_ip'] = 'N/A'
    if psutil:
        try:
            ni = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            net['nics'] = {}
            for name, addrs in ni.items():
                net['nics'][name] = {'isup': stats[name].isup if name in stats else 'N/A', 'addrs': []}
                for a in addrs:
                    net['nics'][name]['addrs'].append({'addr': a.address, 'netmask': a.netmask})
            io = psutil.net_io_counters()
            net['bytes_sent'] = format_bytes(io.bytes_sent)
            net['bytes_recv'] = format_bytes(io.bytes_recv)
        except Exception:
            pass
    return net


def get_gpu():
    out = []
    if GPUtil:
        try:
            for g in GPUtil.getGPUs():
                out.append({'name': g.name, 'load': f"{g.load*100:.1f}%", 'mem_used': f"{g.memoryUsed}MB", 'mem_total': f"{g.memoryTotal}MB"})
        except Exception:
            pass
    return out


def get_top_processes(limit=8):
    res = []
    if not psutil:
        return res
    try:
        procs = []
        for p in psutil.process_iter(['pid','name','username','cpu_percent','memory_percent']):
            procs.append(p.info)
        for p in sorted(procs, key=lambda x: x.get('cpu_percent') or 0, reverse=True)[:limit]:
            res.append(p)
    except Exception:
        pass
    return res


def gather_all():
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'basic': get_basic_info(),
        'uptime': get_uptime(),
        'cpu': get_cpu(),
        'memory': get_memory(),
        'disks': get_disks(),
        'network': get_network(),
        'gpu': get_gpu(),
        'top': get_top_processes()
    }


def pretty_report(data):
    lines = []
    lines.append(f"SYSTEM REPORT - {data.get('timestamp')}")
    lines.append('-'*60)
    b = data.get('basic', {})
    lines.append(f"User: {b.get('user')}@{b.get('hostname')}")
    lines.append(f"Platform: {b.get('platform')} {b.get('release')} {b.get('arch')}")
    lines.append(f"Processor: {b.get('processor')}")
    lines.append(f"Python: {b.get('python')}")
    lines.append(f"Boot: {b.get('boot_time')} Uptime: {data.get('uptime')}")
    lines.append('\nCPU:')
    c = data.get('cpu', {})
    lines.append(f"  Cores: {c.get('logical')}(logical)/{c.get('physical')}(physical)  Total%: {c.get('total_percent')}")
    lines.append('\nMemory:')
    m = data.get('memory', {})
    for k, v in m.items():
        lines.append(f"  {k}: {v}")
    lines.append('\nDisks:')
    for d in data.get('disks', []):
        lines.append(f"  {d.get('device')} mounted on {d.get('mount')} {d.get('total')} ({d.get('percent','')})")
    lines.append('\nTop processes:')
    for p in data.get('top', []):
        lines.append(f"  PID {p.get('pid')} {p.get('name')} CPU%={p.get('cpu_percent')} MEM%={p.get('memory_percent')}")
    return '\n'.join(lines)


class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title('FullInfo - Mayur Dhole')
        self.latest_text = ''
        self.cpu_history = []
        self.mem_history = []
        self._build_ui()
        self.refresh_async()

    def _build_ui(self):
        if USE_CUSTOM and ctk.__name__ == 'customtkinter':
            ctk.set_appearance_mode('dark')
            ctk.set_default_color_theme('dark-blue')

        self.root.geometry('1100x700')
        if USE_CUSTOM and ctk.__name__ == 'customtkinter':
            container = ctk.CTkFrame(self.root)
            container.pack(fill='both', expand=True)
            sidebar = ctk.CTkFrame(container, width=220)
            sidebar.pack(side='left', fill='y', padx=8, pady=8)
            main = ctk.CTkFrame(container)
            main.pack(side='left', fill='both', expand=True, padx=8, pady=8)
        else:
            container = ctk.Frame(self.root)
            container.pack(fill='both', expand=True)
            sidebar = ctk.Frame(container, width=220, bg='#2b2b2b')
            sidebar.pack(side='left', fill='y', padx=8, pady=8)
            main = ctk.Frame(container, bg='#1e1e1e')
            main.pack(side='left', fill='both', expand=True, padx=8, pady=8)

        if USE_CUSTOM and ctk.__name__ == 'customtkinter':
            title = ctk.CTkLabel(sidebar, text='FullInfo', font=('Helvetica', 18, 'bold'))
            title.pack(pady=(6,12))
            self.lbl_user = ctk.CTkLabel(sidebar, text='User: -')
            self.lbl_user.pack(anchor='w', padx=12)
            self.lbl_host = ctk.CTkLabel(sidebar, text='Host: -')
            self.lbl_host.pack(anchor='w', padx=12)
            sep = ctk.CTkLabel(sidebar, text='')
            sep.pack(pady=6)
            btn_refresh = ctk.CTkButton(sidebar, text='Refresh', command=self.refresh_async)
            btn_refresh.pack(fill='x', padx=12, pady=6)
            btn_export = ctk.CTkButton(sidebar, text='Export Report', command=self.export_report)
            btn_export.pack(fill='x', padx=12)
        else:
            title = ctk.Label(sidebar, text='FullInfo', font=('Helvetica', 16), bg=sidebar['bg'], fg='white')
            title.pack(pady=(6,12))
            self.lbl_user = ctk.Label(sidebar, text='User: -', bg=sidebar['bg'], fg='white')
            self.lbl_user.pack(anchor='w', padx=8)
            self.lbl_host = ctk.Label(sidebar, text='Host: -', bg=sidebar['bg'], fg='white')
            self.lbl_host.pack(anchor='w', padx=8)
            btn_refresh = ctk.Button(sidebar, text='Refresh', command=self.refresh_async)
            btn_refresh.pack(fill='x', padx=8, pady=8)
            btn_export = ctk.Button(sidebar, text='Export Report', command=self.export_report)
            btn_export.pack(fill='x', padx=8)

        cards_frame = ctk.Frame(main) if not (USE_CUSTOM and ctk.__name__ == 'customtkinter') else ctk.CTkFrame(main)
        cards_frame.pack(fill='x')

        def make_card(parent, title):
            if USE_CUSTOM and ctk.__name__ == 'customtkinter':
                f = ctk.CTkFrame(parent, corner_radius=8)
                lbl_title = ctk.CTkLabel(f, text=title, font=('Helvetica', 12, 'bold'))
                lbl_title.pack(anchor='w', padx=8, pady=(6,0))
                lbl_val = ctk.CTkLabel(f, text='-', font=('Consolas', 12))
                lbl_val.pack(anchor='w', padx=8, pady=(2,8))
            else:
                f = ctk.Frame(parent, bg=parent['bg'], bd=1, relief='flat')
                lbl_title = ctk.Label(f, text=title, font=('Helvetica', 11, 'bold'), bg=parent['bg'], fg='white')
                lbl_title.pack(anchor='w', padx=6, pady=(6,0))
                lbl_val = ctk.Label(f, text='-', font=('Consolas', 11), bg=parent['bg'], fg='white')
                lbl_val.pack(anchor='w', padx=6, pady=(2,6))
            return f, lbl_val

        self.card_cpu, self.card_cpu_val = make_card(cards_frame, 'CPU')
        self.card_mem, self.card_mem_val = make_card(cards_frame, 'Memory')
        self.card_disk, self.card_disk_val = make_card(cards_frame, 'Disk')
        self.card_net, self.card_net_val = make_card(cards_frame, 'Network')

        for w in [self.card_cpu, self.card_mem, self.card_disk, self.card_net]:
            w.pack(side='left', expand=True, fill='both', padx=6, pady=6)

        lower = ctk.Frame(main) if not (USE_CUSTOM and ctk.__name__ == 'customtkinter') else ctk.CTkFrame(main)
        lower.pack(fill='both', expand=True, pady=(8,0))

        left_pane = ctk.Frame(lower, bg=lower['bg']) if not (USE_CUSTOM and ctk.__name__ == 'customtkinter') else ctk.CTkFrame(lower)
        left_pane.pack(side='left', fill='both', expand=True, padx=6)
        right_pane = ctk.Frame(lower, bg=lower['bg']) if not (USE_CUSTOM and ctk.__name__ == 'customtkinter') else ctk.CTkFrame(lower)
        right_pane.pack(side='left', fill='both', expand=True, padx=6)

        if HAS_MPL:
            self.fig_cpu = Figure(figsize=(4,2.5), dpi=100)
            self.ax_cpu = self.fig_cpu.add_subplot(111)
            self.ax_cpu.set_title('CPU (%) — last samples')
            self.ax_cpu.set_ylim(0, 100)

            self.fig_mem = Figure(figsize=(4,2.5), dpi=100)
            self.ax_mem = self.fig_mem.add_subplot(111)
            self.ax_mem.set_title('Memory (%) — last samples')
            self.ax_mem.set_ylim(0, 100)

            self.canvas_cpu = FigureCanvasTkAgg(self.fig_cpu, master=left_pane)
            self.canvas_cpu.get_tk_widget().pack(fill='both', expand=True, padx=6, pady=6)
            self.canvas_mem = FigureCanvasTkAgg(self.fig_mem, master=left_pane)
            self.canvas_mem.get_tk_widget().pack(fill='both', expand=True, padx=6, pady=6)
        else:
            lbl_no_mpl = ctk.Label(left_pane, text='Matplotlib not installed — charts unavailable', bg=left_pane['bg'] if not (USE_CUSTOM and ctk.__name__ == 'customtkinter') else None, fg='white') if not (USE_CUSTOM and ctk.__name__ == 'customtkinter') else ctk.CTkLabel(left_pane, text='Matplotlib not installed — charts unavailable')
            lbl_no_mpl.pack(padx=6, pady=6)

        self.text_report = scrolledtext.ScrolledText(right_pane, wrap='word', font=('Consolas', 10), width=60)
        self.text_report.pack(fill='both', expand=True, padx=6, pady=6)
        self.text_report.configure(state='disabled')

        self.status_var = ctk.StringVar() if (USE_CUSTOM and ctk.__name__ == 'customtkinter') else ctk.StringVar()
        status_lbl = ctk.Label(self.root, textvariable=self.status_var, anchor='w') if not (USE_CUSTOM and ctk.__name__ == 'customtkinter') else ctk.CTkLabel(self.root, textvariable=self.status_var)
        status_lbl.pack(fill='x')

    def refresh_async(self):
        t = threading.Thread(target=self._refresh)
        t.daemon = True
        t.start()

    def _refresh(self):
        try:
            self._set_status('Collecting system information...')
            data = gather_all()
            self.latest_text = pretty_report(data)
            b = data.get('basic', {})
            self._set_label(self.lbl_user, f"User: {b.get('user')}")
            self._set_label(self.lbl_host, f"Host: {b.get('hostname')}")

            cpu = data.get('cpu', {})
            mem = data.get('memory', {})
            disks = data.get('disks', [])
            net = data.get('network', {})

            self._set_label(self.card_cpu_val, f"{cpu.get('total_percent')}% ({cpu.get('logical')}c)")
            self._set_label(self.card_mem_val, f"{mem.get('percent','-')} — {mem.get('used','-')}/{mem.get('total','-')}")
            if disks:
                d = disks[0]
                self._set_label(self.card_disk_val, f"{d.get('device')} {d.get('used','-')}/{d.get('total','-')}")
            else:
                self._set_label(self.card_disk_val, 'No disk info')
            self._set_label(self.card_net_val, f"IP: {net.get('local_ip','-')}")

            self._set_report(self.latest_text)
            try:
                if psutil:
                    cpu_pct = psutil.cpu_percent(interval=0.1)
                    mem_pct = psutil.virtual_memory().percent
                else:
                    cpu_pct = 0
                    mem_pct = 0
                self.cpu_history.append(cpu_pct)
                self.mem_history.append(mem_pct)
                self.cpu_history = self.cpu_history[-30:]
                self.mem_history = self.mem_history[-30:]
                if HAS_MPL:
                    self.ax_cpu.clear(); self.ax_cpu.plot(self.cpu_history); self.ax_cpu.set_ylim(0,100); self.ax_cpu.set_title('CPU (%) — last samples')
                    self.canvas_cpu.draw_idle()
                    self.ax_mem.clear(); self.ax_mem.plot(self.mem_history); self.ax_mem.set_ylim(0,100); self.ax_mem.set_title('Memory (%) — last samples')
                    self.canvas_mem.draw_idle()
            except Exception:
                pass

            self._set_status(f'Last updated: {data.get("timestamp")}')
        except Exception as e:
            self._set_status(f'Error: {e}')

    def _set_label(self, widget, text):
        try:
            if hasattr(widget, 'configure'):
                widget.configure(text=text)
            else:
                widget.set(text)
        except Exception:
            try:
                widget.set(text)
            except Exception:
                pass

    def _set_report(self, text):
        try:
            self.text_report.configure(state='normal')
            self.text_report.delete('1.0', 'end')
            self.text_report.insert('1.0', text)
            self.text_report.configure(state='disabled')
        except Exception:
            pass

    def _set_status(self, s):
        try:
            self.status_var.set(s)
        except Exception:
            try:
                if USE_CUSTOM and ctk.__name__ == 'customtkinter':
                    pass
            except Exception:
                pass

    def export_report(self):
        try:
            fname = f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file = filedialog.asksaveasfilename(defaultextension='.txt', initialfile=fname, filetypes=[('Text files','*.txt'),('All','*.*')])
            if not file:
                return
            if not self.latest_text:
                data = gather_all(); self.latest_text = pretty_report(data)
            with open(file, 'w', encoding='utf-8') as f:
                f.write(self.latest_text)
            messagebox.showinfo('Exported', f'Report saved: {file}')
        except Exception as e:
            messagebox.showerror('Error', f'Export failed: {e}')

if __name__ == '__main__':
    if USE_CUSTOM and ctk.__name__ == 'customtkinter':
        root = ctk.CTk()
    else:
        root = ctk.Tk()
    app = DashboardApp(root)
    def periodic_refresh():
        while True:
            time.sleep(8)
            try:
                app.refresh_async()
            except Exception:
                pass
    t = threading.Thread(target=periodic_refresh, daemon=True)
    t.start()
    root.mainloop()
