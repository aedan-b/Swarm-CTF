# ---------------------------------------------------------------------------------------------------------
# ORIGINAL HARD-CODED SAMPLE (kept for reference)
# ---------------------------------------------------------------------------------------------------------
# from position import Position
# def sample(obstacles):
#   #scheduler will return [defenders_history, attackers_history]
#   #History:
#   #History is an array of timesteps
#   #Timestep is an array of position objects (data in position.x and position.y)
#   #[[Position, Position, Position][Position, Position, Position]]
#   #ex: Timestep 30, agent 4, x coordinate value
#   #x = defenders_history[30][4].x
#
#   #represents 3 defenders and 0 attackers for 5 timesteps
# 	return [
# 		[
# 			[Position(55.71, 30.53), Position(68.22, 12.05), Position(44.58, 90.21)],
# 			[Position(55.81, 30.53), Position(68.22, 12.15), Position(44.68, 90.31)],
# 			[Position(55.91, 30.53), Position(68.22, 12.25), Position(44.78, 90.41)],
# 			[Position(56.01, 30.53), Position(68.22, 12.35), Position(44.88, 90.51)],
# 			[Position(56.11, 30.53), Position(68.22, 12.45), Position(44.98, 90.61)]
# 		],
# 			[[],[],[],[],[]]
# 	]


"""
Practice scheduler: generates a full fake game so arena.py has something realistic to replay.

Returns [defenders_history, attackers_history] (same format as the real scheduler):
  History is an array of timesteps
  Timestep is an array of Position objects (data in position.x and position.y)
  ex: Timestep 30, agent 4, x coordinate value
      x = defenders_history[30][4].x

Behavior (placeholder, NOT the real algorithms):
  - Attackers follow a shortest-path distance field to the flag, so they route around obstacles,
    and they veer away from nearby defenders.
  - Defenders hold posts on a ring around the flag; any attacker that gets close is chased by the
    nearest available defender (one chaser per attacker).
  - A tagged attacker respawns in the attacker spawn zone.
  - The game ends when an attacker reaches the flag (if stop_on_capture) or after `steps` timesteps.

Coordinates are world units, 0..size on both axes, y pointing down (same as the MAPS in arena.py).
"""
import math
import random
from collections import deque

from position import Position

AGENT_RADIUS = 0.75     # world units, used for collisions
TAG_RADIUS = 1.5        # defender within this distance of an attacker tags it
THREAT_RADIUS = 25      # defenders react to attackers this close to the flag
GUARD_RING = 9          # defender posts sit this far from the flag
AVOID_RADIUS = 8        # attackers steer away from defenders within this distance
AVOID_WEIGHT = 0.6      # how strongly attackers veer away from defenders
SEPARATION_RADIUS = 3   # teammates push apart inside this distance


# ---------------------------------------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------------------------------------
def _blocked(x, y, obstacles, size, pad=AGENT_RADIUS):
    """True if a circle of radius `pad` at (x, y) overlaps an obstacle or leaves the arena."""
    if x < pad or y < pad or x > size - pad or y > size - pad:
        return True
    for ob in obstacles:
        if ob["type"] == "circle":
            cx, cy = ob["center"]
            if math.hypot(x - cx, y - cy) < ob["radius"] + pad:
                return True
        elif ob["type"] == "rectangle":
            rx, ry, rw, rh = ob["rect"]
            nx = min(max(x, rx), rx + rw)       # closest point on the rectangle
            ny = min(max(y, ry), ry + rh)
            if math.hypot(x - nx, y - ny) < pad:
                return True
    return False


def _normalize(dx, dy):
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n > 1e-9 else (0.0, 0.0)


def _step(x, y, dx, dy, speed, obstacles, size):
    """Move `speed` along (dx, dy). If blocked, try rotated directions (slide along walls).
    Returns the new position (or the old one if every option is blocked)."""
    dx, dy = _normalize(dx, dy)
    if dx == 0 and dy == 0:
        return x, y
    for angle in (0, 25, -25, 50, -50, 75, -75, 100, -100):
        a = math.radians(angle)
        rx = dx * math.cos(a) - dy * math.sin(a)
        ry = dx * math.sin(a) + dy * math.cos(a)
        nx, ny = x + rx * speed, y + ry * speed
        if not _blocked(nx, ny, obstacles, size):
            return nx, ny
    return x, y


