import os
import pygame
import random
from gamestate import PaperRaceGameState, PaperRacePointType, Coord

os.environ['SDL_VIDEO_CENTERED'] = '1'


class UIElement(pygame.sprite.Sprite):
    def __init__(self, position, size, bg_color=None):
        super().__init__()
        self.position = position
        self.size = size
        self.surf = pygame.Surface(size)
        # transparent background
        if bg_color is None:
            self.surf.fill((255, 0, 255))
            self.surf.set_colorkey((255, 0, 255))
            pass
        else:
            self.surf.fill(bg_color)
        self.update(position)

    def update(self, position):
        self.rect = self.surf.get_rect(center=(position[0], position[1]))


class UIDot(UIElement):
    def __init__(self, position, color, bg_color=None):
        super().__init__(position, (15, 15), bg_color)
        pygame.draw.line(self.surf, color, (0, 7), (15, 7), 3)
        pygame.draw.line(self.surf, color, (7, 0), (7, 15), 3)


class UILayer():
    def __init__(self, ui, gamestate):
        self.ui = ui
        self.gamestate = gamestate

    def render(self, surface):
        raise NotImplementedError()


class UIImgLayer(UILayer):
    def __init__(self, ui, gamestate, imgfile, x, y, w, h):
        super().__init__(ui, gamestate)
        self.rect = (x, y, w, h)
        self.texture = pygame.image.load(imgfile)
        self.texture = pygame.transform.scale(self.texture, (w, h))

    def render(self, surface):
        surface.blit(self.texture, self.rect)


class UIListLayer(UILayer):
    def render(self, surface):
        for sprite in self.sprites.values():
            surface.blit(sprite.surf, sprite.rect)


class UIDotLayer(UIListLayer):
    def __init__(self, ui, gamestate):
        super().__init__(ui, gamestate)

        # create dots
        self.sprites = dict()
        for pos, t in self.gamestate.grid.items():
            if t == PaperRacePointType.STREET:
                self.sprites[pos] = UIDot(
                    self.ui.coord_game2ui(pos),
                    (50, 50, 50)
                )
            elif t == PaperRacePointType.BLOCK:
                # don't paint a dot were you cant move to
                # self.sprites[pos] = UIDot(
                #   self.ui.coord_game2ui(pos),
                #   (0,0,0),
                #   (0,0,0)
                # )
                pass
            else:
                self.sprites[pos] = UIDot(
                    self.ui.coord_game2ui(pos),
                    (150, 0, 0)
                )


class UIRacer(UIElement):
    def __init__(self, position, racer, color):
        super().__init__(position, (40, 40), color)

        # the unsuccessful attempt to use a car bitmap
        if 0:
            self.racer = racer
            self.size = (40, 60)
            self.filename = "res/car.png"
            self.orientation = Coord((0, -1))
            self.texture = pygame.image.load(self.filename)
            self.texture_size = (10, 15)
            self.texture = pygame.transform.scale(self.texture, self.size)
            super().__init__(position, (40, 60))
            self.surf.blit(self.texture, (0, 0))
            # pygame.draw.rect(self.surf, (0, 0, 240), (0, 0, 30, 30))

    def angle_between(self, d1, d2):
        angle = {(0, 1): 180, (0, -1): 0, (1, 0): -90, (-1, 0): 90,
                 (1, -1): 45, (-1, -1): -45, (-1, 1): -135, (1, 1): 135}
        return angle[d2]-angle[d1]

    def update(self, position):
        super().update(position)
        # part of the attempt to use a bitmap
        if 0:
            print(self.racer)
            if self.racer.speed == (0, 0):
                return
            new_orientation = round(self.racer.speed / abs(self.racer.speed))
            angle = self.angle_between(new_orientation, self.orientation)
            self.texture = pygame.transform.rotate(self.texture, angle)
            self.surf.blit(self.texture, (0, 0))


class UIRacerLayer(UIListLayer):
    def __init__(self, ui, gamestate):
        super().__init__(ui, gamestate)

        self.sprites = dict()
        for id, racer in self.gamestate.racer.items():
            color = (random.randrange(0, 5)*50,
                     random.randrange(0, 5)*50,
                     random.randrange(0, 5)*50)
            self.sprites[id] = UIRacer(self.ui.coord_game2ui(racer.position),
                                       racer,
                                       color)

    def update(self):
        for id, racer in self.sprites.items():
            racer.update(self.ui.coord_game2ui(
                self.gamestate.racer[id].position
            ))


class UINextPositionMarker(UIElement):
    def __init__(self, position, color):
        super().__init__(position, (30, 30))
        pygame.draw.circle(self.surf, color, (15, 15), 15, width=3)


