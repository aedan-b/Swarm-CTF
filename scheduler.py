#todo
import json
from defender import Defender
from attacker import Attacker
from position import Position
from world import World
import random

def printAgents(agents):
	print("[")
	print("\n".join(f"  {agent}" for agent in agents))
	print("]")
if __name__ == "__main__":
	with open("setup.json", "r", encoding="utf-8") as file:
		data = json.load(file)

	za_world = World()

	attackers = []
	for i in range(data["num_defenders"]):
		attackers.append(Attacker(i, Position(random.uniform(0.0, data["size"]),random.uniform(0.0, data["size"]))))

	defenders = []
	for i in range(data["num_defenders"]):
		defenders.append(Defender(i, Position(random.uniform(0.0, data["size"]),random.uniform(0.0, data["size"]))))

	for agent in defenders:
		agent.declareAction()

	printAgents(defenders)

	for agent in defenders:
			agent.move(za_world)

	printAgents(defenders)

	# for i in range(data["max_frames"]):
	# 	for agent in defenders:
	# 		print(agent.position)