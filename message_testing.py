from defender import Defender
from message_grid import MessageGrid
from position import Position
import json

with open("setup.json", "r", encoding="utf-8") as file:
	data = json.load(file)

def test_broadcast_display():
    message_grid = MessageGrid()
    defenders = []
    for i in range(data["num_defenders"]):
        pos = Position(i*10, i*10)
        defender = Defender(i, pos)
        defenders.append(defender)
        defender.broadcast_message(message_grid)

    print(message_grid)


def test_broadcast_reading():
    message_grid = MessageGrid()
    sender = Defender(0, Position(0,0))
    receiver = Defender(1, Position(5, 0))

    sender.broadcast_message(message_grid)
    receiver.read_messages(message_grid)

    print(receiver.messages)



test_broadcast_reading()

