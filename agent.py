# classes for:
  # attackers
  # defenders
  # how they interact
  # how they move
  # each agent's goal
    # defend flag
    # "touch" flag
from position import Position

class Agent():
	def __init__(self, id, position):
		self.id = id
		self.pos = position
		self.declared = Position(0.0, 0.0)
