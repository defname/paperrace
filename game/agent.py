from game.gamestate import PaperRaceGameState, PaperRacePointType
import random
import collections

class PRAgent:
    """Base class for a PaperRace agent

    Attributes:
        gamestate (PapaerRaceGameState): the main gamestate object
        racer_id (int): the id of the racer that should be controled by the
           agent
        h (dict[Coord, int]): heuristic for the rough distance between key
           and the destination area in the grid
    """

    def __init__(self, gamestate: PaperRaceGameState, racer_id: int):
        """Initialize the object"""
        self.gamestate = gamestate
        self.racer_id = racer_id
        self.racer = self.gamestate.racer[self.racer_id]
        self.h = {}
        self.max_h = float("inf")
        self._build_h()
        self.max_h = max(self.h.values())

    def _build_h(self, ):
        """Build the h dictionary.

        This is one of the key functions, since it builds the h dictionary
        which provides the heuristic for the distance from each point to the
        destination area (dictionary key is the point, the value is the
        distance).

        Might be overwritten to fit the agent's needs.

        In this specific heuristic streets are way cheaper than than sand,
        what might not be useful for agents that simulate some future steps.
        """
        start = random.choice(tuple(self.gamestate.grid.destarea))
        queue = collections.deque()
        queue.append(start)
        self.h[start] = 0
        visited = set()

        while queue:
            current = queue.popleft()
            visited.add(current)

            nh = self.gamestate.grid.neighbours(current)
            for n in nh:
                if self.gamestate.grid[n] == PaperRacePointType.BLOCK:
                    continue
                else:
                    if self.gamestate.grid[current] == PaperRacePointType.STREET:
                        if self.gamestate.grid[n] == PaperRacePointType.STREET:
                            costs = self.h[current] + 5
                        else:
                            costs = self.h[current] + 10
                    elif current in self.gamestate.grid.destarea:
                        costs = self.h[current]
                    else:
                        if current in self.gamestate.grid.effects:
                            effect = self.gamestate.grid.effects[current]
                            costs = self.h[current] + 5
                            if effect.type == "SAND":
                                costs = self.h[current] + 10
                            elif effect.type == "MULTISPEED":
                                pass
                            elif effect.type == "MAXSPEED":
                                costs = self.h[current] + 10
                            elif effect.type == "BIGGERTARGETAREA":
                                costs = self.h[current] + 1
                        else:
                            costs = self.h[current] + 5
                        if n in self.gamestate.grid.effects:
                            effect = self.gamestate.grid.effects[n]
                            if effect.type == "SAND" or effect.type == "MAXSPEED":
                                costs += 10
                                pass
                    if n not in self.h or self.h[n] > costs:
                        self.h[n] = costs
                        queue.append(n)

    def apply_speed_effect(self, pos, speed):
        """Apply an effect associated with the given position.

        Check if there is an effect associated with the given position, apply
        it to the the given speed and return the result.

        Args:
            pos (Coord):  position of the field to check for effects
            speed (Coord): current speed

        Returns:
            (Coord) Return the changed speed. If no effect associated return
            the unchanged speed.
        """
        if pos in self.gamestate.grid.effects:
            effect = self.gamestate.grid.effects[pos]
            if effect.type == "SAND" or effect.type == "MULTISPEED":
                speed = effect.config.getint("multiplier", 0) * speed
            elif effect.type == "MAXSPEED":
                max_speed = effect.config.getint("maxspeed", 0)
                if abs(speed) > max_speed:
                    speed = (max_speed / abs(speed)) * speed
        return round(speed)

    def next_position(self):
        """Return the position, the agent's racer should move to.

        This is the method that should be called by the GUI to get the
        agent's next move to hand it over to the PaperRacerGameState.goto()
        method.
        
        This method has to be overloaded by child classes.

        It has to return a position from the racer's possible_next_positions
        list or if it's empty the racer's crash_position, otherwise
        PaperRacerGameState respectively PRRacer will produce errors
        and might crash.

        Returns:
            (Coord) the position the agent should move to.
        """
        raise NotImplementedError


