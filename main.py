"""Pixel Knight - a small platformer built with Pygame Zero.

Run with:  pgzrun main.py

Only Pygame Zero, math and random are used, plus the Rect class imported
directly from Pygame as explicitly permitted by the project rules.
"""
import math
import random

from pygame import Rect

WIDTH = 800
HEIGHT = 600
TITLE = "Pixel Knight"

GRAVITY = 1000.0
MOVE_SPEED = 190.0
JUMP_SPEED = -480.0
TERMINAL_VELOCITY = 650.0
PLAYER_MAX_HEARTS = 3

GROUND_TOP = 560
PLATFORM_WIDTH = 110
PLATFORM_MIN_RISE = 60
PLATFORM_MAX_RISE = 100  # stays well under the ~115px max jump height


def random_platform(anchor_min, anchor_max):
    """A floating platform placed at a random spot and height, always kept
    fully over solid ground and within the player's single-jump reach."""
    left = random.randint(anchor_min, anchor_max)
    rise = random.randint(PLATFORM_MIN_RISE, PLATFORM_MAX_RISE)
    return Rect((left, GROUND_TOP - rise), (PLATFORM_WIDTH, 20))


def coin_spot(platform):
    return (platform.centerx, platform.top - 20)


class Animation:
    """A named sequence of image frames played back at a fixed rate."""

    def __init__(self, frames, frame_duration):
        self.frames = frames
        self.frame_duration = frame_duration


class AnimatedActor:
    """Base class pairing a Pygame Zero Actor with a collision Rect and
    a small state machine of Animations, used for both the hero and the
    enemies so every moving character animates the same way."""

    def __init__(self, animations, start_animation, pos, size):
        self.animations = animations
        self.animation_name = start_animation
        self.frame_index = 0
        self.frame_timer = 0.0
        self.rect = Rect((0, 0), size)
        self.rect.center = pos
        self.actor = Actor(animations[start_animation].frames[0], pos=pos)

    def set_animation(self, name):
        if name != self.animation_name:
            self.animation_name = name
            self.frame_index = 0
            self.frame_timer = 0.0

    def update_animation(self, dt):
        animation = self.animations[self.animation_name]
        self.frame_timer += dt
        if self.frame_timer >= animation.frame_duration:
            self.frame_timer -= animation.frame_duration
            self.frame_index = (self.frame_index + 1) % len(animation.frames)
        self.actor.image = animation.frames[self.frame_index]
        self.actor.center = self.rect.center

    def draw(self):
        self.actor.draw()


HERO_ANIMATIONS = {
    "idle": Animation(["hero_idle_0", "hero_idle_1"], 0.5),
    "walk": Animation(["hero_walk_0", "hero_walk_1", "hero_walk_2", "hero_walk_3"], 0.12),
    "jump": Animation(["hero_jump"], 1.0),
}
SLIME_ANIMATIONS = {
    "idle": Animation(["slime_idle_0", "slime_idle_1"], 0.4),
    "walk": Animation(["slime_walk_0", "slime_walk_1", "slime_walk_2", "slime_walk_3"], 0.15),
}
BAT_ANIMATIONS = {
    "idle": Animation(["bat_idle_0", "bat_idle_1"], 0.3),
    "walk": Animation(["bat_fly_0", "bat_fly_1", "bat_fly_2", "bat_fly_3"], 0.08),
}
COIN_ANIMATIONS = {"spin": Animation(["coin_0", "coin_1", "coin_2", "coin_3"], 0.12)}
FLAG_ANIMATIONS = {"wave": Animation(["flag_0", "flag_1"], 0.5)}


