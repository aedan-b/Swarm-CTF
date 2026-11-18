import json

with open("setup.json", "r", encoding="utf-8") as file:
	data = json.load(file)

class MessageGrid():
	def __init__(self):
		self.grid = [[[] for x in range(data["size"])] for y in range(data["size"])]