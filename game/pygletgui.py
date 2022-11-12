import pyglet
# from pyglet.gl import *
from collections import OrderedDict
from time import time
from game.gamestate import PaperRaceGameState, PaperRacePointType, Coord
import itertools
import math
import time

key = pyglet.window.key


class GridPoint:
    def __init__(self, pos: pyglet.math.Vec2, grid_width, grid_height, size=15, width=2,
                 color=(255, 255, 255),
                 batch=None, group=None):
        offset_x = (grid_width-size) // 2
        offset_y = (grid_height-size) // 2
        self.line1 = pyglet.shapes.Line(offset_x+pos.x+size//2, offset_y+pos.y,
                                        offset_x+pos.x+size//2, offset_y+pos.y+size,
                                        width, color, batch, group)
        self.line2 = pyglet.shapes.Line(offset_x+pos.x, offset_y+pos.y+size//2,
                                        offset_x+pos.x+size, offset_y+pos.y+size//2,
                                        width, color, batch, group)


class Layer:
    def __init__(self, gamestate: PaperRaceGameState, width, height):
        self.gamestate = gamestate
        self.grid = self.gamestate.grid
        self.width = width
        self.height = height

        self.grid_width = self.width//self.grid.width
        self.grid_height = self.height//self.grid.height

        self.batch = pyglet.graphics.Batch()

    def pos_game2ui(self, p: Coord):
        return pyglet.math.Vec2(
            (p[0]+0.5)*self.grid_width,
            (self.gamestate.grid.height - p[1] - 0.5)*self.grid_height
        )


class GridLayer(Layer):
    def __init__(self, gamestate: PaperRaceGameState, width, height):
        super().__init__(gamestate, width, height)

        self.background_group = pyglet.graphics.OrderedGroup(0)
        self.points_group = pyglet.graphics.OrderedGroup(1)

        if self.gamestate.config.ui_background_image != "None":
            self.background_img = pyglet.image.load(
                # self.gamestate.config.map_filename)
                self.gamestate.config.ui_background_image)
            self.background_sprite = pyglet.sprite.Sprite(
                self.background_img,
                batch=self.batch,
                group=self.background_group)
            self.background_sprite.update(
                scale_x=self.width/self.background_img.width,
                scale_y=self.height/self.background_img.height
            )

        self.points = {}

        for coord, t in self.grid.items():
            p = self.pos_game2ui(coord)
            if t == PaperRacePointType.STREET:
                self.points[p] = GridPoint(
                    p,
                    self.grid_width,
                    self.grid_height,
                    color=(0, 255, 0),
                    batch=self.batch,
                    group=self.points_group
                )
            elif t == PaperRacePointType.EFFECT:
                self.points[p] = GridPoint(
                    p,
                    self.grid_width,
                    self.grid_height,
                    color=(255, 255, 0),
                    batch=self.batch,
                    group=self.points_group
                )
            else:
                continue
                self.points[p] = GridPoint(
                    p,
                    self.grid_width,
                    self.grid_height,
                    color=(0, 0, 0),
                    batch=self.batch,
                    group=self.points_group
                )


class Racer:
    def __init__(self, pos: pyglet.math.Vec2, grid_width, grid_height,
                 image="res/car.png",
                 batch=None, group=None):
        size = grid_width
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.batch = batch
        self.group = group
        self.pos = pos
        self.offset_x = (grid_width) // 2
        self.offset_y = (grid_height) // 2
        self.set_image(image)
        #self.sprite.anchor_x = self.sprite.width // 2
        #self.sprite.anchor_y = self.sprite.height // 2

        
        self.update_pos(pos)
        
        #self.rect = pyglet.shapes.Rectangle(pos.x, pos.y, grid_width, grid_height, color, batch, group)

    def set_image(self, image):
        self.img = pyglet.image.load(image)
        self.img.anchor_x = self.img.width // 2
        self.img.anchor_y = self.img.height // 2
        self.sprite = pyglet.sprite.Sprite(self.img, self.pos.x+self.offset_x, self.pos.y+self.offset_y, batch=self.batch, group=self.group)
        self.sprite.scale = self.grid_width/self.img.width * 2.5
        
    def _set_pos(self, pos):
        self.sprite.x = pos.x + self.offset_x
        self.sprite.y = pos.y + self.offset_y
            
    def update_pos(self, pos):
        if self.pos is None or self.pos == pos:
            self.sprite.x = pos.x + self.offset_x
            self.sprite.y = pos.y + self.offset_y
            self.pos = pos
            self._set_pos(pos)
            self.moving = False
            self.rotation = 0
        else:
            self.new_pos = pos
            self.pos = pyglet.math.Vec2(self.sprite.x - self.offset_x, self.sprite.y - self.offset_y)
            self.direction = self.new_pos - self.pos
            self.unit_speed = self.direction.normalize()
            self.motion_start_time = time.time()
            self.rotation = 90 - math.atan2(self.unit_speed.y, self.unit_speed.x) * 180/math.pi
            self.sprite.rotation = self.rotation

            pyglet.clock.schedule_interval(self._move, 1/60.0)

    def _move(self, dt):
        self.moving = True
        _dt = time.time() - self.motion_start_time
        if _dt < 1:
            pos = self.pos + pyglet.math.Vec2(_dt*self.direction[0], _dt*self.direction[1])
            self._set_pos(round(pos))
        else:
            self.pos = self.new_pos
            self._set_pos(self.pos)
            pyglet.clock.unschedule(self._move)
            self.moving = False


