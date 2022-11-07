"""PaperRacer game logic.

The game basically plays on a sheet of quad paper, on which a racetrack is
drawn. The player's start positions are in a marked starting area, and the
goal is to reach a marked target area. The positions are *on* the crosses not
inside the squares. A player can move by choosing one of the eight neighbour
points of it's own position. The speed vector is the vector between last to
points. The next position at same
speed will be the position by adding the speed vector to the current position.
The player can choose if he wants to move to the next position without
changing speed or choose one of the eight neighbours of this point.

For example:
    +--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
    +--+-(S)-+--+--+--+--+--+--+--+--+--+--+--+
    |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
    +--+--+--+--+--+-(T)-+--+--1--2--3--+--+--+
    |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
    +--+--+--+--+--+--+--+--+--8-(N)-4--+--+--+
    |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
    +--+--+--+--+--+--+--+--+--7--6--5--+--+--+
    |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
    +--+--+--+--+--+--+--+--+--+--+--+--+--+--+
If the last move was from (S) to (T), the speed is (4,1), so the next point
(with same speed) would be (N). The player can choose either (N) or 1-8 as
it's next position.

Additional to this basic movement there will be effects on the speed and the
target area (next point + neighbours), like half speed each time landing
outside sthe track, minimal speed for some rounds in case of a crash, etc.
"""

from PIL import Image
import itertools
from enum import Enum
import configparser
import random


class Coord(tuple):
    """Used for positions, vectors, etc. Basically tuples, with the
    possibility for basic calculation
    """
    def __add__(self, other):
        return Coord(x + y for x, y in zip(self, other))

    def __sub__(self, other):
        return Coord(x - y for x, y in zip(self, other))

    def __rmul__(self, other):
        """Elementwise mulitplication with a scalar"""
        return Coord(other * x for x in self)

    __lmul__ = __rmul__

    def __truediv__(self, other):
        """Elementwise division with a scalar. other must not be 0"""
        return Coord(x/other for x in self)

    def __round__(self):
        return Coord(map(round, self))

    def __abs__(self):
        """Absolute value, according to manhatten distance"""
        return max(map(abs, self))

    def scalar_multiplication(self, other):
        return sum([x * y for x, y in zip(self, other)])


class PaperRacePointType(Enum):
    """Different types of points on the grid"""
    STREET = 1
    BLOCK = 2
    EFFECT = 4


