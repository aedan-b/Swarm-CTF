# defenders have more "abilities" than you attacker
# those extra abilities are here

# for the defender, the extension will consist of:
  # messaging
  # coordination
import math

import agent
import json

with open("setup.json", "r") as file:
	data = json.load(file)
	comm_radius = data["comm_radius"]
	vision_radius = data["vision_radius"]

class Defender(agent.Agent):
	def __init__(self, id : int, position : list):
		self.id = id
		self.position = position
		self.broadcast = {}
		self.messages = []
		self.action = []

	def readMessages(self):
		#grab messages from location
		#check actual distance
		self.messages = []

	def broadcast_message(self):
		#assemble message
		self.broadcast = {
			"agent_id" : self.id,
			"position" : self.position,
			"action" : self.action,
			"enemy_positions" : []
		}

		#place message in arena within radius
		


	def __get_circle(self, radius):
		circle_positions=[]
		
		circle_x = comm_radius
		circle_y = 0
		while circle_x >= circle_y:
			circle_positions.append([circle_x + self.position[0], circle_y + self.position[1]]) 	# first octant ++
			circle_positions.append([circle_y + self.position[0], circle_x + self.position[1]]) 	# second octant
			circle_positions.append([circle_y + self.position[0], -circle_x + self.position[1]]) 	# third octant +-
			circle_positions.append([circle_y + self.position[0], circle_x + self.position[1]]) 	# second octant
			

			d = math.sqrt((circle_x - 0.5)^2 + (circle_y + 1)^2)
			if d > comm_radius:
				circle_x -= 1

			circle_y += 1

		pseudo_circle_positions = circle_positions
		for pos in pseudo_circle_positions:
			circle_positions =0

		