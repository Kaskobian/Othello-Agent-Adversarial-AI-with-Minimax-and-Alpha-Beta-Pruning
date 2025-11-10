from typing import Tuple
import time


def now_seconds() -> float:
    return time.time()



def format_seconds(s: float) -> str:
    if s < 0:
        s = 0
        mins = int(s) // 60
        secs = int(s) % 60
    return f"{mins:02d}:{secs:02d}"




def clamp(v, lo, hi):
    return max(lo, min(hi, v))