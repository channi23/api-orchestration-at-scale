"""Read-only admission checks for the separately named sustainable Mac profile.

A guard stops this runner before its next request. It never closes other apps or changes macOS.
"""
import re
import subprocess
import time


def check(config, state):
    if not config.get('require_normal_memory_pressure'):
        return None
    pressure = int(subprocess.check_output(['sysctl', '-n', 'kern.memorystatus_vm_pressure_level'], text=True))
    if pressure != 1:  # userspace NOTE_MEMORYSTATUS_PRESSURE_NORMAL
        raise RuntimeError(f'Memory pressure level {pressure}: no new inference request started. Stop the dedicated model to release memory.')
    raw = subprocess.check_output(['vm_stat'], text=True)
    page_size = int(re.search(r'page size of (\d+) bytes', raw)[1])
    swaps = int(re.search(r'^Swapouts:\s+(\d+)', raw, re.M)[1])
    now = time.monotonic()
    previous = state.get('sample')
    rate = None
    if previous and now > previous[0]:
        rate = max(0, swaps - previous[1]) * page_size / (1024 ** 2) / (now - previous[0])
        state['hot_samples'] = state.get('hot_samples', 0) + 1 if rate >= 1 else 0
        if state['hot_samples'] >= 3:
            raise RuntimeError('Sustained swap writes >= 1 MiB/s: no new inference request started. Existing results are preserved.')
    state['sample'] = (now, swaps)
    return {'memory_pressure_dispatch_level': pressure, 'swapout_mib_per_sec_since_previous_check': rate}
