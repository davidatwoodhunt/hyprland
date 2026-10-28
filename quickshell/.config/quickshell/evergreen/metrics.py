#!/usr/bin/env python3
"""Read-only Linux telemetry: one JSON sample every two seconds, no dependencies."""
import collections
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

PROC = Path('/proc')
SYS = Path('/sys')
INTERVAL = 2.0
TICKS = os.sysconf('SC_CLK_TCK')
PAGE = os.sysconf('SC_PAGE_SIZE')


def read(path):
    return Path(path).read_text().strip()


def cpu_times():
    result = {}
    for line in read(PROC / 'stat').splitlines():
        name, *values = line.split()
        if name == 'cpu' or (name.startswith('cpu') and name[3:].isdigit()):
            v = [int(x) for x in values[:8]]  # guest time is already included in user/nice
            result[name] = (sum(v), v[3] + v[4])
    return result


def temperature():
    for hw in (SYS / 'class/hwmon').glob('hwmon*'):
        try:
            if read(hw / 'name') == 'k10temp':
                for label in hw.glob('temp*_label'):
                    if read(label) == 'Tctl':
                        return int(read(label.with_name(label.name.replace('_label', '_input')))) / 1000
        except (OSError, ValueError):
            continue
    return None


def processes():
    result = {}
    for directory in PROC.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            stat = read(directory / 'stat')
            end = stat.rfind(')')
            fields = stat[end + 2:].split()
            name = stat[stat.index('(') + 1:end]
            # Fields start at stat field 3; starttime guards against reused PIDs.
            result[(int(directory.name), int(fields[19]))] = (
                name, int(fields[11]) + int(fields[12]), max(0, int(fields[21])) * PAGE)
        except (OSError, ValueError, IndexError):
            continue  # exiting or inaccessible process
    return result


def network():
    counters = {}
    for line in read(PROC / 'net/dev').splitlines()[2:]:
        name, values = line.split(':', 1)
        v = values.split()
        if name.strip() != 'lo':
            counters[name.strip()] = (int(v[0]), int(v[8]))
    preferred = []
    for line in read(PROC / 'net/route').splitlines()[1:]:
        v = line.split()
        if v[1] == '00000000' and int(v[3], 16) & 1:
            preferred.append((int(v[6]), v[0]))
    # Include IPv6-only connections; prefer a default route over an idle device.
    for line in read(PROC / 'net/ipv6_route').splitlines():
        v = line.split()
        if v[0] == '0' * 32 and v[1] == '00' and v[-1] != 'lo':
            preferred.append((int(v[5], 16), v[-1]))
    active = []
    for name in counters:
        try:
            if read(SYS / 'class/net' / name / 'operstate') == 'up':
                active.append(name)
        except OSError:
            pass
    iface = next((name for _, name in sorted(preferred) if name in active), next(iter(active), ''))
    return counters, iface, bool(preferred and iface in [name for _, name in preferred])


def gpu():
    try:
        proc = subprocess.run([
            'nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total,power.draw',
            '--format=csv,noheader,nounits', '-i', '0'], capture_output=True, text=True, timeout=1.5, check=True)
        fields = proc.stdout.splitlines()[0].split(',')
        values = []
        for field in fields:
            try:
                values.append(float(field.strip()))
            except ValueError:
                values.append(None)
        return dict(zip(('usage', 'temperature', 'used', 'total', 'power'), values))
    except (OSError, subprocess.SubprocessError, IndexError):
        return {}  # explicit unavailable state, not a fabricated zero


