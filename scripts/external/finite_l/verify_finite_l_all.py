#!/usr/bin/env python3
import math
import sys

sys.path.insert(0, "/tmp")
from finite_l_oracle import exact_oracle
from finite_l_prediction import params, rho_spitzer


def kl(u: float, v: float) -> float:
    out = 0.0
    if u:
        out += u * math.log(u / v)
    if u < 1.0:
        out += (1.0 - u) * math.log((1.0 - u) / (1.0 - v))
    return out


p0, tau0 = 0.202, 0.157
assert abs(rho_spitzer(p0, tau0, 1) - 0.0941692) < 3e-8
assert abs(rho_spitzer(p0, tau0, 4) - 0.1703462) < 4e-8

_, _, _, c0, _ = params(p0, tau0)
max_bregman_error = 0.0
for n in [20, 73, 804, 1304]:
    for f in [0, 1, n // 5, n // 2, n - 1, n]:
        u = f / n
        lhs = n * (kl(u, tau0) - kl(p0, tau0))
        rhs = c0 * (f - p0 * n) + n * kl(u, p0)
        max_bregman_error = max(max_bregman_error, abs(lhs - rhs))
assert max_bregman_error < 3e-12

pairs = [(0.202, 0.157), (0.3, 0.2)]
ds = [1, 2, 4]
alphas = [0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.002]
count = 0
max_mass_error = 0.0
max_tail = 0.0
max_wald2_error = 0.0
checksum_overshoot = 0.0
checksum_selection = 0.0
target = None
for p, tau in pairs:
    for d in ds:
        for alpha in alphas:
            out = exact_oracle(p, tau, math.log(1.0 / alpha), d, n0=20)
            count += 1
            max_mass_error = max(max_mass_error, abs(out.mass + out.tail_mass - 1.0))
            max_tail = max(max_tail, out.tail_mass)
            max_wald2_error = max(max_wald2_error, abs(out.martingale_mean))
            checksum_overshoot += out.mean_overshoot
            checksum_selection += out.selection_cov_correction
            if (p, tau, d, alpha) == (0.202, 0.157, 4, 0.05):
                target = out

assert count == 42
assert max_mass_error < 5e-12
assert max_tail < 2.1e-15
assert max_wald2_error < 3e-9
assert target is not None
assert abs(target.mean_overshoot - 0.22865792747248742) < 2e-12
assert abs(target.selection_cov_correction - 0.18135529004500195) < 2e-12

print(f"cases={count}")
print(f"max_mass_error={max_mass_error:.3g}")
print(f"max_tail={max_tail:.3g}")
print(f"max_wald2_error={max_wald2_error:.3g}")
print(f"max_bregman_error={max_bregman_error:.3g}")
print(f"overshoot_checksum={checksum_overshoot:.15g}")
print(f"selection_checksum={checksum_selection:.15g}")
print(f"target_overshoot={target.mean_overshoot:.15g}")
print(f"target_selection_cov={target.selection_cov_correction:.15g}")
