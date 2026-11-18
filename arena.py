# define play-space
# enable obstacles if desired
# spawn in agents
# define runtime
# run scheduler to perform stepping
# visualize


#---------------------------------------------------------------------------------------------------------
# TODO 1. imports
# --- Standard library ---
import math                      # distances, angles, vector headings
import random                    # agent/obstacle/flag spawn distributions
import time                      # runtime limits, frame timing
from dataclasses import dataclass, field   # Agent / Message / Obstacle records
from collections import defaultdict, deque # message inboxes, pheromone trails (deque(maxlen=N))
from enum import Enum            # Team.ATTACKER / Team.DEFENDER, agent states

# --- Numerics / data ---
import numpy as np               # positions as (N,2) arrays, vectorized movement, RNG via np.random.default_rng(seed)
from scipy.spatial import cKDTree  # fast neighbor queries ("who's in comm range?"), essential once N gets large
import pandas as pd              # step 5: store per-timestep positional/message/capture logs, export to CSV

# --- Visualization ---
import pygame                    # live arena view, vectors, message lines, pheromone trails
import matplotlib.pyplot as plt  # post-run analysis plots (avg inter-agent distance over time, attacker vs defender paths)
#---------------------------------------------------------------------------------------------------------


# TODO 2. call the information we need from the other files
#    - messages / broadcasts
#    - position algorithm
#    - 

# --- Your own modules (step 3) ---
# from messaging import Broadcast, Message
# from positioning import update_position
#---------------------------------------------------------------------------------------------------------


