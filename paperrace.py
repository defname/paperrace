'''
from game.pygamegui import UserInterface

ui = UserInterface()
ui.run()
print("Scoreboard:", ui.gamestate.scoreboard)
'''

from game.pygletgui import Main
from game.gamestate import PaperRaceGameState, PaperRacePointType, Coord


if __name__ == '__main__':
    gamestate = PaperRaceGameState()
    gamestate.load_map("maps/map4.ini")
    main = Main(gamestate)

    main.run()
