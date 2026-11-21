import json

with open("setup.json", "r", encoding="utf-8") as file:
	data = json.load(file)

class MessageGrid():
	def __init__(self):
		self.grid = [[[] for x in range(data["size"])] for y in range(data["size"])]

	def __str__(self):
		output = " " + "__"*data["size"] + " "

		for y in range(data["size"]):
			output += "\n|"
			for x in range(data["size"]):
				cell = self.grid[x][y]
				if cell:
					first_message = cell[0]
					first_id = first_message["agent_id"]
					color = self.__agent_color(first_id)
					output += f"\033[{color}m██\033[00m"
				else:
					output += "  "
			output += "|"

		output += "\n " + "‾‾"*data["size"] + " "
		return output


	def __agent_color(self, agent_id):
		num_colors = 7

		color_num = agent_id % num_colors

		return color_num + 91

	def clear(self):
		self.grid = [[[] for x in range(data["size"])] for y in range(data["size"])]