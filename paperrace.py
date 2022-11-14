from game.pygletgui import Main  # GUI
from game.gamestate import PaperRaceGameState  # game logic
from game.agent import SimplePRAgent, SimplePRAgent2  # agents


if __name__ == '__main__':
    # main object for the game logic
    gamestate = PaperRaceGameState()

    # load a map and create 4 racers
    gamestate.load_map("maps/map10.ini", 4)

    # create agents controlling the racer with the given id
    # 2. argument is the id of the racer to control
    # 3. argument is the search depth for this kind of agent
    agent1 = SimplePRAgent2(gamestate, 0, 5)
    agent2 = SimplePRAgent2(gamestate, 1, 3)
    agent3 = SimplePRAgent2(gamestate, 2, 1)
    # this type of agent doesn't really look into the future, so it doesn't
    # need a search depth
    agent4 = SimplePRAgent(gamestate, 3)

    # create the gui
    main = Main(gamestate)

    # tell the gui which racers are controlled by an agent
    # just don't do it to controll a racer by yourself
    main.add_agent(agent1, agent1.racer_id)
    main.add_agent(agent2, agent2.racer_id)
    main.add_agent(agent3, agent3.racer_id)
    main.add_agent(agent4, agent4.racer_id)

    # run the gui
    main.run()

    # print out the score of finished racers
    print(gamestate.scoreboard)
