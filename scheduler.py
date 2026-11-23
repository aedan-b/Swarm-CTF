#todo
import json
from defender import Defender
from attacker import Attacker
from position import Position
from world import World
import random

with open("setup.json", "r", encoding="utf-8") as file:
	data = json.load(file)

def scheduler(obstacles):
	attackers = []
	for i in range(data["num_attackers"]):
		attackers.append(Attacker(i, Position(random.uniform(0.0, data["size"]),random.uniform(0.0, data["size"]))))
	defenders = []
	for i in range(data["num_defenders"]):
		defenders.append(Defender(i, Position(random.uniform(0.0, data["size"]),random.uniform(0.0, data["size"]))))

	world = World()

	for i in range(data["max_frames"]):
		for agent in defenders:
			agent.read_messages()
			agent.sense(attackers, world)
			agent.broadcast_message()
			agent.declareAction(world)
		for agent in attackers:
			agent.declareAction(world)
		for agent in defenders:
			agent.move(world)
		for agent in attackers:
			agent.move(world)


def printAgents(agents):
	print("[")
	print("\n".join(f"  {agent}" for agent in agents))
	print("]")
if __name__ == "__main__":
	with open("setup.json", "r", encoding="utf-8") as file:
		data = json.load(file)

	world = World()

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
			agent.move(world)

	printAgents(defenders)

	