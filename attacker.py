from agent import Agent
from message import Message
from position import Position
# defenders have more "abilities" than you attacker
# those extra abilities are here

# for the defender, the extension will consist of:
  # messaging
  # coordination
class Attacker(Agent):
	def __init__(self, id, position):
		super().__init__(id, position)

	def __str__(self):
			return f"Agent {self.id}: Atk | Pos: ({self.position.x:.2f}, {self.position.y:.2f})"

	def __repr__(self):
		return str(self)