# defenders have more "abilities" than you attacker
# those extra abilities are here

# for the defender, the extension will consist of:
  # messaging
  # coordination
class Defender(Agent):
	def __init__(self, id, position):
		self.broadcast = []
		self.messages = [Message]

	def readMessages(self):
		#grab messages from location
		#check actual distance
		self.messages = []