# ---------------------------------------------------------------------------------------------------------
# Path planning: BFS distance field from the flag over a 1x1 grid
# ---------------------------------------------------------------------------------------------------------
def _distance_field(flag, obstacles, size, flag_radius):
    """dist[i][j] = number of grid steps from cell (i, j) to the flag zone (None = unreachable).
    The search starts from every free cell inside the flag radius, so a flag that overlaps a wall still works."""
    free = [[not _blocked(i + 0.5, j + 0.5, obstacles, size) for j in range(size)] for i in range(size)]
    dist = [[None] * size for _ in range(size)]
    queue = deque()
    for i in range(size):
        for j in range(size):
            if free[i][j] and math.hypot(i + 0.5 - flag[0], j + 0.5 - flag[1]) < flag_radius:
                dist[i][j] = 0
                queue.append((i, j))
    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    while queue:
        i, j = queue.popleft()
        for di, dj in neighbors:
            ni, nj = i + di, j + dj
            if 0 <= ni < size and 0 <= nj < size and free[ni][nj] and dist[ni][nj] is None:
                # no diagonal corner-cutting through walls
                if di and dj and not (free[i + di][j] and free[i][j + dj]):
                    continue
                dist[ni][nj] = dist[i][j] + 1
                queue.append((ni, nj))
    return dist


def _path_direction(x, y, flag, dist, size):
    """Direction toward the neighboring cell that is closest to the flag.
    Falls back to a straight line if this cell can't reach the flag."""
    i, j = min(max(int(x), 0), size - 1), min(max(int(y), 0), size - 1)
    if dist[i][j] is None or dist[i][j] == 0:
        return _normalize(flag[0] - x, flag[1] - y)
    best, best_cell = dist[i][j], None
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ni, nj = i + di, j + dj
            if 0 <= ni < size and 0 <= nj < size and dist[ni][nj] is not None and dist[ni][nj] < best:
                best, best_cell = dist[ni][nj], (ni, nj)
    if best_cell is None:
        return _normalize(flag[0] - x, flag[1] - y)
    return _normalize(best_cell[0] + 0.5 - x, best_cell[1] + 0.5 - y)


# ---------------------------------------------------------------------------------------------------------
# Spawning
# ---------------------------------------------------------------------------------------------------------
def _spawn_in_box(rng, box, obstacles, size):
    xmin, xmax, ymin, ymax = box
    for _ in range(1000):
        x, y = rng.uniform(xmin, xmax), rng.uniform(ymin, ymax)
        if not _blocked(x, y, obstacles, size):
            return x, y
    raise ValueError(f"no free space to spawn in box {box}")


def _spawn_near(rng, center, radius, obstacles, size):
    for _ in range(1000):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, radius)
        x, y = center[0] + r * math.cos(a), center[1] + r * math.sin(a)
        if not _blocked(x, y, obstacles, size):
            return x, y
    raise ValueError(f"no free space to spawn near {center}")


def _separation(agents, k, radius=SEPARATION_RADIUS):
    """Push agent k away from teammates within `radius`."""
    x, y = agents[k]
    px = py = 0.0
    for m, (ox, oy) in enumerate(agents):
        if m == k:
            continue
        d = math.hypot(x - ox, y - oy)
        if 1e-9 < d < radius:
            w = 1 - d / radius
            px += (x - ox) / d * w
            py += (y - oy) / d * w
    return px, py


