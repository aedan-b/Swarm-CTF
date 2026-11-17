import defender


def render(arena):
    for row in arena:
        row_string = ""
        for tile in row:
            if tile:
                row_string += "██"
            else:
                row_string += "  "
        print(row_string)




arena = [[0 for x in range(30)] for y in range(30)]

test = defender.Defender(0, [15,15])

circle = test.get_circle(10)
print(circle)

for point in circle:
    arena[point[0]][point[1]] = 1

render(arena)