class RacerLayer(Layer):
    images = ["res/viper.png", "res/taxi.png", "res/car.png", "res/audi.png"]
    def __init__(self, gamestate, width, height):
        super().__init__(gamestate, width, height)

        self.racer = {}
        for racer_id in self.gamestate.racer:
            game_pos = self.gamestate.racer[racer_id].position
            self.racer[racer_id] = Racer(self.pos_game2ui(game_pos), self.grid_width, self.grid_height, image=self.images[racer_id%4], batch=self.batch)

    def update_racer(self, racer_id):
        game_pos = self.gamestate.racer[racer_id].position
        self.racer[racer_id].update_pos(self.pos_game2ui(game_pos))

    def racer_is_agent(self, racer_id):
        #self.racer[racer_id].set_image("res/audi.png")
        pass


class CurrentRacerLayer(Layer):
    def __init__(self, gamestate, width, height):
        super().__init__(gamestate, width, height)

        self.target_area = {}

        self.update()

    def update(self):
        self.target_area.clear()
        possible_next_positions = self.gamestate.current_racer().possible_next_positions
        if not possible_next_positions:
            possible_next_positions = [self.gamestate.current_racer().crash_position]
        for game_pos in possible_next_positions:
            pos = self.pos_game2ui(game_pos)
            self.target_area[game_pos] = pyglet.shapes.Ellipse(
                pos.x+self.grid_width//2,
                pos.y+self.grid_height//2,
                self.grid_width//2,
                self.grid_height//2,
                color=(255, 0, 0),
                batch=self.batch)
        self.remove_highlight()

    def highlight_pos(self, game_pos):
        pos = self.pos_game2ui(game_pos)
        r_pos = self.pos_game2ui(self.gamestate.current_racer().position)
        self.line = pyglet.shapes.Line(
            r_pos.x+self.grid_width//2,
            r_pos.y+self.grid_height//2,
            pos.x+self.grid_width//2,
            pos.y+self.grid_height//2,
            width=2,
            color=(255, 0, 0),
            batch=self.batch)

    def remove_highlight(self):
        self.line = None


class AgentLayer(Layer):
    def __init__(self, gamestate, width, height, agent):
        super().__init__(gamestate, width, height)
        self.agent = agent

        self.points = {}

        max_val = self.agent.max_h

        for pos in self.agent.h:
            p = self.pos_game2ui(pos)
            h = self.agent.h[pos]
            c = round(h/max_val * 255)
            color = (c, c, c)
            self.points[pos] = pyglet.shapes.Rectangle(
                p.x,
                p.y,
                self.grid_width,
                self.grid_height,
                color=color,
                batch=self.batch
            )
            self.points[pos].opacity = 170


