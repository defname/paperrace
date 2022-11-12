from game.pygletgui import Main
from game.gamestate import PaperRaceGameState
from game.agent import PRAgent, SimplePRAgent, DFSPRAgent, BetterPRAgent, AStarPRAgent, SimplePRAgent2


if __name__ == '__main__':
    gamestate = PaperRaceGameState()
    gamestate.load_map("maps/map4.ini", 2)
    #agent1 = SimplePRAgent(gamestate, 0)
    agent2 = SimplePRAgent2(gamestate, 1)
    
    main = Main(gamestate)
    #main.add_agent(agent1, agent1.racer_id)
    main.add_agent(agent2, agent2.racer_id)

    main.run()

    print(gamestate.scoreboard)
