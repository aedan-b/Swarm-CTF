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
import math

import agent
import json

with open("setup.json", "r") as file:
	data = json.load(file)
	comm_radius = data["comm_radius"]
	vision_radius = data["vision_radius"]
	grid_size = data["grid_size"]

class Defender(agent.Agent):
	def __init__(self, id : int, position : list):
		self.id = id
		self.position = position
		self.broadcast = {}
		self.messages = []
		self.action = []

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

		
	def broadcast_message(self):
		#assemble message
		self.broadcast = {
			"agent_id" : self.id,
			"position" : self.position,
			"action" : self.action,
			"enemy_positions" : []
		}

		#place message in arena within radius
		broadcast_points = self.__get_circle()
		for point in broadcast_points:
			# arena.message_grid[point[0]][point[1]].append(self.broadcast) TODO
			pass


	def read_messages(self):
		cells = self.__get_nearby_cells()
		
		read_ids = []
		messages = []
		for cell in cells:
			for message in cell:
				if message["agent_id"] in read_ids:
					continue

				read_ids.append(message["agent_id"])
				sender_position = message["position"]
				euclidean = math.sqrt((sender_position[0]-self.position[0])**2 + (sender_position[1]-self.position[1])**2)
				if euclidean <= comm_radius:
					messages.append(message)


	def __get_nearby_cells(self):
		int_x = int(self.position[0])
		int_y = int(self.position[1])
		neighbor_cells = []

		for x in range(int_x-1, int_x+1):
			for y in range(int_y-1, int_y+1):
				self.__safe_append(neighbor_cells, [x, y])

		return neighbor_cells


	def __check_boundaries(self, point, grid_size=grid_size):
		if point[0] < 0 or point[1] < 0:
			return False
		if point[0] >= grid_size or point[1] >= grid_size:
			return False
		else:
			return True


	def __get_circle(self):
		# returns a list of points in a circle around the agent with a given radius
		circle_positions=[]
		
		circle_x = comm_radius
		circle_y = 0
		while circle_x >= circle_y:
			for i in range(circle_x + 1):

				self.__safe_append(circle_positions, [circle_x + self.position[0] - i, circle_y + self.position[1]]) 	# first octant ++  |  (x-i),  y 
				self.__safe_append(circle_positions, [circle_y + self.position[0], circle_x + self.position[1] - i]) 	# second octant    |  y,      (x-i)
				self.__safe_append(circle_positions, [-circle_y + self.position[0], circle_x + self.position[1] - i]) 	# third octant -+  | -y,      (x-i)
				self.__safe_append(circle_positions, [-circle_x + self.position[0] + i, circle_y + self.position[1]]) 	# fourth octant    | -(x-i),  y
				self.__safe_append(circle_positions, [-circle_x + self.position[0] + i, -circle_y + self.position[1]]) 	# fifth octant +-  | -(x-i), -y
				self.__safe_append(circle_positions, [-circle_y + self.position[0], -circle_x + self.position[1] + i]) 	# sixth octant     | -y,     -(x-i)
				self.__safe_append(circle_positions, [circle_y + self.position[0], -circle_x + self.position[1] + i]) 	# seventh octant --|  y,     -(x-i) 
				self.__safe_append(circle_positions, [circle_x + self.position[0] - i, -circle_y + self.position[1]]) 	# eighth octant    |  (x-i), -y
			

			d = math.sqrt((circle_x - 0.5)**2 + (circle_y + 1)**2)
			if d > comm_radius:
				circle_x -= 1

			circle_y += 1

		return circle_positions


	def __safe_append(self, array, point):
		if self.__check_boundaries(point):
			array.append(point)

		
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
