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

# from messaging import Broadcast, Message
# from positioning import update_position
import json

def load_config(path="setup.json"):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

config = load_config()

ARENA_WIDTH = int(config["arena_width"]) # 100
ARENA_LENGTH = int(config["arena_length"]) # 100
NUM_ATTACKERS = int(config["num_attackers"])
NUM_DEFENDERS = int(config["num_defenders"])
AGENT_SPEED = float(config["def_speed"])
COMMUNICATION_RANGE = float(config["comm_radius"])
MAX_TIMESTEPS = int(config["max_frames"])
FPS = int(config["fps"])
SEED = int(config["seed"])

from scheduler_sample import sample # scheduler import

#---------------------------------------------------------------------------------------------------------


# TODO 3. initialize global variables
# Arena settings
BG_COLOR = (0, 0, 0)  # black background
ATTACKER_COLOR = (255, 0, 0)  # red attackers
DEFENDER_COLOR = (0, 0, 255)  # blue defenders
AGENT_RADIUS = 0.5
SCALE = 8 # pixels per world unit
SCREEN_W, SCREEN_H = ARENA_WIDTH * SCALE, ARENA_LENGTH * SCALE
FLAG_RADIUS = float(config["flag_radius"])
AGENT_RADIUS = 0.75                      # world units
OBSTACLE_COLOR = (90, 90, 90)

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
    },
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
    },
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

MAP = MAPS[SEED]
FLAG_POSITION = MAP["flag_position"]

#---------------------------------------------------------------------------------------------------------
# TODO 5. build the arena
#    - spawn in agents (distribution?)
#    - spawn in obstacles
#    - spawn in flag zone
#    - 


def to_px(x, y):
    return int(x * SCALE), int(y * SCALE)

def history_to_array(hist):
    """
    list[timestep][agent] of Position -> array (timesteps, number of agents on the team, 2 [one xy pair per agent]). reshape keeps (T, 0, 2) for empty teams.
    e.g. (5,4,2) is 5 timesteps, 4 attackers, and their xy's
    """
    return np.array([[(p.x, p.y) for p in step] for step in hist], dtype=float).reshape(len(hist), -1, 2)

def first_capture(A):
    """First timestep any attacker catches the flag (i.e. is inside the flag radius)"""
    if A.shape[1] == 0:
        return None # i.e. no attacker caught a flag
    inside = np.linalg.norm(A - np.array(FLAG_POSITION), axis=2) < FLAG_RADIUS # (T,N)
    hits = np.where(inside.any(axis=1))[0]
    return int(hits[0]) if len(hits) else None # return the first capture if a flag was caught

def draw_obstacles(screen):
    """Draw circle and rectangle obstacles"""
    for ob in MAP["obstacles"]:
        if ob["type"] == "circle":
            pygame.draw.circle(screen, OBSTACLE_COLOR, to_px(*ob["center"]), ob["radius"] * SCALE)
        elif ob["type"] == "rectangle":
            x, y, w, h = ob["rect"]
            pygame.draw.rect(screen, OBSTACLE_COLOR, (x * SCALE, y * SCALE, w * SCALE, h * SCALE))

def draw_frame(screen, font, t, T, attackers, defenders, captured):
    """Drawing the arena with agents"""
    screen.fill(BG_COLOR)
    draw_obstacles(screen)
    pygame.draw.circle(screen, (255, 255, 255), to_px(*FLAG_POSITION), FLAG_RADIUS * SCALE, width=2)
    for x, y in attackers:
        pygame.draw.circle(screen, ATTACKER_COLOR, to_px(x, y), AGENT_RADIUS * SCALE)
    for x, y in defenders:
        pygame.draw.circle(screen, DEFENDER_COLOR, to_px(x, y), AGENT_RADIUS * SCALE)
    screen.blit(font.redner(f"Step: {t}/{T - 1} MAP: {MAP['name']}", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(f"Flag Captured: {captured}", True, (255, 255, 255)), (10, 30))
    pygame.display.flip()
        
def main(result=None):
    """Putting everything together"""
    if result is None:
        result = sample(MAP["obstacles"])
    defenders_hist, attackers_hist = result # scheduler order here
    D, A = history_to_array(defenders_hist), history_to_array(attackers_hist)
    T = max(len(D), len(A))
    capture_t = first_capture(A)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Swarm Arena Playback")
    font = pygame.font.SysFont(None, 24)
    clock = pygame.time.Clock()

    t, paused, running = 0, False, True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False # stop playback
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: paused = not paused
                elif event.key == pygame.K_RIGHT: t = min(t + 1, T - 1)
                elif event.key == pygame.K_LEFT:  t = max(t - 1, 0)
                elif event.key == pygame.K_r:     t = 0
        a = A[min(t, len(A) - 1)] if len(A) else np.empty((0, 2))
        d = D[min(t, len(D) - 1)] if len(D) else np.empty((0, 2))
        captured = capture_t is not None and t >= capture_t
        draw_frame(screen, font, t, T, a, d, captured) # drawing
        if not paused:
            t = min(t + 1, T - 1)
        clock.tick(FPS)
    pygame.quit()

#---------------------------------------------------------------------------------------------------------


# TODO 6. run a timestep
#    - move agents
#    - determine if flag captured
#    -


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

if __name__ == "__main__":
    main()