class Player(AnimatedActor):
    """The hero. Handles keyboard movement, jumping, gravity, platform
    collisions and taking damage from enemies."""

    def __init__(self, pos):
        super().__init__(HERO_ANIMATIONS, "idle", pos, (20, 34))
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.on_ground = False
        self.hearts = PLAYER_MAX_HEARTS
        self.invulnerable_timer = 0.0
        self.coins_collected = 0
        self.reached_flag = False

    def physics_update(self, dt, ground_platforms, floating_platforms):
        moving = False
        if keyboard.left or keyboard.a:
            self.velocity_x = -MOVE_SPEED
            moving = True
        elif keyboard.right or keyboard.d:
            self.velocity_x = MOVE_SPEED
            moving = True
        else:
            self.velocity_x = 0.0

        if (keyboard.space or keyboard.up or keyboard.w) and self.on_ground:
            self.velocity_y = JUMP_SPEED
            self.on_ground = False
            play_sound("jump")

        self.velocity_y = min(self.velocity_y + GRAVITY * dt, TERMINAL_VELOCITY)

        self.rect.x += self.velocity_x * dt
        self._resolve_solid(ground_platforms, "x")
        previous_bottom = self.rect.bottom
        self.rect.y += self.velocity_y * dt
        self.on_ground = False
        self._resolve_solid(ground_platforms, "y")
        self._resolve_one_way(floating_platforms, previous_bottom)

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt

        if not self.on_ground:
            self.set_animation("jump")
        elif moving:
            self.set_animation("walk")
        else:
            self.set_animation("idle")
        self.update_animation(dt)

    def _resolve_solid(self, platforms, axis):
        for platform in platforms:
            if not self.rect.colliderect(platform):
                continue
            if axis == "x":
                if self.velocity_x > 0:
                    self.rect.right = platform.left
                elif self.velocity_x < 0:
                    self.rect.left = platform.right
            else:
                if self.velocity_y > 0:
                    self.rect.bottom = platform.top
                    self.velocity_y = 0.0
                    self.on_ground = True
                elif self.velocity_y < 0:
                    self.rect.top = platform.bottom
                    self.velocity_y = 0.0

    def _resolve_one_way(self, platforms, previous_bottom):
        """Floating platforms can be jumped up through from underneath, but
        catch the player when they land on top of them from above."""
        if self.velocity_y <= 0:
            return
        for platform in platforms:
            if previous_bottom <= platform.top + 1 and self.rect.colliderect(platform):
                self.rect.bottom = platform.top
                self.velocity_y = 0.0
                self.on_ground = True

    def take_damage(self, knock_left):
        self.hearts -= 1
        self.invulnerable_timer = 1.2
        self.velocity_x = -220.0 if knock_left else 220.0
        self.velocity_y = -260.0

    def is_flickering(self):
        return self.invulnerable_timer > 0 and int(self.invulnerable_timer * 10) % 2 == 0


class Enemy(AnimatedActor):
    """Common patrol behaviour shared by every enemy: move back and forth
    inside a fixed range, occasionally pausing to idle, and being
    temporarily removed and respawned after being stomped on."""

    def __init__(self, animations, pos, size, patrol_min, patrol_max, speed):
        super().__init__(animations, "idle", pos, size)
        self.start_pos = pos
        self.patrol_min = patrol_min
        self.patrol_max = patrol_max
        self.speed = speed
        self.direction = 1
        self.active = True
        self.respawn_timer = 0.0
        self.moving = True
        self.state_timer = random.uniform(2.0, 3.0)

    def stomp(self):
        self.active = False
        self.respawn_timer = 3.0

    def patrol(self, dt):
        self.state_timer -= dt
        if self.state_timer <= 0:
            self.moving = not self.moving
            self.state_timer = random.uniform(2.0, 3.0) if self.moving else random.uniform(1.0, 1.8)
        if self.moving:
            self.rect.x += self.direction * self.speed * dt
            if self.rect.left <= self.patrol_min:
                self.rect.left = self.patrol_min
                self.direction = 1
            elif self.rect.right >= self.patrol_max:
                self.rect.right = self.patrol_max
                self.direction = -1
        self.set_animation("walk" if self.moving else "idle")

    def update(self, dt):
        if not self.active:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.active = True
                self.rect.center = self.start_pos
                self.direction = 1
                self.moving = True
            return
        self.patrol(dt)
        self.update_animation(dt)

    def draw(self):
        if self.active:
            super().draw()


