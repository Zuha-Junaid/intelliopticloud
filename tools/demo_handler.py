"""Handler of the demo Lambda functions. Its behaviour is controlled by the event, so the same
code can be an I/O-bound, a CPU-bound or a memory-hungry function."""
import math
import time


def lambda_handler(event, context):
    alloc_mb = int(event.get("alloc_mb", 0))      # memory to allocate and touch
    cpu_iters = int(event.get("cpu_iters", 0))    # CPU work (loop iterations)
    sleep_ms = int(event.get("sleep_ms", 0))      # waiting, like a call to a database or an API

    buf = bytearray(alloc_mb * 1024 * 1024)
    for i in range(0, len(buf), 4096):            # touch every page so the memory is really used
        buf[i] = 1
    x = 0.0
    for i in range(cpu_iters):
        x += math.sqrt(i)
    if sleep_ms:
        time.sleep(sleep_ms / 1000.0)
    return {"ok": True, "checksum": x}
