import json

with open("setup.json", "r", encoding="utf-8") as file:
	data = json.load(file)

class World():
	def __init__(self):
		pass
	def validMove(self, position):
		if position.x < 0 or position.x > data["size"]:
			return False
		if position.y < 0 or position.y > data["size"]:
			return False
		return True