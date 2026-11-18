from agent import Agent
from message import Message
from position import Position
import json
import random

# defenders have more "abilities" than you attacker
# those extra abilities are here

with open("setup.json", "r", encoding="utf-8") as file:
	data = json.load(file)

# for the defender, the extension will consist of:
  # messaging
  # coordination
class Defender(Agent):
	def __init__(self, id, position):
		self.broadcast = []
		self.messages = []
		super().__init__(id, position)

	def __str__(self):
		# return f"Agent {self.id}: Def | Pos: ({self.position.x:.2f}, {self.position.y:.2f}) | Declared: ({self.declared_action.x:.2f}, {self.declared_action.y:.2f})"
		return (
            f"Def Agent {self.id:<3}|  "
            f"Pos: ({self.pos.x:>6.2f}, {self.pos.y:>6.2f})  |  "
            f"Declared: ({self.declared.x:>6.2f}, {self.declared.y:>6.2f})"
        )

	def __repr__(self):
		return str(self)

	def readMessages(self):
		#grab messages from location
		#check actual distance
		self.messages = []

	def declareAction(self):
		#random
		if not self.messages:
			max_step = data["def_speed"]/data["fps"]
			self.declared = Position(random.uniform(-max_step, max_step),random.uniform(-max_step, max_step))

	def move(self, world):
		new_pos = Position(self.pos.x + self.declared.x,
		                   self.pos.y + self.declared.y)
		if(world.validMove(new_pos)):
			self.pos = new_pos
			self.declared = Position(0.0,0.0)
		else:
			print("AGENT OUT OF BOUNDS")
			self.declared = Position(0.0,0.0)