class Slime(Enemy):
    def __init__(self, pos, patrol_min, patrol_max, speed):
        super().__init__(SLIME_ANIMATIONS, pos, (26, 20), patrol_min, patrol_max, speed)


class Bat(Enemy):
    def __init__(self, pos, patrol_min, patrol_max, speed):
        super().__init__(BAT_ANIMATIONS, pos, (28, 18), patrol_min, patrol_max, speed)
        self.base_y = pos[1]
        self.time_alive = 0.0

    def patrol(self, dt):
        self.time_alive += dt
        super().patrol(dt)
        self.rect.centery = self.base_y + math.sin(self.time_alive * 3.0) * 10


class Coin(AnimatedActor):
    def __init__(self, pos):
        super().__init__(COIN_ANIMATIONS, "spin", pos, (16, 16))
        self.collected = False


class Flag(AnimatedActor):
    def __init__(self, pos):
        super().__init__(FLAG_ANIMATIONS, "wave", pos, (16, 46))


class World:
    """Holds the current level: platforms, the player, enemies, coins and
    the goal flag, and runs their updates and collisions each frame."""

    def __init__(self):
        platform_left = random_platform(20, 150)
        platform_mid = random_platform(190, 230)
        platform_right = random_platform(460, 590)
        self.ground_platforms = [
            Rect((0, 560), (340, 40)),
            Rect((460, 560), (340, 40)),
        ]
        self.floating_platforms = [platform_left, platform_mid, platform_right]
        self.platforms = self.ground_platforms + self.floating_platforms
        self.player = Player((60, 520))
        self.enemies = [
            Slime((560, 542), 480, 700, 55),
            Bat((650, 260), 560, 760, 90),
        ]
        self.coins = [
            Coin(coin_spot(platform_left)),
            Coin(coin_spot(platform_mid)),
            Coin(coin_spot(platform_right)),
        ]
        self.flag = Flag((770, 502))
        self.hint_timer = 0.0

    def update(self, dt):
        self.player.physics_update(dt, self.ground_platforms, self.floating_platforms)
        for enemy in self.enemies:
            enemy.update(dt)
        for coin in self.coins:
            if not coin.collected:
                coin.update_animation(dt)
        self.flag.update_animation(dt)
        self.hint_timer = max(0.0, self.hint_timer - dt)
        self._handle_collisions()

        if self.player.rect.top > HEIGHT + 60:
            return "LOSE", "You fell into the pit!"
        if self.player.hearts <= 0:
            return "LOSE", "The knight was defeated!"
        if self.player.reached_flag:
            return "WIN", "You reached the flag with every coin!"
        return "PLAYING", ""

    def _handle_collisions(self):
        player = self.player
        for enemy in self.enemies:
            if not enemy.active or not player.rect.colliderect(enemy.rect):
                continue
            if player.velocity_y > 0 and player.rect.bottom - enemy.rect.top <= 16:
                enemy.stomp()
                player.velocity_y = JUMP_SPEED * 0.55
                play_sound("stomp")
            elif player.invulnerable_timer <= 0:
                player.take_damage(knock_left=player.rect.centerx < enemy.rect.centerx)
                play_sound("hit")

        for coin in self.coins:
            if not coin.collected and player.rect.colliderect(coin.rect):
                coin.collected = True
                player.coins_collected += 1
                play_sound("coin")

        if player.rect.colliderect(self.flag.rect):
            if player.coins_collected >= len(self.coins):
                player.reached_flag = True
            else:
                self.hint_timer = 1.5

    def draw(self):
        screen.blit("background", (0, 0))
        for platform in self.platforms:
            tile_count = max(1, platform.width // 40)
            for i in range(tile_count):
                screen.blit("platform_tile", (platform.left + i * 40, platform.top))
        for coin in self.coins:
            if not coin.collected:
                coin.draw()
        self.flag.draw()
        for enemy in self.enemies:
            enemy.draw()
        if not self.player.is_flickering():
            self.player.draw()
        self._draw_hud()
        if self.hint_timer > 0:
            screen.draw.text(
                "Collect every coin before reaching the flag!",
                center=(WIDTH / 2, 90), fontsize=30, color="gold", owidth=1, ocolor="black",
            )

    def _draw_hud(self):
        for i in range(PLAYER_MAX_HEARTS):
            name = "heart_full" if i < self.player.hearts else "heart_empty"
            screen.blit(name, (16 + i * 26, 14))
        screen.draw.text(
            f"Coins: {self.player.coins_collected}/{len(self.coins)}",
            topright=(WIDTH - 16, 16), fontsize=28, color="white", owidth=1, ocolor="black",
        )
        screen.draw.text(
            "ESC: quit to menu",
            bottomleft=(16, HEIGHT - 12), fontsize=20, color=(210, 210, 220), owidth=1, ocolor="black",
        )


class Button:
    def __init__(self, text, rect, callback):
        self.text = text
        self.rect = rect
        self.callback = callback

    def contains(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self):
        screen.draw.filled_rect(self.rect, (36, 40, 64))
        screen.draw.rect(self.rect, (230, 230, 240))
        screen.draw.text(self.text, center=self.rect.center, fontsize=30, color="white")


def play_sound(name):
    if sound_on:
        getattr(sounds, name).play()


def sound_button_label():
    return f"Sound: {'On' if sound_on else 'Off'}"


def start_game():
    global world, game_state
    world = World()
    game_state = "PLAYING"
    if sound_on:
        music.play("theme.wav")


def toggle_sound():
    global sound_on
    sound_on = not sound_on
    sound_button.text = sound_button_label()
    if sound_on:
        music.unpause()
    else:
        music.pause()


def exit_game():
    raise SystemExit


game_state = "MENU"
sound_on = True
world = None
end_message = ""

buttons = [
    Button("Start Game", Rect((300, 220), (200, 50)), start_game),
    Button(sound_button_label(), Rect((300, 290), (200, 50)), toggle_sound),
    Button("Exit", Rect((300, 360), (200, 50)), exit_game),
]
sound_button = buttons[1]


def draw_menu():
    screen.fill((16, 20, 38))
    screen.draw.text("Pixel Knight", center=(WIDTH / 2, 120), fontsize=64, color="white", owidth=1.2, ocolor="black")
    screen.draw.text(
        "Arrows/WASD to move, Space to jump, jump on slimes to defeat them",
        center=(WIDTH / 2, 175), fontsize=20, color=(200, 200, 220),
    )
    for button in buttons:
        button.draw()


def draw_end_screen(title, subtitle):
    screen.fill((12, 12, 22))
    screen.draw.text(title, center=(WIDTH / 2, HEIGHT / 2 - 40), fontsize=58, color="white")
    screen.draw.text(subtitle, center=(WIDTH / 2, HEIGHT / 2 + 20), fontsize=26, color=(210, 210, 230))
    screen.draw.text(
        "Press ENTER to return to the menu", center=(WIDTH / 2, HEIGHT / 2 + 70),
        fontsize=22, color=(180, 180, 200),
    )


def draw():
    if game_state == "MENU":
        draw_menu()
    elif game_state == "PLAYING":
        world.draw()
    elif game_state == "WIN":
        draw_end_screen("You Win!", end_message)
    elif game_state == "LOSE":
        draw_end_screen("Game Over", end_message)


def update(dt):
    global game_state, end_message
    if game_state == "PLAYING":
        status, message = world.update(dt)
        if status != "PLAYING":
            game_state = status
            end_message = message
            play_sound("win" if status == "WIN" else "lose")
            music.fadeout(0.6)


def on_mouse_down(pos):
    if game_state == "MENU":
        for button in buttons:
            if button.contains(pos):
                button.callback()


def on_key_down(key):
    global game_state
    if game_state == "PLAYING" and key == keys.ESCAPE:
        game_state = "MENU"
        music.fadeout(0.4)
    elif game_state in ("WIN", "LOSE") and key in (keys.RETURN, keys.SPACE):
        game_state = "MENU"