# ---------------------------------------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------------------------------------
def sample(obstacles,
           flag=(75, 50),
           attacker_spawn=(0, 20, 20, 80),   # xmin, xmax, ymin, ymax
           num_attackers=10,
           num_defenders=10,
           steps=600,
           atk_speed=0.45,
           def_speed=0.35,
           flag_radius=3,
           size=100,
           seed=0,
           stop_on_capture=True):
    rng = random.Random(seed)
    obstacles = obstacles or []
    dist = _distance_field(flag, obstacles, size, flag_radius)

    attackers = [_spawn_in_box(rng, attacker_spawn, obstacles, size) for _ in range(num_attackers)]
    defenders = [_spawn_near(rng, flag, GUARD_RING + 4, obstacles, size) for _ in range(num_defenders)]

    # each defender gets a home post on a ring around the flag (nudged off walls if needed)
    posts = []
    for k in range(num_defenders):
        a = 2 * math.pi * k / max(num_defenders, 1)
        px, py = flag[0] + GUARD_RING * math.cos(a), flag[1] + GUARD_RING * math.sin(a)
        if _blocked(px, py, obstacles, size):
            px, py = _spawn_near(rng, (px, py), 4, obstacles, size)
        posts.append((px, py))

    def snapshot(agents):
        return [Position(x, y) for x, y in agents]

    defenders_history = [snapshot(defenders)]
    attackers_history = [snapshot(attackers)]

    for _ in range(steps):
        # ---- attackers: follow the path to the flag, dodge defenders, spread out ----
        new_attackers = []
        for k, (x, y) in enumerate(attackers):
            dx, dy = _path_direction(x, y, flag, dist, size)
            for ox, oy in defenders:
                d = math.hypot(x - ox, y - oy)
                if 1e-9 < d < AVOID_RADIUS:
                    w = AVOID_WEIGHT * (1 - d / AVOID_RADIUS)
                    dx += (x - ox) / d * w
                    dy += (y - oy) / d * w
            sx, sy = _separation(attackers, k)
            dx += sx + rng.gauss(0, 0.25)
            dy += sy + rng.gauss(0, 0.25)
            new_attackers.append(_step(x, y, dx, dy, atk_speed, obstacles, size))
        attackers = new_attackers

        # ---- defenders: one chaser per nearby attacker, everyone else holds their post ----
        threats = [a for a, (x, y) in enumerate(attackers)
                   if math.hypot(x - flag[0], y - flag[1]) < THREAT_RADIUS]
        pairs = sorted((math.dist(defenders[d], attackers[a]), d, a)
                       for d in range(num_defenders) for a in threats)
        assignment, taken = {}, set()
        for _, d, a in pairs:                     # greedy closest-first matching
            if d not in assignment and a not in taken:
                assignment[d] = a
                taken.add(a)

        new_defenders = []
        for k, (x, y) in enumerate(defenders):
            if k in assignment:
                tx, ty = attackers[assignment[k]]
                dx, dy = _normalize(tx - x, ty - y)
                speed = def_speed
            else:
                tx, ty = posts[k]
                d = math.hypot(tx - x, ty - y)
                dx, dy = _normalize(tx - x, ty - y)
                speed = min(def_speed, d)         # ease into the post instead of jittering
            sx, sy = _separation(defenders, k)
            new_defenders.append(_step(x, y, dx + sx, dy + sy, speed, obstacles, size))
        defenders = new_defenders

        # ---- tagging: tagged attackers respawn at their spawn zone ----
        for a, (x, y) in enumerate(attackers):
            if any(math.hypot(x - ox, y - oy) < TAG_RADIUS for ox, oy in defenders):
                attackers[a] = _spawn_in_box(rng, attacker_spawn, obstacles, size)

        defenders_history.append(snapshot(defenders))
        attackers_history.append(snapshot(attackers))

        # ---- capture ----
        if stop_on_capture and any(math.hypot(x - flag[0], y - flag[1]) < flag_radius for x, y in attackers):
            break

    return [defenders_history, attackers_history]


if __name__ == "__main__":
    d_hist, a_hist = sample([])
    print(f"{len(d_hist)} timesteps, {len(d_hist[0])} defenders, {len(a_hist[0])} attackers")
    print("defender 0 at t=30:", d_hist[30][0])


