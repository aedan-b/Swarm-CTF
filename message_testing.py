import math

from defender import Defender
from message_grid import MessageGrid
from position import Position
import json

with open("setup.json", "r", encoding="utf-8") as file:
	data = json.load(file)

def test_broadcast_display():
    # Expected output:
    # A visual message grid with a diagonal line of different colored circles.
    message_grid = MessageGrid()
    defenders = []
    for i in range(data["num_defenders"]):
        pos = Position(i*10, i*10)
        defender = Defender(i, pos)
        defenders.append(defender)
        defender.broadcast_message(message_grid)

    print(message_grid)


def test_single_broadcast(sender_position, receiver_position):

    message_grid = MessageGrid()
    sender = Defender(0, sender_position)
    receiver = Defender(1, receiver_position)

    should_receive = math.sqrt((sender_position.x-receiver_position.x)**2+(sender_position.y-receiver_position.y)**2) <= data["comm_radius"]

    sender.enemy_positions.append(Position(0,2))
    sender.broadcast_message(message_grid)
    receiver.read_messages(message_grid)

    passed = (len(receiver.messages) == 1*should_receive)
    

    print("\033[0;0;41m" + "\033[0;0;42m"*passed + f"{sender_position}, {receiver_position} Test " + "Passed"*passed + "Failed"*(not passed) + "\033[00m")


def test_circle_broadcast(radius):
    for i in range(8):
        angle = math.pi/4*i
        x = radius*math.cos(angle)
        y = radius*math.sin(angle)

        test_single_broadcast(sender_position=Position(50,50), receiver_position=Position(50+x, 50+y))


def thorough_test_broadcast():
    for i in range(3):
        stage_names = ["half comm_radius", "at comm_radius", "just after comm_radius"]
        stage_radii = [data["comm_radius"]/2, data["comm_radius"], data["comm_radius"]+0.01]
        print("\n" + stage_names[i])
        test_circle_broadcast(stage_radii[i])


thorough_test_broadcast()
# print("\nSingle test")
# test_single_broadcast(Position(50, 50), Position(42.93, 42.93))

