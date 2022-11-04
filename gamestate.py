from PIL import Image
import itertools
from enum import Enum
import operator
import configparser
import random

class Coord(tuple):
    def __add__(self, other):
        return Coord(x + y for x, y in zip(self, other))
    
    def __sub__(self, other):
        return Coord(x - y for x, y in zip(self, other))

    def __rmul__(self, other):
        if isinstance(other, (Coord, tuple, list)):
            return sum([x * y for x, y in zip(self, other)])
        return Coord(other * x for x in self)
    
    __lmul__=__rmul__
    
    def __truediv__(self, other):
        return Coord(x/other for x in self)

    def __round__(self):
        return Coord(map(round, self))

    def __abs__(self):
        return max(map(abs, self))
    
    def scalar_multiplication(self, other):
        return sum([x * y for x, y in zip(self, other)])

def lines_intersect(line1, line2):
    P0, P1 = line1
    Q0, Q1 = line2
    d = (P1[0]-P0[0]) * (Q1[1]-Q0[1]) + (P1[1]-P0[1]) * (Q0[0]-Q1[0]) 
    if d == 0:
        return None
    t = ((Q0[0]-P0[0]) * (Q1[1]-Q0[1]) + (Q0[1]-P0[1]) * (Q0[0]-Q1[0])) / d
    u = ((Q0[0]-P0[0]) * (P1[1]-P0[1]) + (Q0[1]-P0[1]) * (P0[0]-P1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return round(P1[0] * t + P0[0] * (1-t)), round(P1[1] * t + P0[1] * (1-t))
    return None

class PaperRacePointType(Enum):
    Street = 1
    Block  = 2
    Effect = 4

class PaperRaceGrid:
    def __init__(self, config):
        self.config = config
        self.init_grid(0,0)
        self.effects = dict()

    def init_grid(self, w, h):
        self.width = w
        self.height = h
        self.grid = dict({ (x,y): 0 for x, y in itertools.product(range(self.width), range(self.height)) })
        self.startarea = set()
        self.destarea = set()

    def __getitem__(self, position):
        return self.grid.get(position)

    def items(self):
        return self.grid.items()
    
    def values(self):
        return self.grid.values()

    def in_range(self, position):
        return position in self.grid

    def is_accessable(self, position):
        return self.in_range(position) and self.grid[position] != PaperRacePointType.Block
    
    def is_reachable(self, start, dest):
        line = self.line(start, dest)
        for p in line:
            if not self.is_accessable(p):
                return False
        return True

    def load_from_bitmap(self, filename):
        cell_size = 20
        im = Image.open(filename, "r")
        im_rgb = im.convert("RGB")
        w, h = im.size

        self.init_grid(w//cell_size, h//cell_size)
        
        for x, y in self.grid:
            pixel = im_rgb.getpixel(((x+0.5)*cell_size, (y+0.5)*cell_size))
            if pixel == self.config.blockcolor:
                self.grid[x, y] = PaperRacePointType.Block
            elif pixel == self.config.streetcolor:
                self.grid[x, y] = PaperRacePointType.Street
            elif pixel == self.config.startcolor:
                self.startarea.add((x,y))
                self.grid[x, y] = PaperRacePointType.Street
            elif pixel == self.config.destcolor:
                self.destarea.add((x,y))
                self.grid[x, y] = PaperRacePointType.Street
            else:
                if pixel in self.config.effects:
                    self.effects[x,y] = self.config.effects[pixel]
                self.grid[x, y] = PaperRacePointType.Effect

    def dist(self, p1, p2):
        return max([abs(v1-v2) for v1, v2 in zip(p1,p2)])

    def line(self, p1, p2):
        distance = self.dist(p1, p2)
        l = list()
        for i in range(distance):
            p = p1 + (i/distance)*(p2-p1)
            
            l.append(round(p))
        l.append(p2)
        return l

    def neighbours(self, p):
        nh = [p + d for d in [(0,1), (0,-1), (1,0), (-1,0), (1,-1), (-1,-1), (-1,1),(1,1)]]
        nh = [p for p in nh if self.is_accessable(p)]
        return nh

class PREffectType(Enum):
    SpeedEffect = 1
    TargetAreaEffect = 2

class PREffect:
    def __init__(self, type, racer, duration, priority=1):
        self.type = type
        self.racer = racer
        self.duration = duration
        self.priority = priority

    def apply(self):
        if self.duration == 0:
            return False
        self.duration -= 1
        print("Apply effect", type(self), "on", self.racer.id, "duration:", self.duration)
        return True

class PRMaxSpeedEffect(PREffect):
    def __init__(self, racer, duration=3, max_speed=1, priority=1):
        super().__init__(PREffectType.SpeedEffect, racer, duration, priority)
        self.max_speed = max_speed

    def apply(self):
        if not super().apply():
            return False
        if abs(self.racer.speed) > 0:
            self.racer.speed = round((self.max_speed / abs(self.racer.speed)) * self.racer.speed)
        return True

class PRMultiSpeedEffect(PREffect):
    def __init__(self, racer, multiplier=0.5, priority=1):
        super().__init__(PREffectType.SpeedEffect, racer, 1, priority)
        self.multiplier = multiplier

    def apply(self):
        if not super().apply():
            return False
        if abs(self.racer.speed) > 0:
            self.racer.speed = round(self.multiplier * self.racer.speed)
        return True

class PRSandEffect(PRMultiSpeedEffect):
    def __init__(self, racer):
        super().__init__(racer, 0.5, 1)

class PRCrashEffect(PRMaxSpeedEffect):
    def __init__(self, racer):
        super().__init__(racer, 10, 0, 5)

class PRBiggerTargetAreaEffect(PREffect):
    def __init__(self, racer, duration, priority=1):
        super().__init__(PREffectType.TargetAreaEffect, racer, duration, priority)

    def apply(self):
        if not super().apply():
            return False
        next_positions = set()
    
        for p in self.racer.possible_next_positions:
            next_positions |= set(self.racer.grid.neighbours(p))
        self.racer.possible_next_positions = list(next_positions)



class PaperRacer:
    def __init__(self, id, grid, gamestate, position):
        self.id = id
        self.grid = grid
        self.gamestate = gamestate
        self.position = Coord(position)
        self.speed = Coord((0,0))
        self.path = [self.position]

        self.possible_next_positions = list()
        self.calc_possible_next_positions()
        self.crash_position = None

        self.effects = list()

    def calc_possible_next_positions(self):
        self.possible_next_positions.clear()
        #next_positions = [
        #    self.position + self.speed + d 
        #    for d in [(0,0), (0,1), (0,-1), (1,0), (-1,0)]
        #]
        next_positions = [self.position + self.speed]+self.grid.neighbours(self.position + self.speed)
        self.possible_next_positions = [p for p in next_positions if self.grid.is_reachable(self.position, p)]
        
        # if there is no position reachable with current speed
        # set crash_position to the last possible position
        if not self.possible_next_positions:
            line = self.grid.line(self.position, self.position+self.speed)
            for p in line:
                if self.grid.is_accessable(p):
                    self.crash_position = p
                else:
                    break
    
    def evaluate_position(self):
        if self.grid[self.position] == PaperRacePointType.Effect:
            if self.position in self.grid.effects:
                self.add_effect(self.grid.effects[self.position].createNewEffectObj(self))
            else:
                print("No effect associated!")

    def add_effect(self, effect):
        self.effects.append(effect)
        self.effects.sort(key=lambda e: e.priority)

    def apply_effects(self, effect_type):
        remove_list = list()
        for effect in filter(lambda e: e.type == effect_type, self.effects):
            effect.apply()
            # mark ended effects for deletion 
            if effect.duration == 0:
                remove_list.append(effect)
        # delete old effects
        for e in remove_list:
            self.effects.remove(e)

    def goto(self, position):
        position = Coord(position)
        new_position = None
        if self.crash_position is not None:
            new_position = self.crash_position
            self.crash_position = None
            self.add_effect(PRCrashEffect(self))
            self.speed = Coord((0,0))
        elif position in self.possible_next_positions:
            other_racer = self.gamestate.racer_on_position(position)
            if other_racer is not None:
                # Crash between two racer
                line = self.grid.line(other_racer.position, self.position)
                new_position = line[1]

                effect = PRMaxSpeedEffect(other_racer, 2, 0, 10)
                effect.apply()
                other_racer.calc_possible_next_positions()
                self.add_effect(PRMaxSpeedEffect(self, 1, 0, 10))
            else:
                new_position = position
            self.speed = new_position - self.position
        
        # given position is not reachable
        if new_position == None:
            return False
        
        self.position = new_position
        self.path.append(new_position)

        # check position for effects caused by it
        self.evaluate_position()

        # apply effects on the speed of the racer
        self.apply_effects(PREffectType.SpeedEffect)

        # calc the possible next positions
        self.calc_possible_next_positions()

        # apply effects on the possible next positions
        self.apply_effects(PREffectType.TargetAreaEffect)

        return True

class PREffectConfig:
    def __init__(self, conf):
        self.type = conf["type"]
        self.config = conf

    def createNewEffectObj(self, racer):
        if self.type == "SAND":
            return PRSandEffect(racer)
        elif self.type == "MULTISPEED":
            multiplier = self.config.getint("multiplier", 0)
            priority = self.config.getint("priority", 1)
            return PRMultiSpeedEffect(racer, multiplier, priority)
        elif self.type == "MAXSPEED":
            maxspeed = self.config.getint("multiplier", 1)
            priority = self.config.getint("priority", 1)
            duration = self.config.getint("duration", 5)
            return PRMaxSpeedEffect(racer, duration, maxspeed, priority)
        elif self.type == "BIGGERTARGETAREA":
            priority = self.config.getint("priority", 1)
            duration = self.config.getint("duration", 5)
            return PRBiggerTargetAreaEffect(racer, duration, priority)
        else:
            raise NameError("Invalid effect type", self.type, "in config")

class PRConfig:
    def __init__(self):
        pass

    def str_to_color(self, s):
        if s is None:
            raise NameError("invalid color")
        return tuple(map(int, s.split(",")))

    def load_map(self, filename):
        cp = configparser.ConfigParser()
        
        with open(filename) as fp:
            cp.read_file(itertools.chain(['[global]'], fp), source=filename)
        
        if "General" not in cp.sections():
            raise NameError("No [General] section in", filename)
        
        if "mapfile" not in cp["General"]:
            raise NameError("No mapfile specified in", filename)
        self.map_filename = cp["General"]["mapfile"]

        self.map_name = cp["General"].get("name", "Default Level Name")
        self.map_image_gridsize = cp["General"].getint("gridsize", 20)
        self.ui_background_image = cp["General"].get("ui_bgimage", "None")
        self.ui_background_color = self.str_to_color(cp["General"].get("ui_bgcolor", "255,255,255"))
        self.blockcolor = self.str_to_color(cp["General"].get("blockcolor", "0,0,0"))
        self.streetcolor = self.str_to_color(cp["General"].get("streetcolor", "255,255,255"))
        self.startcolor = self.str_to_color(cp["General"].get("startcolor", "0,255,0"))
        self.destcolor = self.str_to_color(cp["General"].get("destcolor", "0,255,0"))

        self.effects = dict()
        for sec in cp.sections():
            if sec == "global" or sec == "General":
                continue
            if sec.startswith("effect:"):
                name = sec[7:]
                if "mapcolor" not in cp[sec]:
                    raise NameError("mapcolor not specified in effect section")
                color = self.str_to_color(cp[sec].get("mapcolor"))
                self.effects[color] = PREffectConfig(cp[sec])
        


class PaperRaceGameState:
    def __init__(self):
        self.config = PRConfig()
        self.grid = PaperRaceGrid(self.config)
        self.scoreboard = dict()

    def load_map(self, filename):
        self.config.load_map(filename)

        self.grid.load_from_bitmap(self.config.map_filename)

        self.racer = dict()

        self.scoreboard.clear()
        self.finished = False
        self.racer[0] = PaperRacer(0, self.grid, self, random.choice(list(self.grid.startarea)))
        self.racer[1] = PaperRacer(1, self.grid, self, random.choice(list(self.grid.startarea)))
        #self.racer[1].speed = Coord((3,1))
        self.current_racer_id = 0

    def current_racer(self):
        return self.racer[self.current_racer_id]

    def goto(self, position):
        if not self.current_racer().goto(position):
            print("Something went wrong")
            return False
        if self.current_racer().position in self.grid.destarea:
            self.scoreboard[self.current_racer_id] = len(self.current_racer().path)
        self.next_player()

    def next_player(self):
        if len(self.scoreboard) >= len(self.racer):
            self.finished = True
            return
        self.current_racer_id += 1
        self.current_racer_id %= len(self.racer)
        if self.current_racer_id in self.scoreboard:
            self.next_player()

    def racer_on_position(self, position):
        for racer in self.racer.values():
            if racer.position == position:
                return racer
        return None

        

