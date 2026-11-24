# Камера референса: az, el, roll (градусы), s (пикс/ед), ox, oy (пикс), dist (ед; большая = почти орто).
# Кадр glTF, Y вверх. Экран: u вправо, v вниз.
import numpy as np
def basis(az, el, roll=0.0):
    az, el, ro = np.radians(az), np.radians(el), np.radians(roll)
    d = np.array([np.sin(az) * np.cos(el), np.sin(el), np.cos(az) * np.cos(el)])   # к камере
    r = np.cross([0, 1, 0], d); r /= np.linalg.norm(r); u = np.cross(d, r)
    return r * np.cos(ro) + u * np.sin(ro), -r * np.sin(ro) + u * np.cos(ro), d
def proj(P, c, center=np.zeros(3)):
    r, u, d = basis(c['az'], c['el'], c.get('roll', 0)); D = c.get('dist', 1e6)
    q = P - center; z = D - q @ d
    k = D / z
    return np.stack([(q @ r) * k * c['s'] + c['ox'], -(q @ u) * k * c['s'] + c['oy']], -1)
def depth(P, c):
    return P @ basis(c['az'], c['el'], c.get('roll', 0))[2]   # больше = ближе к камере