# TODO 3. initialize global variables
# Arena settings
ARENA_WIDTH = 800
ARENA_HEIGHT = 600
NUM_ATTACKERS = 5
NUM_DEFENDERS = 5
AGENT_SPEED = 2.0
COMMUNICATION_RANGE = 100.0
FLAG_POSITION = (ARENA_WIDTH -200, ARENA_HEIGHT // 2)
FLAG_RADIUS = 20
MAX_TIMESTEPS = 1000
FPS = 60
SEED = 1
BG_COLOR = (0, 0, 0)  # black background
ATTACKER_COLOR = (255, 0, 0)  # red attackers
DEFENDER_COLOR = (0, 0, 255)  # blue defenders
AGENT_RADIUS = 5

# Feature toggles
ENABLE_TAGGING = True   # False = no tag/jail; the TAG / JAIL FEATURE section can then be commented out

# random number generator
rng = np.random.default_rng(SEED)

# Simulate state
step_count = 0
flag_captured = False
history = []  # list of dicts to store per-timestep data
#---------------------------------------------------------------------------------------------------------


# TODO 4. build the arena
#    - spawn in agents (distribution?)
#    - spawn in obstacles
#    - spawn in flag zone
#    - 
def build_arena():
    global attackers, defenders, obstacles, flag_position
    attackers = []
    defenders = []
    obstacles = []
    flag_position = FLAG_POSITION


    # place agents in arena
    # attackers at random positions on left half of arena
    attackers = rng.uniform(low=[20, 20], high=[200, ARENA_HEIGHT - 20], size=(NUM_ATTACKERS, 2))
    # defenders at normalized positions around the flag
    defenders = FLAG_POSITION + rng.normal(0, 60, size=(NUM_DEFENDERS, 2))

    if ENABLE_TAGGING:
        tag_reset()

# flag captured (only "free" attackers can capture; all are free when tagging is off)
def flag_captured_check(attacker_free):
    global flag_captured
    for i, attacker in enumerate(attackers):
        if attacker_free[i] and np.linalg.norm(attacker - FLAG_POSITION) < FLAG_RADIUS:
            flag_captured = True
            break

# drawing the arena
def draw_arena(screen, font, step, captured):
    screen.fill(BG_COLOR)
    # draw flag
    pygame.draw.circle(screen, (255, 255, 255), FLAG_POSITION, FLAG_RADIUS, width=2)  # white flag ring
    # draw attackers
    for attacker in attackers:
        pygame.draw.circle(screen, ATTACKER_COLOR, attacker.astype(int), AGENT_RADIUS)
    # draw defenders
    for defender in defenders:
        pygame.draw.circle(screen, DEFENDER_COLOR, defender.astype(int), AGENT_RADIUS)
    # draw step count and capture status
    step_text = font.render(f"Step: {step}", True, (255, 255, 255))
    captured_text = font.render(f"Flag Captured: {captured}", True, (255, 255, 255))
    screen.blit(step_text, (10, 10))
    screen.blit(captured_text, (10, 30))

    if ENABLE_TAGGING:
        tag_draw(screen, font)   # jail box, dimmed jailed attackers, tag counter

    pygame.display.flip()

#---------------------------------------------------------------------------------------------------------


# PLACEHOLDER BEHAVIOR -- replace with imports from the behavior files later.
# Contract: a policy takes positions in, and returns one direction per agent, shape (N, 2).
# It should NOT modify the position arrays itself; apply_movement does that.
def attacker_policy(attackers, defenders, flag):
    to_flag = np.asarray(flag) - attackers                 # head toward the flag...
    wiggle = rng.normal(0, 0.5, size=attackers.shape)      # ...with a bit of randomness
    return to_flag / (np.linalg.norm(to_flag, axis=1, keepdims=True) + 1e-9) + wiggle

def defender_policy(defenders, attackers, flag):
    return rng.normal(0, 1, size=defenders.shape)          # random wander (used when tagging is off)


# Arena physics: turns directions into actual moves and enforces the rules
def apply_movement(positions, directions):
    length = np.linalg.norm(directions, axis=1, keepdims=True) + 1e-9
    new_pos = positions + directions / length * AGENT_SPEED   # fixed speed, any direction
    new_pos[:, 0] = np.clip(new_pos[:, 0], AGENT_RADIUS, ARENA_WIDTH - AGENT_RADIUS)   # walls
    new_pos[:, 1] = np.clip(new_pos[:, 1], AGENT_RADIUS, ARENA_HEIGHT - AGENT_RADIUS)
    return new_pos

#---------------------------------------------------------------------------------------------------------


# =========================================================================================================
# TAG / JAIL FEATURE  ---------------------------------------------------------------- START
# Defenders that touch an attacker send it to jail (bottom-left corner) for JAIL_TIME steps.
# To disable: set ENABLE_TAGGING = False (top of file). You can then comment out this whole section;
# the rest of the file only touches it through `if ENABLE_TAGGING:` lines.
# =========================================================================================================

# --- Tag / jail settings ---
TAG_RADIUS = 2 * AGENT_RADIUS            # defender "touches" attacker when circles overlap
JAIL_TIME = 100                          # timesteps an attacker spends in jail
JAIL_POSITION = (40, ARENA_HEIGHT - 40)  # bottom-left corner
JAIL_SIZE = 60                           # jail square side length (pixels)
DEFEND_RADIUS = 150                      # defenders chase attackers within this distance of the flag
GUARD_RING = 70                          # each defender's home post sits on a ring this far from the flag
SEPARATION_RADIUS = 40                   # defenders push away from teammates closer than this
JAIL_COLOR = (120, 120, 120)
JAILED_ATTACKER_COLOR = (120, 40, 40)    # dimmed red while in jail

# --- Tag / jail state ---
jail_timer = np.zeros(NUM_ATTACKERS, dtype=int)  # steps left in jail per attacker (0 = free)
tag_count = 0


def tag_reset():
    """Called from build_arena: empty the jail."""
    global jail_timer, tag_count
    jail_timer = np.zeros(NUM_ATTACKERS, dtype=int)
    tag_count = 0


def tag_update():
    """Called at the start of each timestep: count down sentences, return which attackers are free."""
    np.subtract(jail_timer, 1, out=jail_timer, where=jail_timer > 0)
    return jail_timer == 0


def tag_check():
    """Called after movement: any free attacker touched by a defender goes to jail."""
    global tag_count
    for i in range(NUM_ATTACKERS):
        if jail_timer[i] > 0:
            continue  # already in jail
        dists = np.linalg.norm(defenders - attackers[i], axis=1)
        if np.any(dists < TAG_RADIUS):
            jail_timer[i] = JAIL_TIME
            # spread jailed attackers out in a small grid so they don't overlap
            offset = np.array([(i % 3) * 15 - 15, (i // 3) * 15 - 15])
            attackers[i] = np.array(JAIL_POSITION) + offset
            tag_count += 1


def tag_assign_targets(defenders, threats):
    """Greedy one-to-one matching: repeatedly pair the closest (defender, attacker) that are both
    still unassigned. Returns {defender index: attacker row in `threats`}. Each attacker gets at most
    one chaser, so defenders don't all pile onto the same target."""
    if len(threats) == 0:
        return {}
    dist = np.linalg.norm(defenders[:, None, :] - threats[None, :, :], axis=2)  # (defenders, threats)
    assignment = {}
    for _ in range(min(len(defenders), len(threats))):
        j, t = np.unravel_index(np.argmin(dist), dist.shape)
        assignment[j] = t
        dist[j, :] = np.inf   # this defender is taken
        dist[:, t] = np.inf   # this attacker is covered
    return assignment


def tag_separation(defenders):
    """Push each defender away from teammates within SEPARATION_RADIUS (stronger when closer)."""
    diff = defenders[:, None, :] - defenders[None, :, :]                # (N, N, 2): vector from k to j
    dist = np.linalg.norm(diff, axis=2) + 1e-9
    strength = np.clip(1 - dist / SEPARATION_RADIUS, 0, None)          # 1 when touching, 0 at the radius
    np.fill_diagonal(strength, 0)                                       # ignore yourself
    return (diff / dist[:, :, None] * strength[:, :, None]).sum(axis=1)


def tag_defender_policy(defenders, attackers, flag, attacker_free):
    """Zone defense:
    - Each free attacker within DEFEND_RADIUS of the flag gets ONE chaser (closest available defender).
    - Defenders without a target return to their own post on a ring around the flag.
    - All defenders keep some distance from each other (separation)."""
    flag = np.asarray(flag)
    n = len(defenders)

    # home posts evenly spaced around the flag
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    posts = flag + GUARD_RING * np.column_stack([np.cos(angles), np.sin(angles)])

    # which attackers are threats, and who chases whom
    threat_idx = np.where(attacker_free & (np.linalg.norm(attackers - flag, axis=1) < DEFEND_RADIUS))[0]
    assignment = tag_assign_targets(defenders, attackers[threat_idx])

    separation = tag_separation(defenders)
    directions = np.zeros_like(defenders)
    for j in range(n):
        if j in assignment:
            to_target = attackers[threat_idx[assignment[j]]] - defenders[j]
            directions[j] = to_target / (np.linalg.norm(to_target) + 1e-9) + 0.5 * separation[j]   # chase
        else:
            to_post = posts[j] - defenders[j]
            dist = np.linalg.norm(to_post)
            pull = to_post / (dist + 1e-9) * min(dist / 20, 1.0)       # ease in near the post
            directions[j] = pull + 1.5 * separation[j] + rng.normal(0, 0.3, size=2)            # hold post
    return directions


def tag_draw(screen, font):
    """Called from draw_arena: jail box, dimmed jailed attackers, tag counter."""
    jail_rect = pygame.Rect(0, 0, JAIL_SIZE, JAIL_SIZE)
    jail_rect.center = JAIL_POSITION
    pygame.draw.rect(screen, JAIL_COLOR, jail_rect, width=2)
    for i, attacker in enumerate(attackers):
        if jail_timer[i] > 0:
            pygame.draw.circle(screen, JAILED_ATTACKER_COLOR, attacker.astype(int), AGENT_RADIUS)
    tags_text = font.render(f"Tags: {tag_count}   In jail: {int(np.sum(jail_timer > 0))}", True, (255, 255, 255))
    screen.blit(tags_text, (10, 50))

# =========================================================================================================
# TAG / JAIL FEATURE  ---------------------------------------------------------------- END
# =========================================================================================================


# TODO 5. run a timestep
#    - move agents
#    - determine if flag captured
#    -
def run_timestep():
    global step_count, attackers, defenders
    if flag_captured or step_count >= MAX_TIMESTEPS:
        return  # stop simulation if flag is captured or max timesteps reached

    # which attackers can act this step (all of them unless tagging puts some in jail)
    attacker_free = np.ones(NUM_ATTACKERS, dtype=bool)
    if ENABLE_TAGGING:
        attacker_free = tag_update()

    # 1. agent behavior: decide directions
    a_dirs = attacker_policy(attackers, defenders, FLAG_POSITION)
    a_dirs[~attacker_free] = 0              # jailed attackers stay put
    if ENABLE_TAGGING:
        d_dirs = tag_defender_policy(defenders, attackers, FLAG_POSITION, attacker_free)
    else:
        d_dirs = defender_policy(defenders, attackers, FLAG_POSITION)
    # 2. move agents
    attackers = apply_movement(attackers, a_dirs)
    defenders = apply_movement(defenders, d_dirs)
    # 3. check rules (tag first, so a tagged attacker can't also capture this step)
    if ENABLE_TAGGING:
        tag_check()
        attacker_free = jail_timer == 0
    flag_captured_check(attacker_free)
    # record history for this timestep
    record = {
        'step': step_count,
        'attackers': attackers.copy(),
        'defenders': defenders.copy(),
        'flag_captured': flag_captured
    }
    if ENABLE_TAGGING:
        record['jailed'] = jail_timer > 0   # boolean mask: which attackers are in jail
    history.append(record)

    step_count += 1
#---------------------------------------------------------------------------------------------------------

    
# TODO 5. store data in structure
#    - positional data
#    - messaging data
#---------------------------------------------------------------------------------------------------------


# TODO 6. visualize data
#    - pygame
#    - what do we want to visualize
#        - arena over time
#        - isolate defender and attacker movement
#        - average distance between agents over time
#        - visualize messages for debugging
#        - visualize vectors
#        - trace / path pheremone
#---------------------------------------------------------------------------------------------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((ARENA_WIDTH, ARENA_HEIGHT))
    pygame.display.set_caption("Swarm Arena Simulation")
    font = pygame.font.SysFont(None, 24)

    build_arena()

    clock = pygame.time.Clock()
    running = True
    while running: # iterating over timesteps
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        run_timestep()
        draw_arena(screen, font, step_count, flag_captured)
        clock.tick(FPS)

    pygame.quit()
    return history

if __name__ == "__main__":
    main()