class UICurrentRacer(UIListLayer):
    def __init__(self, ui, gamestate):
        super().__init__(ui, gamestate)
        self.racer = None
        self.next_pos = Coord((0, 0))
        self.highlight_position = None
        self.sprites = dict()
        self.update()

    def update(self):
        # update
        self.racer = self.gamestate.current_racer()
        self.next_pos = self.racer.position + self.racer.speed
        self.possible_targets = self.racer.possible_next_positions
        color = (0, 0, 240)
        if not self.possible_targets:
            self.possible_targets = [self.racer.crash_position]
            color = (240, 0, 0)

        # update sprites
        self.sprites = {
            p: UINextPositionMarker(self.ui.coord_game2ui(p), color)
            for p in self.possible_targets
        }

    def render(self, surface):
        if self.racer is None:
            return

        if self.highlight_position:
            pygame.draw.line(
                surface,
                (200, 0, 0),
                self.ui.coord_game2ui(self.racer.position),
                self.ui.coord_game2ui(self.highlight_position),
                width=3
            )

        super().render(surface)

    def handle_mouse_hover(self):
        if self.ui.mouse_pos in self.sprites:
            self.highlight_position = self.ui.mouse_pos
        else:
            self.highlight_position = None


class UserInterface:
    def __init__(self):
        pygame.init()

        self.init_game()

    def init_game(self):
        self.gamestate = PaperRaceGameState()
        self.gamestate.load_map("maps/map4.ini")
        self.cell_size = 35
        self.padding = 20
        self.ui_bgcolor = self.gamestate.config.ui_background_color

        # set window size
        self.window = pygame.display.set_mode((
            self.gamestate.grid.width * self.cell_size + 2 * self.padding,
            self.gamestate.grid.height * self.cell_size + 2 * self.padding
        ))
        self.window.set_colorkey((255, 0, 255))

        if self.gamestate.config.ui_background_image != "None":
            self.background_layer = UIImgLayer(
                self,
                self.gamestate,
                self.gamestate.config.ui_background_image,
                self.padding,
                self.padding,
                self.gamestate.grid.width * self.cell_size,
                self.gamestate.grid.height * self.cell_size
            )
        self.dot_layer = UIDotLayer(self, self.gamestate)
        self.racer_layer = UIRacerLayer(self, self.gamestate)
        self.current_racer_layer = UICurrentRacer(self, self.gamestate)

        pygame.display.set_caption("Paperrace")
        # pygame.display.set_icon(pygame.image.load("icon.png"))
        self.clock = pygame.time.Clock()
        self.running = True
        self.new_pos = None

    def coord_game2ui(self, position):
        def g2u(x): x*self.cell_size + self.cell_size//2 + self.padding
        return Coord(map(g2u, position))

    def coord_ui2game(self, position):
        def u2g(x): (x - self.padding) // self.cell_size
        return Coord(map(u2g, position))

    def processInput(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                break
            elif event.type == pygame.MOUSEMOTION:
                # position of the mouse in pixel
                self.mouse_ui_pos = pygame.mouse.get_pos()
                # position of the mouse in game coordination
                self.mouse_pos = self.coord_ui2game(self.mouse_ui_pos)

                self.handle_mouse_hover()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    break
                elif event.key == pygame.K_RIGHT:
                    pass
                elif event.key == pygame.K_LEFT:
                    pass
                elif event.key == pygame.K_DOWN:
                    pass
                elif event.key == pygame.K_UP:
                    pass
            elif event.type == pygame.MOUSEBUTTONUP:
                # check if mouse clicked on possible target point
                self.handle_mouse_click()

    def handle_mouse_click(self):
        for pos, s in self.current_racer_layer.sprites.items():
            if s.rect.collidepoint(self.mouse_ui_pos):
                self.new_pos = (self.gamestate.current_racer_id, pos)

    def handle_mouse_hover(self):
        self.current_racer_layer.handle_mouse_hover()

    def update(self):
        # set new racer pos if racer position changed
        if self.new_pos is not None:
            # format of self.new_pos is (racer_id, position)
            # racer_id = self.new_pos[0]
            new_pos = self.new_pos[1]
            self.gamestate.goto(new_pos)
            self.new_pos = None
            self.running = not self.gamestate.finished

            self.racer_layer.update()
            self.current_racer_layer.update()

    def render(self):
        self.window.fill(self.ui_bgcolor)
        # TODO: this is dirty...
        if hasattr(self, "background_layer"):
            self.background_layer.render(self.window)
        self.dot_layer.render(self.window)
        self.racer_layer.render(self.window)
        self.current_racer_layer.render(self.window)
        pygame.display.update()

    def run(self):
        while self.running:
            self.processInput()
            self.update()
            self.render()
            self.clock.tick(300)
            pygame.time.wait(5)


ui = UserInterface()
ui.run()
print(ui.gamestate.scoreboard)
