"""Read-only admission checks for the separately named sustainable Mac profile.

A guard stops this runner before its next request. It never closes other apps or changes macOS.
"""
import ctypes
import functools
import re
import subprocess
import time


@functools.lru_cache(maxsize=1)
def _thermal_reader():
    # Public Foundation ProcessInfo.thermalState through the Objective-C runtime; no sensors/utilities installed.
    ctypes.CDLL('/System/Library/Frameworks/Foundation.framework/Foundation')
    objc = ctypes.CDLL('/usr/lib/libobjc.A.dylib')
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    pointer_message = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(('objc_msgSend', objc))
    integer_message = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)(('objc_msgSend', objc))
    info = pointer_message(objc.objc_getClass(b'NSProcessInfo'), objc.sel_registerName(b'processInfo'))
    selector = objc.sel_registerName(b'thermalState')
    return lambda: int(integer_message(info, selector))


def thermal_state():
    return _thermal_reader()()


def check(config, state):
    if not config.get('require_normal_memory_pressure'):
        return None
    pressure = int(subprocess.check_output(['sysctl', '-n', 'kern.memorystatus_vm_pressure_level'], text=True))
    if pressure != 1:  # userspace NOTE_MEMORYSTATUS_PRESSURE_NORMAL
        raise RuntimeError(f'Memory pressure level {pressure}: no new inference request started. Stop the dedicated model to release memory.')
    thermal = None
    if config.get('require_acceptable_thermal_state'):
        thermal = thermal_state()
        if thermal not in (0, 1):
            raise RuntimeError(f'Thermal state {thermal}: no new inference request started. Allow the dedicated model to cool.')
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
    return {'thermal_state': thermal, 'memory_pressure_dispatch_level': pressure, 'swapout_mib_per_sec_since_previous_check': rate}
