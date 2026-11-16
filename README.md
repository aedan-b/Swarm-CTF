# Swarm-CTF

class Agent():
	def __init__(self, id, position):
		self.id = id
		self.position = position
		self.broadcast = []
		self.messages = [Message]
		self.declared_action = []

def readMessages(self):
		#grab messages from location
		#check actual distance
		self.messages = []

class Message():
	def __init__(self, origin, content):
		self.origin = origin
		self. content = content


if __name__ == "__main__":
	max_frames = 1000
	size = 100
	vision_radius = 10
	comm_radius = 10
	tile_size = comm_radius
	tile_board = 


	for i in range(max_frames):



<img width="454" height="400" alt="image" src="https://github.com/user-attachments/assets/4c9e2537-8a68-4c14-a5b8-939d8d635209" />
<img width="780" height="497" alt="image" src="https://github.com/user-attachments/assets/ea2d686f-7478-4f52-b8e4-b65f7376ed01" />

Messaging using a broadcast system
first agents have a broadcast  phase where they place there message in each gridcell within their broadcast radius in the environment
then each agent has a receive phase where they read any messages nearby them and calculate if they should have received that message.
