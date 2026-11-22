from position import Position
def sample(obstacles):
  #scheduler will return [defenders_history, attackers_history]
  #History:
  #History is an array of timesteps
  #Timestep is an array of position objects (data in position.x and position.y)
  #[[Position, Position, Position][Position, Position, Position]]
  #ex: Timestep 30, agent 4, x coordinate value
  #x = defenders_history[30][4].x

  #represents 3 defenders and 0 attackers for 5 timesteps
	return [
		[
			[Position(55.71, 30.53), Position(68.22, 12.05), Position(44.58, 90.21)],
			[Position(55.81, 30.53), Position(68.22, 12.15), Position(44.68, 90.31)],
			[Position(55.91, 30.53), Position(68.22, 12.25), Position(44.78, 90.41)],
			[Position(56.01, 30.53), Position(68.22, 12.35), Position(44.88, 90.51)],
			[Position(56.11, 30.53), Position(68.22, 12.45), Position(44.98, 90.61)]
		],
			[[],[],[],[],[]]
	]