def root_device():
    try:
        device = subprocess.check_output(['findmnt', '-n', '-o', 'MAJ:MIN', '/'], text=True).strip()
        path = (SYS / 'dev/block' / device).resolve()
        if (path / 'partition').exists():
            path = path.parent
        if (path / 'stat').exists():
            return path / 'stat'
        # btrfs reports a virtual MAJ:MIN; find its mounted backing device.
        source = subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE', '/'], text=True).strip().split('[')[0]
        path = SYS / 'class/block' / Path(source).resolve().name
        if (path / 'stat').exists():
            return path / 'stat'
    except (OSError, subprocess.SubprocessError):
        pass
    return None  # btrfs/multi-device roots may have no single block-device counter


class Sampler:
    def __init__(self):
        self.cpu = cpu_times()
        self.proc = processes()
        self.net, _, _ = network()
        self.when = time.monotonic()
        self.disk_path = root_device()
        self.disk = self.disk_stat()
        self.history = {key: collections.deque(maxlen=40) for key in ('cpu', 'gpu', 'download', 'upload')}

    def disk_stat(self):
        try:
            v = [int(x) for x in read(self.disk_path).split()]
            return v[2] * 512, v[6] * 512
        except (OSError, TypeError, ValueError):
            return None

    def sample(self):
        now = time.monotonic()
        elapsed = max(0.001, now - self.when)
        current = cpu_times()
        usage = {}
        for name, (total, idle) in current.items():
            old_total, old_idle = self.cpu.get(name, (total, idle))
            delta = total - old_total
            usage[name] = max(0, min(100, 100 * (1 - (idle - old_idle) / delta))) if delta > 0 else 0
        frequencies = [float(line.split(':')[1]) for line in read(PROC / 'cpuinfo').splitlines() if line.startswith('cpu MHz')]
        memory = {line.split(':')[0]: int(line.split()[1]) * 1024 for line in read(PROC / 'meminfo').splitlines() if len(line.split()) >= 3}
        memory_used = memory['MemTotal'] - memory['MemAvailable']
        net, iface, routed = network()
        download = upload = 0
        if iface in self.net and iface in net:
            download, upload = [max(0, net[iface][i] - self.net[iface][i]) / elapsed for i in range(2)]
        procs = processes()
        top = []
        for key, (name, ticks, rss) in procs.items():
            old = self.proc.get(key)
            percent = max(0, (ticks - old[1]) / TICKS / elapsed * 100) if old else 0
            top.append({'pid': key[0], 'name': name, 'cpu': round(percent, 1), 'memory': rss})
        top.sort(key=lambda p: (p['cpu'], p['memory']), reverse=True)
        disk = shutil.disk_usage('/')
        ds = self.disk_stat()
        activity = None
        if ds and self.disk:
            activity = [max(0, ds[i] - self.disk[i]) / elapsed for i in range(2)]
        zram = []
        for path in (SYS / 'block').glob('zram*/mm_stat'):
            try:
                v = read(path).split()
                zram.append({'name': path.parent.name, 'original': int(v[0]), 'compressed': int(v[1]), 'resident': int(v[2])})
            except (OSError, ValueError, IndexError):
                continue
        g = gpu()
        for key, value in [('cpu', usage['cpu']), ('gpu', g.get('usage')), ('download', download), ('upload', upload)]:
            self.history[key].append(value)
        result = {
            'cpu': {'usage': usage['cpu'], 'cores': [usage[k] for k in sorted(usage, key=lambda k: int(k[3:]) if k != 'cpu' else -1) if k != 'cpu'],
                    'mhz': sum(frequencies) / len(frequencies) if frequencies else None, 'temperature': temperature()},
            'gpu': g,
            'memory': {'total': memory['MemTotal'], 'used': memory_used, 'available': memory['MemAvailable'],
                       'swapTotal': memory['SwapTotal'], 'swapUsed': memory['SwapTotal'] - memory['SwapFree'], 'zram': zram},
            'disk': {'total': disk.total, 'used': disk.used, 'available': disk.free, 'activity': activity},
            'network': {'interface': iface, 'status': 'connected' if routed else ('link up · no default route' if iface else 'disconnected'), 'download': download, 'upload': upload},
            'processes': top[:5], 'uptime': float(read(PROC / 'uptime').split()[0]), 'load': list(os.getloadavg()),
            'history': {k: list(v) for k, v in self.history.items()}, 'timestamp': time.time(),
        }
        self.cpu, self.proc, self.net, self.disk, self.when = current, procs, net, ds, now
        return result


def main():
    sampler = Sampler()
    once = '--once' in sys.argv
    time.sleep(INTERVAL)  # use real deltas for the first sample
    while True:
        start = time.monotonic()
        try:
            print(json.dumps(sampler.sample(), allow_nan=False), flush=True)
        except (OSError, ValueError, KeyError) as error:
            print(json.dumps({'error': str(error), 'timestamp': time.time()}), flush=True)
        if once:
            return
        time.sleep(max(0.1, INTERVAL - (time.monotonic() - start)))


if __name__ == '__main__':
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
