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
import json
#---------------------------------------------------------------------------------------------------------


# TODO 3. initialize global variables
# Arena settings

# defined in json
#    ARENA_WIDTH = 100
#    ARENA_HEIGHT = 100
#    NUM_ATTACKERS = 5
#    NUM_DEFENDERS = 5
#    AGENT_SPEED = 2.0
#    COMMUNICATION_RANGE = 100.0
#    FLAG_POSITION = (ARENA_WIDTH -200, ARENA_HEIGHT // 2)
#    FLAG_RADIUS = 20
#    MAX_TIMESTEPS = 1000
#    FPS = 60
BG_COLOR = (0, 0, 0)  # black background
ATTACKER_COLOR = (255, 0, 0)  # red attackers
DEFENDER_COLOR = (0, 0, 255)  # blue defenders
AGENT_RADIUS = 0.5

# Feature toggles
ENABLE_TAGGING = True   # False = no tag/jail; the TAG / JAIL FEATURE section can then be commented out

# random number generator
rng = np.random.default_rng(SEED)

# Simulate state
step_count = 0
flag_captured = False
history = []  # list of dicts to store per-timestep data
#---------------------------------------------------------------------------------------------------------

# TODO 4. different arenas
# SEED = 1 -- empty arena
# SEED = 2 -- forest of cylinders
# SEED = 3 -- rectangles around
# SEED = 4 -- channel tunnel to flag
# SEED = 5 -- castle around flag
#---------------------------------------------------------------------------------------------------------


# TODO 5. build the arena
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


# TODO 6. run a timestep
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

    
# TODO 7. store data in structure
#    - positional data
#    - messaging data
#---------------------------------------------------------------------------------------------------------


# TODO 8. visualize data
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
