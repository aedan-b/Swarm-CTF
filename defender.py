from agent import Agent
from position import Position
import json
import random
import math

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

		
	def broadcast_message(self, message_grid):
		#assemble message
		self.broadcast = {
			"agent_id" : self.id,
			"position" : self.pos,
			"action" : self.declared,
			"enemy_positions" : []
		}

		#place message in arena within radius
		broadcast_points = self.__get_circle()
		for point in broadcast_points:
			message_grid.grid[point[1]][point[0]].append(self.broadcast)


	def read_messages(self, message_grid):
		cells = self.__get_nearby_cells()
		
		read_ids = []
		messages = []
		for cell in cells:
			messages = message_grid.grid[cell[0]][cell[1]]
			for message in messages:
				if message["agent_id"] in read_ids:
					continue

				read_ids.append(message["agent_id"])
				sender_position = message["position"]
				euclidean = math.sqrt((sender_position.x-self.pos.x)**2 + (sender_position.y-self.pos.y)**2)
				if euclidean <= data["comm_radius"]:
					self.messages.append(message)


	def __get_nearby_cells(self):
		int_x = int(self.pos.x)
		int_y = int(self.pos.y)
		neighbor_cells = []

		for x in range(int_x-1, int_x+1):
			for y in range(int_y-1, int_y+1):
				self.__safe_append(neighbor_cells, [x, y])

		return neighbor_cells


	def __check_boundaries(self, point, grid_size=data["size"]):
		if point[0] < 0 or point[1] < 0:
			return False
		if point[0] >= grid_size or point[1] >= grid_size:
			return False
		else:
			return True


	def __get_circle(self):
		# returns a list of points in a circle around the agent with a given radius
		circle_positions=[]
		
		circle_x = data["comm_radius"]
		circle_y = 0
		while circle_x >= circle_y:
			for i in range(circle_x + 1):

				self.__safe_append(circle_positions, [circle_x + self.pos.x - i, circle_y + self.pos.y]) 	# first octant ++  |  (x-i),  y 
				self.__safe_append(circle_positions, [circle_y + self.pos.x, circle_x + self.pos.y - i]) 	# second octant    |  y,      (x-i)
				self.__safe_append(circle_positions, [-circle_y + self.pos.x, circle_x + self.pos.y - i]) 	# third octant -+  | -y,      (x-i)
				self.__safe_append(circle_positions, [-circle_x + self.pos.x + i, circle_y + self.pos.y]) 	# fourth octant    | -(x-i),  y
				self.__safe_append(circle_positions, [-circle_x + self.pos.x + i, -circle_y + self.pos.y]) 	# fifth octant +-  | -(x-i), -y
				self.__safe_append(circle_positions, [-circle_y + self.pos.x, -circle_x + self.pos.y + i]) 	# sixth octant     | -y,     -(x-i)
				self.__safe_append(circle_positions, [circle_y + self.pos.x, -circle_x + self.pos.y + i]) 	# seventh octant --|  y,     -(x-i) 
				self.__safe_append(circle_positions, [circle_x + self.pos.x - i, -circle_y + self.pos.y]) 	# eighth octant    |  (x-i), -y
			

			d = math.sqrt((circle_x - 0.5)**2 + (circle_y + 1)**2)
			if d > data["comm_radius"]:
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
