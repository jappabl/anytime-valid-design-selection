"""Kelly-floored variant of the WSR block betting CS.

Identical validity to WSRBlockCS (any predictable bet is valid); the
bet is floored at a shrunk Kelly plug-in after a warmup, which repairs
the measured long-horizon pathology of the stock lam ~ 1/sqrt(t log t)
schedule (results_kelly_floor.txt: llama-MBPP overhead dimension
2.46 -> 0.51; 15-33% median speedups across pools; null MC 0.034
<= alpha). Kept as an OPT-IN class so committed artifacts built on the
stock schedule remain byte-reproducible.
"""

import numpy as np

from .wsr_block_cs import WSRBlockCS

WARMUP = 10


class KellyFloorWSR(WSRBlockCS):
    """WSR with the bet floored at a shrunk Kelly plug-in (predictable)."""

    def update(self, x: float):
        if not 0.0 <= x <= 1.0:
            raise ValueError(f"observation {x} outside [0, 1]")
        self.t += 1
        sigma2 = self.sq / self.t
        lam = np.sqrt(2 * np.log(2 / self.alpha)
                      / (sigma2 * self.t * np.log(self.t + 1) + 1e-12))
        lam_p = np.minimum(lam, self.c / np.maximum(self.grid, 1e-6))
        lam_m = np.minimum(lam, self.c / np.maximum(1 - self.grid, 1e-6))
        if self.t > WARMUP:
            gap = self.mean - self.grid
            kelly = gap / (sigma2 + gap * gap + 1e-12)
            kp = np.clip(kelly, 0.0,
                         self.c / np.maximum(self.grid, 1e-6))
            km = np.clip(-kelly, 0.0,
                         self.c / np.maximum(1 - self.grid, 1e-6))
            lam_p = np.maximum(lam_p, kp)
            lam_m = np.maximum(lam_m, km)
        self.log_kp += np.log1p(lam_p * (x - self.grid))
        self.log_km += np.log1p(-lam_m * (x - self.grid))
        self.sq += (x - self.mean) ** 2
        self.mean += (x - self.mean) / (self.t + 1)