class SimplePRAgent2(PRAgent):
    """Little bit better version of a simple agent.

    This one makes a very simple simulation of it's own next few moves.
    Some effects are applied to modify the speed according to effects on the
    map, but only once, so the duration property of the effects have no
    influence.

    To simulate future steps, only the best, least and middle rated position
    from possible_next_positions (according to PRAgent.h heuristic) is used,
    to limit the branching factor.

    Since the original heuristic produce wierd behaviour in some situations
    the sand fields are changed to less costs (In some situations it is just
    better to go over sand fields), since the agent put the negative effects
    of using this fields in calculation.

    With the search_depth attribute the number of future steps to simulate
    can be specified, what leads to very different behaviours.
    Suprisingly the result is not necessarily better with a better search
    depth. I sadly don't have an explanation for this.

    It's interesting to play around with the used heuristic (somethimes best
    results are produced with the simplest heuristic that only give the
    distance to the destination area indipendendly from the type of the
    field) and different search depths.
    """
    
    def __init__(self, gamestate, racer_id, search_depth=5):
        """Initialize agent

        Args:
            look at PRAgent.init()
            search_depth (int): number of steps to simulate
        """
        super().__init__(gamestate, racer_id)
        self._build_h()
        self.search_depth = search_depth

    def next_position(self):
        # return crash position if there is no choice
        if not self.racer.possible_next_positions:
            print("Agent goes to crash position")
            return self.racer.crash_position

        # current position of the agent's racer
        pos = self.racer.position

        best_position = min(self.racer.possible_next_positions, key=lambda p: self.h[p])
        #best_score = (float("inf"), 0)
        best_score = (self.h[best_position], 0)

        # choose the most promising position
        for new_pos in self.racer.possible_next_positions:
            if new_pos in self.gamestate.grid.destarea:
                return new_pos

            if new_pos == self.racer.position:
                continue

            old_pos = self.racer.position

            if self.gamestate.racer_on_position(new_pos) and self.gamestate.racer_on_position(new_pos).id!=self.racer_id:
                line = self.gamestate.grid.line(new_pos, self.racer.position)
                new_pos = line[1]
                old_pos = line[1]

            score = self._score(new_pos, old_pos, self.search_depth)
            #new_pos2 = pos + 2 * speed
            #if self.gamestate.grid.is_reachable(pos, new_pos2) and self.h[new_pos2] < self.h[new_pos]:
            #    score *= self.h[new_pos2]/self.max_h

            if score < best_score:
                best_score = score
                best_position = new_pos
        return best_position

    def neighbours(self, pos):
        nh = sorted(self.gamestate.grid.neighbours(pos), key=lambda p: self.h[p])
        if not nh:
            return []
        #return random.choices(self.gamestate.grid.neighbours(pos), k=2)
        return [nh[0], nh[len(nh)//2], nh[-1]]

    def _score(self, pos, old_pos, depth=6):
        if pos in self.gamestate.grid.destarea and pos != self.racer.position:
            return (0, -depth)

        if depth == 0:
            return (self.h[pos], -depth)

        if pos in self.racer.path:
            return (self.h[pos]+1, -depth)

        speed = pos - old_pos
        speed = self.apply_speed_effect(pos, speed)

        new_target = pos + speed

        #nh = self.gamestate.grid.neighbours(new_target)
        nh = self.neighbours(new_target)
        if not nh:
            return (self.h[pos], -depth)

        #best_score = (self.h[pos], -depth)
        best_score = (float("inf"), -depth)

        for n in nh:
            if not self.gamestate.grid.is_reachable(pos, n):
                continue

            best_score = min(self._score(n, pos, depth-1), best_score)

        return best_score

    def _build_h(self, ):
        """Build the h dictionary.

        This is one of the key functions, since it builds the h dictionary
        which provides the heuristic for the distance from the point (working
        as key) to the destination area. As better this heuristic is, as
        better every search algorithm will work.
        """
        start = random.choice(tuple(self.gamestate.grid.destarea))
        queue = collections.deque()
        queue.append(start)
        self.h[start] = 0
        visited = set()

        while queue:
            current = queue.popleft()
            visited.add(current)

            nh = self.gamestate.grid.neighbours(current)
            for n in nh:
                if self.gamestate.grid[n] == PaperRacePointType.BLOCK:
                    continue
                else:
                    if current in self.gamestate.grid.destarea:
                        costs = 0
                    elif self.gamestate.grid[current] == PaperRacePointType.STREET:
                        if self.gamestate.grid[n] == PaperRacePointType.STREET:
                            costs = self.h[current] + 1
                        else:
                            costs = self.h[current] + 1.5
                    else:
                        costs = self.h[current] + 1.5

                    if n not in self.h or self.h[n] > costs:
                        self.h[n] = costs
                        queue.append(n)


class SimplePRAgent(PRAgent):
    """A simple agent without any simulation.

    It's choices mainly depends on the heuristic. To limit the speed and
    prevent the agent to get too fast it checks the points in the current
    direction with same speed (or changed speed if an effect is hit) if they
    are reachable and score them less good if not.

    Works suprisingly good, but it's also not a winner type of agent.
    """
    def __init__(self, gamestate, racer_id):
        super().__init__(gamestate, racer_id)

    def next_position(self):
        # return crash position if there is no choice
        if not self.racer.possible_next_positions:
            return self.racer.crash_position

        # current position of the agent's racer
        pos = self.racer.position
        best_score = float("inf")
        best_position = None

        # choose the most promising position
        for new_pos in self.racer.possible_next_positions:
            if new_pos in self.gamestate.grid.destarea:
                return new_pos

            if self.gamestate.racer_on_position(new_pos):
                score = (self.h[new_pos])/(self.max_h)
                speed = new_pos - pos
                if abs(speed) > 0:
                    speed = round((1/abs(speed)) * speed)
            else:
                score = self.h[new_pos]/self.max_h

                speed = new_pos - pos
                speed = self.apply_speed_effect(new_pos, speed)
            new_pos1 = new_pos
            new_pos2 = pos + speed
            for i in range(1, abs(speed)):
                if self.gamestate.grid.is_reachable(new_pos1, new_pos2):
                    #if self.h[new_pos2] < self.h[new_pos1]:
                        score *= self.h[new_pos2]/self.max_h
                else:
                    break
                if new_pos2 in self.gamestate.grid.destarea:
                    return new_pos
                new_pos1 = new_pos2
                speed = self.apply_speed_effect(new_pos1, speed)
                new_pos2 = new_pos1 + speed

            #new_pos2 = pos + 2 * speed
            #if self.gamestate.grid.is_reachable(pos, new_pos2) and self.h[new_pos2] < self.h[new_pos]:
            #    score *= self.h[new_pos2]/self.max_h

            if score < best_score:
                best_score = score
                best_position = new_pos
        return best_position

    def apply_speed_effect(self, pos, speed):
        if pos in self.gamestate.grid.effects:
            effect = self.gamestate.grid.effects[pos]
            if effect.type == "SAND" or effect.type == "MULTISPEED":
                speed = effect.config.getint("multiplier", 0) * speed
            elif effect.type == "MAXSPEED":
                max_speed = effect.config.getint("maxspeed", 0)
                if abs(speed) > max_speed:
                    speed = (max_speed / abs(speed)) * speed
        return round(speed)