class PaperRaceGrid:
    """Represent the paper, on which the game is played"""

    def __init__(self, config):
        """Initialize object. Called by PaperRacerGameState

        Main initialization is done by PaperRaceGrid.init_grid()

        Args:
            config (PRConfig): PRConfig object with the filename of the
              used bitmap, and other information relevant for this class
        """
        self.config = config
        # init empty grid, just to initialize class properties
        self.init_grid(0, 0)
        self.effects = {}

    def init_grid(self, w, h):
        """Initialize grid.

        Set the correct width and height and initialize the grid with zeros.

        Args:
            w (int): width of the grid
            h (int): height of the grid

        Note:
            w and h are measured in game coordinates, not pixels.
        """
        self.width = w
        self.height = h
        # init grid with zeros
        self.grid = dict({
                (x, y): 0
                for x, y
                in itertools.product(
                    range(self.width), range(self.height)
                )
            })
        self.startarea = set()
        self.destarea = set()

    def __getitem__(self, position):
        """Get the type of the point at given position.

        Just a shortcut...

        Args:
            position (Coord): position

        Returns:
            (PaperRacerPointType) STREET, EFFECT or BLOCK
        """
        return self.grid.get(position)

    def items(self):
        """Shortcut to self.grid.items()"""
        return self.grid.items()

    def values(self):
        """Shortcut to self.grid.values()"""
        return self.grid.values()

    def in_range(self, position):
        """Check if position is on the grid.

        Args:
            position (Coord): position

        Returns:
            (bool)
        """
        return position in self.grid

    def is_accessable(self, position):
        """Check if a position in the grid is accessable.

        Can a racer move to this position in principle?

        Args:
            position (Coord): position to check

        Returns:
            (bool)
        """
        return self.in_range(position) \
            and self.grid[position] != PaperRacePointType.BLOCK

    def is_reachable(self, start, dest):
        """Check if a position on the grid is reachable from another position.

        Args:
            start (Coord): position on the grid
            dest (Coord): position on the grid

        Returns:
            (bool) True if dest is reachable from start, that means it's
            possible for a racer to move from start to dest without crashing
            into a PaperRacerPointType.BLOCK field (which would cause a
            PRCrashEffect). False otherwise
        """
        line = self.line(start, dest)
        for p in line:
            if not self.is_accessable(p):
                return False
        return True

    def load_from_bitmap(self, filename):
        """Load the grid from a bitmap file.

        Load the grid from a bitmap file according to the gridsize and the
        colors specified in the PRConfig object refered to by the config
        property.

        Note:
            The bitmap file should not be compressed or with best quality, so
            that the color values of the pixels are not affected by noise or
            similar effects.

        Args:
            filename (str): filename of the bitmap relative to the file
              executed (should be paperrace.py).
        """
        cell_size = self.config.map_image_gridsize
        im = Image.open(filename, "r")
        im_rgb = im.convert("RGB")
        w, h = im.size

        self.init_grid(w//cell_size, h//cell_size)

        for x, y in self.grid:
            pixel = im_rgb.getpixel(((x+0.5)*cell_size, (y+0.5)*cell_size))
            if pixel == self.config.blockcolor:
                self.grid[x, y] = PaperRacePointType.BLOCK
            elif pixel == self.config.streetcolor:
                self.grid[x, y] = PaperRacePointType.STREET
            elif pixel == self.config.startcolor:
                self.startarea.add((x, y))
                self.grid[x, y] = PaperRacePointType.STREET
            elif pixel == self.config.destcolor:
                self.destarea.add((x, y))
                self.grid[x, y] = PaperRacePointType.STREET
            else:
                if pixel in self.config.effects:
                    self.effects[x, y] = self.config.effects[pixel]
                self.grid[x, y] = PaperRacePointType.EFFECT

    def dist(self, p1, p2):
        """Return the manhatten distance between two points."""
        return max([abs(v1-v2) for v1, v2 in zip(p1, p2)])

    def line(self, p1, p2):
        """Return all points on the line between two points.

        Args:
            p1 (Coord): position of the starting point of the line
            p2 (Coord): position of the end point

        Returns:
            (list) All points on the line. First element of the list is
            p1, last element is p2. If p1 == p2 the list has only one
            element.
        """
        distance = self.dist(p1, p2)
        line = list()
        for i in range(distance):
            p = p1 + (i/distance)*(p2-p1)

            line.append(round(p))
        line.append(p2)
        return line

    def neighbours(self, p):
        """Return a list of all neighbours of p.

        Args:
            p (Coord): position on the grid

        Returns:
            (list) of all neighbours of p, that are accessable (accoring
            to PaperRaceGrid.is_accessable()).
        """
        nh = [
            p + d
            for d
            in [(0, 1), (0, -1), (1, 0), (-1, 0),
                (1, -1), (-1, -1), (-1, 1), (1, 1)]
        ]
        nh = [p for p in nh if self.is_accessable(p)]
        return nh


class PREffectType(Enum):
    """Specify diferent types of effects"""
    SpeedEffect = 1
    TargetAreaEffect = 2


class PREffect:
    """Baseclass for effects that can occur.

    For each effect triggered by a racer by hitting a point on the grid
    associated with an effect, an PREffect object (respectivly an object
    of a child class) is created by the PRRacer object.
    PREffect.apply() is called by PRRacer during the PRRacer.goto().
    The exact time it is called depends on the type of the effect.


    Attributes:
        type (PREffectType): this decides on which point during the
           PRRacer.goto() call the effect is applied
        racer (PRRacer): the racer on which the effect is applied
        duration (int): positive integer for the number of rounds the effect
           has impact. If it's down to 0 the effect has ended and the object
           can be deleted.
        priority (int): Number between 1 and 10 deciding when within the
           other effects of the same type this effect is applied.
           As higher the number as later it is applied.

    Todo:
        * Add the possibility to trigger an effect by just passing a point
    """

    def __init__(self, etype, racer, duration, priority=1):
        self.type = etype
        self.racer = racer
        self.duration = duration
        self.priority = priority

    def apply(self):
        """Apply the effect defined by this object.

        This function is usually called by the PRRacer object which also
        created the effect. There might be exceptions, like if a crash
        between two racers happen, the racer which caused the crash needs
        also to create and apply an effect for the other racer.

        This function must be overloaded AND called by child classes.
        """
        if self.duration == 0:
            return False
        self.duration -= 1
        print("Apply effect", type(self), "on", self.racer.id,
              "duration:", self.duration)
        return True


class PRMaxSpeedEffect(PREffect):
    """Effect that limits the speed of the racer to a maximum value"""

    def __init__(self, racer, duration=3, max_speed=1, priority=1):
        """Initialize the object

        Args:
            racer (PRRacer): the racer on which the effect should be appplied
            duration (int): positive number for the number of rounds the effect
               should occur (default: 3)
            max_speed (int): the maximum to which the racer's speed will be
               limited (default: 3)
            priority (int): number between 1 and 10. As higher the priority as
              later the effect will be applied. The default value can be used
              for most cases (default: 1)
        """
        super().__init__(PREffectType.SpeedEffect, racer, duration, priority)
        self.max_speed = max_speed

    def apply(self):
        if not super().apply():
            return False
        if abs(self.racer.speed) > self.max_speed:
            self.racer.speed = round((
                self.max_speed / abs(self.racer.speed)) * self.racer.speed)
        return True


class PRMultiSpeedEffect(PREffect):
    """Effect that multiplies the speed with a number"""

    def __init__(self, racer, multiplier=0.5, priority=1):
        """Initialize the object

        Args:
            racer (PRRacer): the racer on which the effect should be appplied
            multiplier (float): positive float number with which the speed
               of the racer will be multiplied (default: 0.5)
            priority (int): number between 1 and 10
        """
        super().__init__(PREffectType.SpeedEffect, racer, 1, priority)
        self.multiplier = multiplier

    def apply(self):
        if not super().apply():
            return False
        if abs(self.racer.speed) > 0:
            self.racer.speed = round(self.multiplier * self.racer.speed)
        return True


class PRSandEffect(PRMultiSpeedEffect):
    """Default effect for points outside the track.

    Half the speed every time a point with this effect is hit
    """
    def __init__(self, racer):
        super().__init__(racer, 0.5, 1)


class PRCrashEffect(PRMaxSpeedEffect):
    """Default effect for crashes.

    Occur if a racer tries to go to a point where another racer is already on
    """
    def __init__(self, racer):
        super().__init__(racer, 10, 0, 5)


class PRCollisionEffect(PRMaxSpeedEffect):
    """Default effect for collisions between two racers

    The effect is applied to both racers involved in the collision. To
    distinguish for which of the racers the effect is created the other
    parameter of the constructor method is used. So it's possible to
    define different consequences for the two racers.
    """

    def __init__(self, racer, other=False):
        """Initialize object.

        Args:
            racer (PRRacer): the racer on which the effect should be appplied
            other (bool): False if the effect is for the racer that caused the
               collision, True for the racer which is hitted. (default: False)
        """
        if other:
            super().__init__(racer, 2, 0, 10)
        else:
            super().__init__(racer, 1, 0, 10)


class PRBiggerTargetAreaEffect(PREffect):
    """Increase the target area of a racer

    Double the number of points the player can choose his move from

    Todo:
        * Add possibility to limit how often the effect can occur for one racer
    """

    def __init__(self, racer, duration, priority=1):
        super().__init__(PREffectType.TargetAreaEffect,
                         racer, duration, priority)

    def apply(self):
        if not super().apply():
            return False
        next_positions = set()

        for p in self.racer.possible_next_positions:
            next_positions |= set(self.racer.grid.neighbours(p))
        self.racer.possible_next_positions = list(next_positions)


class PaperRacer:
    """Paper racer objects represent a racer on the grid.

    Attributes:
        id (int): id of the racer. It's also used to check if two objects
           represent the same racer
        grid (PaperRacerGrid): the main grid
        gamestate (PaperRacerGameState): the main game object
        position (Coord): currrent position of the racer
        speed (Coord): current speed of the racer (as vector). It can be
           affected by PRMAXSpeedEffect objects and PRMultipleSpeedEffect
           objects
        path (list[Coord]): list of all points the racer has been. Last entries
           are the lates
        possible_nect_positions (list[Coord]): list of the positions the player
           can choose his next move from. This list is affected by
           PRTargetAreaEffect objects.
        effects (list[PREffect]): a list of effects currently affecting the
           racer. If the duration of an effect is down to 0 it will be deleted
        """

    def __init__(self, racer_id, grid, gamestate, position):
        """Initialize object

        Args:
            racer_id (int): id of the racer. It's used to check if two objects
               represent the same racer via the PRPaperRacer.__eq__() operator
            grid (PaperRacerGrid): main grid, on which the game is played.
               used to check whats on the grid, which target points possible,
               etc
            gamestate (PaperRacerGameState): main game object. Needed to check
               if other racers are on a target position
            positio (Coord): initial position of the racer
        """
        self.id = racer_id
        self.grid = grid
        self.gamestate = gamestate
        self.position = Coord(position)
        self.speed = Coord((0, 0))
        self.path = [self.position]

        self.possible_next_positions = list()
        self._calc_possible_next_positions()
        self.crash_position = None

        self.effects = list()

    def __eq__(self, other):
        return self.id == other.id

    def _calc_possible_next_positions(self):
        """Calculate the next possible positions.

        Calculate the next possible positions of which the player can choose
        his move from, based on current speed (PRRacer.speed), and obsticals
        on the grid. Store the results in PRRacer.next_possible_positions.

        If there is no position on the grid reachable at current speed set
        PRRacer.crash_position
        """
        # reset stuff
        self.possible_next_positions.clear()
        self.crash_position = None

        next_positions = [self.position + self.speed] \
            + self.grid.neighbours(self.position + self.speed)
        self.possible_next_positions = [
            p for p in next_positions
            if self.grid.is_reachable(self.position, p)
        ]

        # if there is no position reachable with current speed
        # set crash_position to the last possible position
        if not self.possible_next_positions:
            line = self.grid.line(self.position, self.position + self.speed)
            for p in line:
                if self.grid.is_accessable(p):
                    self.crash_position = p
                else:
                    break

    def _evaluate_position(self):
        """Add new effects associated with the current position

        Check if there is a effect associated with the current position and
        add it to the PRRacer.effects list if so.

        The method is called by PRacer.goto() after the new position is set
        """
        if self.grid[self.position] == PaperRacePointType.EFFECT:
            if self.position in self.grid.effects:
                self.add_effect(
                    self.grid.effects[self.position].createNewEffectObj(self)
                )
            else:
                print("No effect associated!")

    def add_effect(self, effect):
        """Add an effect to the PRRacer.effects list.

        Add e new effect to the effects list, that should be applied as long
        as it is active. The method is called by PRRacer._evaluate_position()
        to add effects to itself and in case of a crash by PRRacer.goto()
        for the objecct itself and the other PRRacer object this one crashed
        into
        """
        self.effects.append(effect)
        self.effects.sort(key=lambda e: e.priority)

    def _apply_effects(self, effect_type):
        """Apply all effects of given type to the racer.

        Apply all effects in PRRacer.effects of type effect_type to the
        racer object. If the effect duration is down to 0 delete the effect
        from the effect list.

        It is needed to distinguish the effects to apply be their type,
        because, speed and target area effects need to be applied at different
        times

        Args:
            effect_type (PREffectType): type of the effects that should be
               applied
        """
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
        """Move to position and do everything what is caused by the movement

        Set the new position of the racer. If the new position causes a crash
        (this is figured out by PRRacer._calc_possible_next_positions()) add a
        PRCrashEffect to PRRacer.effects.
        If the new position is also the position of another racer apply
        collision effects.

        Furthermore evaluate the new position, apply active effects and set the
        new speed.

        Note:
            This method should only be called from the
            PaperRacerGameState.goto() method!

        Args:
            position (Coord): The position where the racer should move to. This
               must be a valid position from PRRacer.possible_next_positions
               or PRRacer.crash_position.

        Returns:
            True if the racer could move to the specified position, False
            otherwise
        """
        position = Coord(position)
        new_position = None
        if self.crash_position is not None:
            new_position = self.crash_position
            self.crash_position = None
            self.add_effect(PRCrashEffect(self))
            self.speed = Coord((0, 0))
        elif position in self.possible_next_positions:
            other_racer = self.gamestate.racer_on_position(position)
            if other_racer is not None and other_racer != self:
                # Collision between two racer:
                # set new position to the last position before the position
                # of the other racer
                line = self.grid.line(other_racer.position, self.position)
                new_position = line[1]

                # apply a collision effect to the other racer
                effect = PRCollisionEffect(other_racer, other=True)
                effect.apply()
                # recalculate the other racer's next positions, since they
                # are affected by the collision effect
                other_racer.calc_possible_next_positions()
                # add the collision effect to own effects list
                self.add_effect(PRCollisionEffect(self, other=False))
            else:
                new_position = position
            self.speed = new_position - self.position

        # given position is not reachable
        if new_position is None:
            return False

        self.position = new_position
        self.path.append(new_position)

        # check position for effects caused by it
        self._evaluate_position()

        # apply effects on the speed of the racer
        self._apply_effects(PREffectType.SpeedEffect)

        # calc the possible next positions
        self._calc_possible_next_positions()

        # apply effects on the possible next positions
        self._apply_effects(PREffectType.TargetAreaEffect)

        return True


class PREffectConfig:
    """This class is used to create new PREffect objects.

    The class is used to create new PREffect objects according to the
    definitions in the map file.
    For each effect section in the map file one PREffectConfig object
    is created, to create the specified effect when needed.

    Attributes:
        name (str): The name of the effect
        type (str): Type of the effect (one of "SAND", "MULTISPEED",
           "MAXSPEED", "BIGGERTARGETAREA")
        config (configparser.SectionProxy): the section of the map file
           defining the effect
    """

    def __init__(self, name, config):
        """Initialize object.

        Args:
            name (str): Name of the effect (from the section name in the
               map file). It's not used but should be the correct name for
               future versions of this class
            config (configparser.SectionProxy): The section of the map file
               defining the effect
        """
        self.name = name
        self.type = config["type"]
        self.config = config

    def createNewEffectObj(self, racer):
        """Create and return a PREffect object with the specified properties.

        Args:
            racer (PRRacer): The racer for which the effect is created

        Returns:
            The created PREffect object
        """
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
    """Class to load the mapfile and act as global configuration proxy.

    Attributes:
        map_filename (str): path to the map file (the bitmap file)
        map_name (str): Name of the map
        ui_background_image (str): path to a image that is used as background
        ui_background_color (tuple): RGB color to fill the background
        blockcolor (tuple): RGB color which represents points of type
           PaperRacerPointType.BLOCK in the bitmap map file
        streetcolor (tuple): RGB color of the street in the bitmap map file
        startcolor (tuple): RGB color of the start area
        destcolor (tuple): RGB color of the destination area (finish)
        effects (dict[tuple, PREffectConfig]): dictionary that maps the color
           of the points in the bitmap map file corresponding to an effect
           to its PREffectConfig object
    """

    def __init__(self):
        pass

    def str_to_color(self, s):
        """Helper function to convert a string to a RGB color value.

        Args:
            s (str): a string in the format "r,g,b", e.g. "255,0,0"
               (without the quotation marks)

        Returns:
            RGB color as tuple of ints, e.g (255, 0, 0)
        """
        if s is None:
            raise NameError("invalid color")
        return tuple(map(int, s.split(",")))

    def load_map(self, filename):
        """Load the configuration from the map file.

        Load the map file specified by filename, set all the class attributes
        and create the PREffectConfig objects for every effect specified in the
        map file

        Args:
            filename (str): path to the map file (the INI file)
        """
        cp = configparser.ConfigParser()

        # this is just a workaround to avoid a bug in the parsing of the
        # mapfile
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
        self.ui_background_color = self.str_to_color(
            cp["General"].get("ui_bgcolor", "255,255,255")
        )
        self.blockcolor = self.str_to_color(
            cp["General"].get("blockcolor", "0,0,0")
        )
        self.streetcolor = self.str_to_color(
            cp["General"].get("streetcolor", "255,255,255")
        )
        self.startcolor = self.str_to_color(
            cp["General"].get("startcolor", "0,255,0")
        )
        self.destcolor = self.str_to_color(
            cp["General"].get("destcolor", "0,255,0")
        )

        self.effects = dict()
        for sec in cp.sections():
            if sec == "global" or sec == "General":
                continue
            if sec.startswith("effect:"):
                name = sec[7:]
                if "mapcolor" not in cp[sec]:
                    raise NameError("mapcolor not specified in effect section")
                color = self.str_to_color(cp[sec].get("mapcolor"))
                self.effects[color] = PREffectConfig(name, cp[sec])


class PaperRaceGameState:
    """Main class of the game.

    This class holds the state of the game. The complete interaction between
    the gui or agents and the game should happen via the methods of this class.

    Attributes:
        config (PRConfig): Configuration loaded from the map file (INI file)
        grid (PaperRacerGrid): The 'board' or map on which the game is played
        scoreboard (dict[int, int]): dictionary with all ids of racers that
           reached the target area, with the number of steps they needed
        finished (bool): False while the game is running, True if it's finished
        racer (dict[int, PRRacer]): holds all racer objects indexed with their
           ids
        current_racer_id (int): the id of the racer that will be moved by
           calling PaperRacerGameState.goto() the next time
    """
    def __init__(self):
        """Initialize object."""
        self.config = PRConfig()
        self.grid = PaperRaceGrid(self.config)
        self.scoreboard = {}

    def load_map(self, filename):
        """Load the map specified by filename

        Load the map file in the configuration object, load the grid from the
        bitmap according to the configuration, create racer

        Args:
            filename (str): path to the map file (the INI file)
        """
        self.config.load_map(filename)

        self.grid.load_from_bitmap(self.config.map_filename)

        self.racer = {}

        self.scoreboard.clear()
        self.finished = False
        self.racer[0] = PaperRacer(0, self.grid, self,
                                   random.choice(list(self.grid.startarea)))
        self.racer[1] = PaperRacer(1, self.grid, self,
                                   random.choice(list(self.grid.startarea)))

        self.current_racer_id = 0

    def current_racer(self):
        """Return the racer with the id PaperRacerGameState.current_racer_id"""
        return self.racer[self.current_racer_id]

    def goto(self, position):
        """Move the current racer to position.

        The command is delegated to the PRRacer object which moves.
        If a racer reaches the destination area (finish) it is added to the
        scoreboard and thereby deactivated.

        Call PaperRacerGameState.next_player() to switch to the next racer

        Args:
            position (Coord): The position to move to. This *must* be a valid
               position from current_racer().possible_next_positions or in the
               case this list is empty current_racer().crash_position

        Returns:
            True if the racer could move to the position, False otherwise (in
            this case it is very likely, that the specified position is not
            in the current_racer().possible_next_positions list)
        """
        if not self.current_racer().goto(position):
            print("Something went wrong")
            return False
        if self.current_racer().position in self.grid.destarea:
            self.scoreboard[self.current_racer_id] \
                = len(self.current_racer().path)
        self.next_player()
        return True

    def next_player(self):
        """Set current_racer_id to the id of the next active racer.

        If there are no active racers left (because all reached the destination
        area, mark the game as finished.
        """
        if len(self.scoreboard) >= len(self.racer):
            self.finished = True
            return
        self.current_racer_id += 1
        self.current_racer_id %= len(self.racer)
        if self.current_racer_id in self.scoreboard:
            self.next_player()

    def racer_on_position(self, position):
        """Check if there is a racer at position.

        Check if there is a racer at the given position and if so return the
        PRRacer object.

        Args:
            position (Coord): The position to check

        Returns:
            The PRRacer object if there is a racer at the position, None
            otherwise
        """
        for racer in self.racer.values():
            if racer.position == position:
                return racer
        return None
