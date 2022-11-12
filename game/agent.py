from game.gamestate import PaperRaceGameState, PaperRacePointType
import random
import collections
import heapq
import copy


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
        raise NotImplementedError


class SimplePRAgent2(PRAgent):
    def __init__(self, gamestate, racer_id):
        super().__init__(gamestate, racer_id)

    def next_position(self):
        # return crash position if there is no choice
        if not self.racer.possible_next_positions:
            return self.racer.crash_position

        # current position of the agent's racer
        pos = self.racer.position
        best_score = (float("inf"), 0)
        best_position = None

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

            score = self._score(new_pos, old_pos)
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

    def _score(self, pos, old_pos, depth=5):
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
        
        best_score = (self.h[pos], -depth)
        
        for n in nh:
            if not self.gamestate.grid.is_reachable(pos, n):
                continue
            
            best_score = min(self._score(n, pos, depth-1), best_score)
            
        return best_score

class SimplePRAgent(PRAgent):
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


class BetterPRAgent(PRAgent):
    def __init__(self, gamestate, racer_id):
        super().__init__(gamestate, racer_id)

    def next_position(self):
        if not self.racer.possible_next_positions:
            return self.racer.crash_position

        best_score = float("inf")
        best_position = None
        for n in self.racer.possible_next_positions:
            score = self._score(n)
            if score < best_score:
                best_score = score
                best_position = n
        return best_position

    def _score(self, pos, old_pos=None, depth=3):
        if depth == 0:
            return self.h[pos]

        if old_pos is None:
            old_pos = self.racer.position
        speed = pos - old_pos

        biggertargetarea = False
        if pos in self.gamestate.grid.effects:
            effect = self.gamestate.grid.effects[pos]
            if effect.type == "SAND" or effect.type == "MULTISPEED":
                speed *= effect.config.getint("multiplier", 0)
            elif effect.type == "MAXSPEED":
                max_speed = effect.config.getint("maxspeed", 0)
                if abs(speed) > max_speed:
                    speed = max_speed / abs(speed) * speed
            elif effect.type == "BIGGERTARGETAREA":
                biggertargetarea = True

        next_positions = [pos] + self.gamestate.grid.neighbours(pos)

        best_score = float("inf")
        #best_pos = None
        for new_pos in next_positions:
            if not self.gamestate.grid.is_reachable(pos, new_pos):
                score = self.h[pos]*2
            else:
                score = self._score(new_pos, pos, depth-1) + self.h[pos]
            if score < best_score:
                best_score = score
                #best_pos = new_pos
        return best_score


class AStarPRAgent(PRAgent):
    def __init__(self, gamestate, racer_id):
        super().__init__(gamestate, racer_id)

    def next_position(self):
        target_node, came_from = self.a_star_search(1000)
        if len(came_from) == 0:
            return self.racer.crash_position

        if target_node is None:
            target_node = self.lowest_value_node(came_from)
        print(target_node, self.h[target_node])
        path = self.build_path(came_from, self.racer.position, target_node)
        return path[-2]

    def a_star_search(self, depth):
        openlist = []  # priority queue
        closedlist = set()

        costs = {}
        came_from = {}

        for s in self.racer.possible_next_positions:
            came_from[s] = self.racer.position
            costs[s] = 1
            speed = s - self.racer.position
            heapq.heappush(openlist, (self.h[s], s, speed, depth))

        while openlist:
            _, c_pos, c_speed, d = heapq.heappop(openlist)

            # destination area found
            #if c_pos in self.gamestate.grid.destarea:
            #    print("destination area reached")
            #    return c_pos, came_from

            # required depth is reached
            #if d == 0:
            #    return c_pos, came_from

            closedlist.add((c_pos, speed))

            ##########################################
            # expand node
            speed = self.apply_speed_effect(c_pos, speed)
            target_pos = c_pos+speed

            next_positions = []
            if self.gamestate.grid.is_reachable(c_pos, target_pos):
                next_positions = [target_pos]
            next_positions += self.gamestate.grid.neighbours(c_pos + speed)

            for n_pos in next_positions:
                n_speed = n_pos - c_pos

                #if (n_pos, n_speed) in closedlist:
                #    continue

                expected_costs = costs[c_pos] + 1

                if n_pos not in costs or costs[n_pos] > expected_costs:
                    costs[n_pos] = expected_costs
                    came_from[n_pos] = c_pos
                    f = self.h[n_pos] + costs[n_pos]
                    heapq.heappush(openlist, (f, n_pos, n_speed, d-1))

        # destination area not found
        print("End of loop")
        return None, came_from

    def lowest_value_node(self, came_from):
        return min(came_from, key=lambda p: self.h[p])

    def build_path(self, came_from, start, end):
        if start == end:
            return [start]
        if start not in came_from.values() or end not in came_from:
            return []

        path = []
        node = end
        while node != start:
            path.append(node)
            node = came_from[node]
        path.append(start)

        return path

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


class DFSPRAgent(PRAgent):
    """Super time consuming...

    cause of the deepcopy for every iteration, I guess
    """
    def __init__(self, gamestate, racer_id):
        super().__init__(gamestate, racer_id)

    def next_position(self):
        self.calls = 0
        best_score = self.max_h+10
        best_pos = None
        next_positions = sorted(self.racer.possible_next_positions, key=lambda p: self.h[p])
        if len(next_positions) == 0:
            return self.racer.crash_position
        for pos in next_positions:
            gs_copy = copy.deepcopy(self.gamestate)
            gs_copy.goto(pos)
            score = self._score_position(gs_copy)
            print(pos, score)
            if score < best_score:
                best_score = score
                best_pos = pos
        print(best_score)
        print(self.calls)
        return best_pos

    def _score_position(self, gamestate: PaperRaceGameState, max_score=float("inf"), depth=1):
        self.calls += 1
        pos = gamestate.racer[self.racer_id].position
        if pos in gamestate.grid.destarea:
            return 0
        if depth == 0:
            return self.h[pos]

        while gamestate.current_racer_id != self.racer_id:
            if len(gamestate.current_racer().possible_next_positions) > 0:
                random_pos = random.choice(tuple(gamestate.current_racer().possible_next_positions))
            else:
                random_pos = gamestate.current_racer().crash_position
            gamestate.goto(random_pos)

        next_positions = gamestate.racer[self.racer_id].possible_next_positions
        if len(next_positions) == 0:
            next_positions = [gamestate.racer[self.racer_id].crash_position]
        next_positions = sorted(next_positions, key=lambda p: self.h[p])

        best_score = self.max_h+10
        for n in next_positions:
            gs_copy = copy.deepcopy(gamestate)
            gs_copy.goto(n)
            score = self._score_position(gs_copy, best_score, depth-1)
            if score < best_score:
                best_score = score
                if score > max_score:
                    return max_score

        return best_score
