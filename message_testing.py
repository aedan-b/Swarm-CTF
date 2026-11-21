import math
import random

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

def test_multi_broadcast():
    sender_1_position = Position(40, 50)
    receiver_position = Position(50, 50)
    sender_2_position = Position(60, 50)

    message_grid = MessageGrid()
    sender_1 = Defender(0, sender_1_position)
    sender_2 = Defender(2, sender_2_position)
    receiver = Defender(1, receiver_position)

    should_receive_1 = math.sqrt((sender_1_position.x-receiver_position.x)**2+(sender_1_position.y-receiver_position.y)**2) <= data["comm_radius"]
    should_receive_2 = math.sqrt((sender_2_position.x-receiver_position.x)**2+(sender_2_position.y-receiver_position.y)**2) <= data["comm_radius"]

    sender_1.enemy_positions.append(Position(0,2))
    sender_2.enemy_positions.append(Position(0,0))
    sender_1.broadcast_message(message_grid)
    sender_2.broadcast_message(message_grid)
    receiver.read_messages(message_grid)

    passed = (len(receiver.messages) == 1*should_receive_1 + 1*should_receive_2)    

    print("\033[0;0;41m" + "\033[0;0;42m"*passed + f"{sender_1_position}, {sender_2_position}, {receiver_position} Test " + "Passed"*passed + "Failed"*(not passed) + "\033[00m")


def num_defenders_random_test(seed):
    # WARNING: COMPUTATIONALLY INTENSIVE
    # USES COMBINATORIAL MATH TO CHECK ANSWER
    message_grid = MessageGrid()
    random.seed(seed)
    defenders = []
    for i in range(data["num_defenders"]):
        pos = Position(random.randrange(0, data["size"]*100)/100, random.randrange(0, data["size"]*100)/100)
        defender = Defender(i, pos)
        defenders.append(defender)
        defender.enemy_positions.append(Position(0,0))
        defender.broadcast_message(message_grid)

    for defender in defenders:

        # Brute force check how many messages should have been received
        expected_message_count = 0
        for defender_2 in defenders:
            if defender == defender_2:
                continue
            expected_message_count += 1*(math.sqrt((defender.pos.x-defender_2.pos.x)**2+(defender.pos.y-defender_2.pos.y)**2) <= data["comm_radius"])

        # actual message count
        defender.read_messages(message_grid)
        actual_message_count = len(defender.messages)

        if not (expected_message_count == actual_message_count):
            print(f"Failed on defender {defender.id}")
            print(f"expected {expected_message_count} messages, received {actual_message_count}")
            return

        print("success")


# thorough_test_broadcast()
# print("\nSingle test")
# test_single_broadcast(Position(50, 50), Position(42.93, 42.93))
# test_multi_broadcast()
num_defenders_random_test(0)

