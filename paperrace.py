from game.pygletgui import Main
from game.gamestate import PaperRaceGameState
from game.agent import SimplePRAgent, SimplePRAgent2


if __name__ == '__main__':
    gamestate = PaperRaceGameState()
    gamestate.load_map("maps/map10.ini", 4)
    agent1 = SimplePRAgent2(gamestate, 0, 5)
    agent2 = SimplePRAgent2(gamestate, 1, 3)
    agent3 = SimplePRAgent2(gamestate, 2, 1)
    agent4 = SimplePRAgent(gamestate, 3)
    
    main = Main(gamestate)
    main.add_agent(agent1, agent1.racer_id)
    main.add_agent(agent2, agent2.racer_id)
    main.add_agent(agent3, agent3.racer_id)
    main.add_agent(agent4, agent4.racer_id)

    main.run()

    print(gamestate.scoreboard)
