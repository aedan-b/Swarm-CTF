# classes for:
  # attackers
  # defenders
  # how they interact
  # how they move
  # each agent's goal
    # defend flag
    # "touch" flag
class Agent():
	def __init__(self, id, position):
		self.id = id
		self.position = position
		self.declared_action = []
