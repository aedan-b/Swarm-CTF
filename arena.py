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

def load_config(path="setup.json"):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

config = load_config()

ARENA_WIDTH = int(config["arena_width"]) # 100
ARENA_HEIGHT = int(config["arena_height"]) # 100
NUM_ATTACKERS = int(config["num_attackers"])
NUM_DEFENDERS = int(config["num_defenders"])
AGENT_SPEED = float(config["def_speed"])
COMMUNICATION_RANGE = float(config["com_radius"])
MAX_TIMESTEPS = int(config["max_frames"])
FPS = int(config["fps"])
SEED = int(config["seed"])
#---------------------------------------------------------------------------------------------------------


# TODO 3. initialize global variables
# Arena settings
FLAG_POSITION = (ARENA_WIDTH -200, ARENA_HEIGHT // 2)
FLAG_RADIUS = 20
BG_COLOR = (0, 0, 0)  # black background
ATTACKER_COLOR = (255, 0, 0)  # red attackers
DEFENDER_COLOR = (0, 0, 255)  # blue defenders
AGENT_RADIUS = 0.5

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
# SEED = 4 -- moat and bridge (i.e. tunnel)
# SEED = 5 -- castle around flag
# SEED = 6 -- river
# SEED = 7 -- maze
# SEED = 8 -- mountains

MAPS = {
    1: {
        "name": "Open field",
        "flag_position": (75, 50),
        "attacker_spawn": (0, 20, 20, 80),  # xmin, xmax, ymin, ymax
        "defender_spawn": "around_flag",
        "obstacles": [],
    },
    2: {
        "name": "Cylinder forest",
        "flag_position": (75, 50),
        "attacker_spawn": (0, 20, 20, 80),  # xmin, xmax, ymin, ymax
        "defender_spawn": "around_flag",
        "obstacles": [
            {"type": "circle", "center": (12, 18), "radius": 4},
            {"type": "circle", "center": (25, 32), "radius": 3},
            {"type": "circle", "center": (38, 15), "radius": 5},
            {"type": "circle", "center": (48, 28), "radius": 3},
            {"type": "circle", "center": (62, 18), "radius": 4},
            {"type": "circle", "center": (70, 35), "radius": 5},
            {"type": "circle", "center": (18, 48), "radius": 3},
            {"type": "circle", "center": (32, 58), "radius": 4},
            {"type": "circle", "center": (44, 48), "radius": 5},
            {"type": "circle", "center": (58, 62), "radius": 3},
            {"type": "circle", "center": (68, 52), "radius": 4},
            {"type": "circle", "center": (15, 72), "radius": 5},
            {"type": "circle", "center": (28, 82), "radius": 3},
            {"type": "circle", "center": (42, 72), "radius": 4},
            {"type": "circle", "center": (55, 88), "radius": 5},
            {"type": "circle", "center": (70, 78), "radius": 3},
        ],
    }
    3: {
        "name": "Rectangles",
        "flag_position": (75, 50),
        "attacker_spawn": (0, 20, 20, 80),
        "defender_spawn": "around_flag",
        "obstacles": [
            {"type": "rectangle", "rect": (24, 18, 14, 7)},
            {"type": "rectangle", "rect": (52, 26, 8, 16)},
            {"type": "rectangle", "rect": (66, 72, 15, 8)},
            {"type": "rectangle", "rect": (38, 82, 18, 7)},
            {"type": "rectangle", "rect": (14, 55, 9, 14)},
        ],
    },
    4: {
        "name": "Moat and Bridge",
        "flag_position": (75, 50),
        "attacker_spawn": (0, 20, 20, 80),
        "defender_spawn": "around_flag",
        "obstacles": [
            # Solid square moat, with a bridge gap on the west side
            {"type": "rectangle", "rect": (50, 20, 4, 60)},  # left
            {"type": "rectangle", "rect": (96, 20, 4, 60)},  # right
            {"type": "rectangle", "rect": (50, 20, 50, 4)},  # top
            {"type": "rectangle", "rect": (50, 76, 50, 4)},  # bottom
            {"type": "rectangle", "rect": (50, 45, 18, 10)}, # bridge
        ],
    }
    5: {
        "name": "Castle",
        "flag_position": (75, 50),
        "attacker_spawn": (0, 20, 20, 80),
        "defender_spawn": "around_flag",
        "obstacles": [
            # Exterior walls; gap in the west wall is the single entrance
            {"type": "rectangle", "rect": (30, 18, 3, 28)},
            {"type": "rectangle", "rect": (30, 54, 3, 28)},
            {"type": "rectangle", "rect": (30, 18, 65, 3)},
            {"type": "rectangle", "rect": (30, 79, 65, 3)},
            {"type": "rectangle", "rect": (92, 18, 3, 64)},
    
            # Interior walls form branching corridors around the central passage
            {"type": "rectangle", "rect": (46, 21, 3, 21)},
            {"type": "rectangle", "rect": (46, 58, 3, 21)},
            {"type": "rectangle", "rect": (64, 21, 3, 15)},
            {"type": "rectangle", "rect": (64, 64, 3, 15)},
    
            # Upper and lower partitions, leaving openings to connect corridors
            {"type": "rectangle", "rect": (49, 36, 15, 3)},
            {"type": "rectangle", "rect": (67, 36, 22, 3)},
            {"type": "rectangle", "rect": (49, 61, 15, 3)},
            {"type": "rectangle", "rect": (67, 61, 22, 3)},
    
            # Short inner partitions create turns without blocking the route to the flag
            {"type": "rectangle", "rect": (79, 39, 3, 9)},
            {"type": "rectangle", "rect": (79, 52, 3, 6)},
        ],
    },
    6: {
        "name": "River",
        "flag_position": (75, 50),
        "attacker_spawn": (0, 20, 20, 80),
        "defender_spawn": "around_flag",
        "obstacles": [
            {"type": "rectangle", "rect": (0, 14, 12, 6)},
            {"type": "rectangle", "rect": (10, 17, 12, 6)},
            {"type": "rectangle", "rect": (20, 21, 12, 6)},
            {"type": "rectangle", "rect": (30, 27, 12, 6)},
            {"type": "rectangle", "rect": (40, 34, 12, 7)},
            {"type": "rectangle", "rect": (50, 42, 12, 7)},
            {"type": "rectangle", "rect": (60, 51, 12, 7)},
            {"type": "rectangle", "rect": (70, 58, 12, 7)},
            {"type": "rectangle", "rect": (80, 63, 12, 6)},
            {"type": "rectangle", "rect": (90, 66, 10, 6)},
        ],
    },
    7: {
        "name": "Maze",
        "flag_position": (75, 50),
        "attacker_spawn": (0, 20, 20, 80),
        "defender_spawn": "around_flag",
        "obstacles": [
            # Outer walls
            {"type": "rectangle", "rect": (5, 5, 90, 2)},
            {"type": "rectangle", "rect": (5, 93, 90, 2)},
            {"type": "rectangle", "rect": (5, 5, 2, 90)},
            {"type": "rectangle", "rect": (93, 5, 2, 90)},
    
            # Vertical walls
            {"type": "rectangle", "rect": (20, 5, 2, 38)},
            {"type": "rectangle", "rect": (20, 57, 2, 38)},
            {"type": "rectangle", "rect": (35, 5, 2, 24)},
            {"type": "rectangle", "rect": (35, 43, 2, 52)},
            {"type": "rectangle", "rect": (50, 5, 2, 52)},
            {"type": "rectangle", "rect": (50, 71, 2, 24)},
            {"type": "rectangle", "rect": (65, 5, 2, 24)},
            {"type": "rectangle", "rect": (65, 43, 2, 52)},
            {"type": "rectangle", "rect": (80, 5, 2, 38)},
            {"type": "rectangle", "rect": (80, 57, 2, 38)},
    
            # Horizontal walls
            {"type": "rectangle", "rect": (5, 20, 30, 2)},
            {"type": "rectangle", "rect": (49, 20, 31, 2)},
            {"type": "rectangle", "rect": (5, 35, 15, 2)},
            {"type": "rectangle", "rect": (20, 35, 15, 2)},
            {"type": "rectangle", "rect": (50, 35, 30, 2)},
            {"type": "rectangle", "rect": (5, 50, 30, 2)},
            {"type": "rectangle", "rect": (65, 50, 28, 2)},
            {"type": "rectangle", "rect": (20, 65, 30, 2)},
            {"type": "rectangle", "rect": (65, 65, 15, 2)},
            {"type": "rectangle", "rect": (5, 80, 30, 2)},
            {"type": "rectangle", "rect": (49, 80, 31, 2)},
        ],
    },
    8: {
        "name": "Mountains",
        "flag_position": (75, 50),
        "attacker_spawn": (0, 20, 20, 80),
        "defender_spawn": "around_flag",
        "obstacles": [
            # Western mountain: wide base and uneven rounded peaks
            {"type": "rectangle", "rect": (8, 48, 30, 18)},
            {"type": "circle", "center": (15, 48), "radius": 9},
            {"type": "circle", "center": (25, 43), "radius": 13},
            {"type": "circle", "center": (34, 51), "radius": 8},
    
            # Northern mountain
            {"type": "rectangle", "rect": (42, 8, 28, 17)},
            {"type": "circle", "center": (48, 12), "radius": 8},
            {"type": "circle", "center": (58, 8), "radius": 12},
            {"type": "circle", "center": (68, 15), "radius": 8},
    
            # Southern mountain
            {"type": "rectangle", "rect": (37, 76, 33, 16)},
            {"type": "circle", "center": (43, 76), "radius": 8},
            {"type": "circle", "center": (54, 72), "radius": 12},
            {"type": "circle", "center": (65, 78), "radius": 9},
        ],
    },
    
    
}
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
