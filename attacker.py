from agent import Agent
from position import Position
from math import sqrt
import json
# defenders have more "abilities" than you attacker
# those extra abilities are here

# for the defender, the extension will consist of:
  # messaging
  # coordination

with open("setup.json", "r", encoding="utf-8") as file:
	data = json.load(file)


class Attacker(Agent):
	def __init__(self, id, position):
		super().__init__(id, position)

	def __str__(self):
			return f"Agent {self.id}: Atk | Pos: ({self.pos.x:.2f}, {self.pos.y:.2f})"

	def __repr__(self):
		return str(self)

	def declareAction(self, world):
		max_step = data["atk_speed"]/data["fps"]
		x = world.flag.x-self.pos.x
		y = world.flag.y-self.pos.y
		x_scaled = x / (sqrt(x^2 + y^2)) * max_step
		y_scaled = y / (sqrt(x^2 + y^2)) * max_step