class Main(pyglet.window.Window):
    def __init__(self, gamestate: PaperRaceGameState, width=2200, height=1200,
                 caption="PaperRace",
                 fps=True,
                 *args, **kwargs):
        self.gamestate = gamestate
        height = int(width * self.gamestate.grid.height/self.gamestate.grid.width)

        super().__init__(width, height, *args, **kwargs)

        # platform = pyglet.window.get_platform()
        display = pyglet.canvas.get_display()
        screen = display.get_default_screen()

        self.xDisplay = int(screen.width / 2 - self.width / 2)
        self.yDisplay = int(screen.height / 2 - self.height / 2)
        self.set_location(self.xDisplay, self.yDisplay)

        self.sprites = OrderedDict()

        self.batch = pyglet.graphics.Batch()

        if fps:
            self.sprites['fps_label'] = pyglet.text.Label('0 fps', x=10, y=10, batch=self.batch)
            self.last_update = time.time()
            self.fps_count = 0

        self.grid_layer = GridLayer(self.gamestate, self.width, self.height)
        self.racer_layer = RacerLayer(self.gamestate, self.width, self.height)
        self.current_racer_layer = CurrentRacerLayer(self.gamestate, self.width, self.height)

        self.keys = OrderedDict()

        self.mouse_x = 0
        self.mouse_y = 0

        self.alive = 1

        self.agents = {}

    def add_agent(self, agent, racer_id):
        self.agents[racer_id] = agent
        # DEBUG LAYER
        self.agent_layer = AgentLayer(self.gamestate, self.width, self.height, agent)
        self.racer_layer.racer_is_agent(racer_id)

    def pos_ui2game(self, x, y):
        gx = (x-0.5*self.grid_layer.grid_width) // self.grid_layer.grid_width
        gy = self.gamestate.grid.height - (y-0.5*self.grid_layer.grid_height) // self.grid_layer.grid_height - 1
        return Coord((int(gx), int(gy)))

    def on_draw(self):
        self.render()

    def on_close(self):
        self.alive = 0

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x
        self.mouse_y = y

        self.mouse_game_pos = self.pos_ui2game(x, y)

        # print(self.mouse_game_pos, self.current_racer_layer.target_area)
        if self.gamestate.current_racer_id in self.agents:
            return
        
        if self.mouse_game_pos in self.gamestate.current_racer().possible_next_positions \
                or self.mouse_game_pos == self.gamestate.current_racer().crash_position:
            self.current_racer_layer.highlight_pos(self.mouse_game_pos)
        elif self.current_racer_layer.line != None:
            self.current_racer_layer.remove_highlight()

    def on_mouse_release(self, x, y, button, modifiers):
        print('Released mouse at {}x{}'.format(x, y))
        if self.gamestate.current_racer_id in self.agents:
            return
        if self.mouse_game_pos in self.gamestate.current_racer().possible_next_positions \
                or self.mouse_game_pos == self.gamestate.current_racer().crash_position:
            racer_id = self.gamestate.current_racer_id
            self.gamestate.goto(self.mouse_game_pos)
            self.racer_layer.update_racer(racer_id)
            self.current_racer_layer.update()

            if self.gamestate.finished:
                self.alive = False

    def on_mouse_press(self, x, y, button, modifiers):
        if button == 1:
            print('Pressed mouse at {}x{}'.format(x, y))
            print("Coord:", self.pos_ui2game(x, y))

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.drag = True
        print('Dragging mouse at {}x{}'.format(x, y))
        print("Coord:", self.pos_ui2game(x, y))

    def on_key_release(self, symbol, modifiers):
        try:
            del self.keys[symbol]
        except:
            pass

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:  # [ESC]
            self.alive = 0

        self.keys[symbol] = True

    def pre_render(self):
        pass

    def render(self):
        self.clear()

        # FPS stuff (if you want to)
        self.fps_count += 1
        if time.time() - self.last_update > 1: # 1 sec passed
            self.sprites['fps_label'].text = str(self.fps_count)
            self.fps_count = 0
            self.last_update = time.time()

        # self.bg.draw()
        self.pre_render()

        #for sprite in self.sprites:
        #    self.sprites[sprite].draw()

        
        self.grid_layer.batch.draw()
        self.agent_layer.batch.draw()
        self.current_racer_layer.batch.draw()
        self.racer_layer.batch.draw()
        self.batch.draw()

        self.flip()

    def run(self):
        while self.alive == 1:
            racer_id = self.gamestate.current_racer_id
            if racer_id in self.agents and not self.racer_layer.racer[racer_id].moving:
                pos = self.agents[self.gamestate.current_racer_id].next_position()

                if not self.gamestate.goto(pos):
                    raise NameError("Invalid move by agent")
                self.racer_layer.update_racer(racer_id)
                self.current_racer_layer.update()

                if self.gamestate.finished:
                    self.alive = False

            self.render()

            # -----------> This is key <----------
            # This is what replaces pyglet.app.run()
            # but is required for the GUI to not freeze
            pyglet.clock.tick()
            event = self.dispatch_events()
