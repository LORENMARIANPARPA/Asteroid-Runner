"""Game setup, state updates, collision handling, and rendering."""

import math
import random
from pathlib import Path

import pygame

from assets import (
    load_background,
    load_explosion_frames,
    load_sprite_sheet_frames,
    load_trimmed_image,
)
from entities import Asteroid, AsteroidExplosion, Player, Rocket
from settings import HEIGHT, WIDTH


class SpaceDodger:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Asteroid Run")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.high_score_path = Path.home() / ".asteroid_run_high_score"
        self.high_score = self.load_high_score()

        self.background = load_background("Starry background  - Layer 01 - Void.png")
        self.star_layer = load_background("Starry background  - Layer 02 - Stars.png")
        self.galaxy_layer = load_background("Starry background  - Layer 03 - Stars.png")
        self.ship_image = load_trimmed_image(
            "Main Ship - Base - Full health.png", (60, 52)
        )
        self.asteroid_image = load_trimmed_image("Asteroid 01 - Base.png", (58, 52))
        self.grey_asteroid_image = load_trimmed_image("Asteroid_02.png", (58, 52))
        self.shooting_asteroid_image = load_trimmed_image(
            "Asteroid_01_Shooting_Meteor.png", (87, 78)
        )
        self.explosion_frames = load_explosion_frames("Asteroid 01 - Explode.png")
        self.grey_explosion_frames = load_explosion_frames("Asteroid 02 - Explode.png")
        self.shield_frames = load_sprite_sheet_frames(
            "Main Ship - Shields - Round Shield.png", display_scale=1.5
        )
        self.rocket_frames = load_sprite_sheet_frames(
            "Main ship weapon - Projectile - Rocket.png", display_scale=3.0
        )
        self.rocket_masks = tuple(
            pygame.mask.from_surface(frame, threshold=0) for frame in self.rocket_frames
        )

        self.title_font = pygame.font.Font(None, 76)
        self.large_font = pygame.font.Font(None, 58)
        self.font = pygame.font.Font(None, 34)
        self.small_font = pygame.font.Font(None, 26)
        self.heart_font = pygame.font.SysFont("Segoe UI Emoji", 30)
        self.ability_font = pygame.font.SysFont("Segoe UI Emoji", 26)
        self.hud_panel = pygame.Surface((226, 228), pygame.SRCALPHA)
        pygame.draw.rect(
            self.hud_panel,
            (12, 10, 28, 175),
            self.hud_panel.get_rect(),
            border_radius=16,
        )
        pygame.draw.rect(
            self.hud_panel,
            (115, 93, 177, 190),
            self.hud_panel.get_rect(),
            width=2,
            border_radius=16,
        )
        self.hud_movement_hint = self.small_font.render(
            "MOVE  A / D  OR  ARROW KEYS", True, (190, 182, 214)
        )
        self.hud_ability_hint = self.small_font.render(
            "SHRINK  Z   SHIELD  X   FIRE  C", True, (190, 182, 214)
        )
        self.hud_icons = {
            "shrink": self.ability_font.render("\u2b50\ufe0f", True, (255, 211, 76)),
            "shield": self.ability_font.render("\U0001f7e2", True, (81, 226, 130)),
            "projectile": self.ability_font.render(
                "\U0001f7e6", True, (91, 166, 255)
            ),
        }
        self.heart_images = {
            lives: self.heart_font.render(
                "\u2764\ufe0f" * lives, True, (255, 91, 137)
            )
            for lives in range(4)
        }
        self.reset_game()
        self.state = "title"

    def reset_game(self):
        self.player = Player(self.ship_image)
        self.asteroids = []
        self.explosions = []
        self.rockets = []
        self.elapsed = 0.0
        self.spawn_timer = 0.0
        self.state = "playing"

    def start_game(self):
        self.reset_game()

    def load_high_score(self):
        try:
            score = int(self.high_score_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return 0
        if score < 0:
            raise ValueError(f"High score cannot be negative: {self.high_score_path}")
        return score

    def save_high_score(self):
        self.high_score_path.write_text(f"{self.high_score}\n", encoding="utf-8")

    def record_high_score(self):
        score = int(self.elapsed)
        if score > self.high_score:
            self.high_score = score
            self.save_high_score()

    @staticmethod
    def asteroids_overlap(first, second):
        if not first.rect.colliderect(second.rect):
            return False
        offset = (
            second.rect.x - first.rect.x,
            second.rect.y - first.rect.y,
        )
        return first.mask.overlap(second.mask, offset) is not None

    def spawn_asteroid(self, speed):
        diagonal = self.elapsed >= 100 and random.random() < 0.01
        shooting = random.random() < 0.05
        asteroid = Asteroid(
            self.asteroid_image,
            speed * 2 if shooting else speed,
            diagonal=diagonal,
            grey_image=self.grey_asteroid_image,
            shooting_image=self.shooting_asteroid_image,
            shooting=shooting,
        )
        max_x = max(0, WIDTH - asteroid.rect.width)

        if diagonal:
            # Diagonal asteroids enter from the top corner matching their direction.
            asteroid.rect.left = (
                -asteroid.rect.width if asteroid.velocity.x > 0 else WIDTH
            )
            asteroid.rect.top = -asteroid.rect.height
            while any(
                asteroid.rect.inflate(4, 4).colliderect(other.rect)
                for other in self.asteroids
            ):
                asteroid.rect.y -= asteroid.rect.height + 4
        else:
            asteroid.rect.top = -asteroid.rect.height
            candidates = [random.randint(0, max_x) for _ in range(64)]
            candidates.extend(range(max_x + 1))

            for x in candidates:
                asteroid.rect.left = x
                if not any(
                    asteroid.rect.inflate(4, 4).colliderect(other.rect)
                    for other in self.asteroids
                ):
                    asteroid.position = pygame.Vector2(asteroid.rect.center)
                    self.asteroids.append(asteroid)
                    return

            # If the whole top row is occupied, queue the asteroid above the field.
            asteroid.rect.left = random.randint(0, max_x)
            asteroid.rect.top = min(
                (other.rect.top for other in self.asteroids),
                default=0,
            ) - asteroid.rect.height - 4

        asteroid.position = pygame.Vector2(asteroid.rect.center)
        self.asteroids.append(asteroid)

    @staticmethod
    def turn_away_from_each_other(first, second, dx, dy):
        distance = math.hypot(dx, dy)
        if distance == 0:
            normal = pygame.Vector2(random.choice((-1, 1)), 0)
        else:
            normal = pygame.Vector2(dx / distance, dy / distance)

        for asteroid, away in ((first, -normal), (second, normal)):
            velocity = asteroid.velocity
            options = (
                pygame.Vector2(velocity.y, -velocity.x),
                pygame.Vector2(-velocity.y, velocity.x),
            )
            scores = [option.dot(away) for option in options]
            if scores[0] == scores[1]:
                asteroid.velocity = random.choice(options)
            else:
                asteroid.velocity = options[scores.index(max(scores))]
            asteroid.face_velocity()

        # Separate colliding sprites immediately so they don't stay stuck together.
        for _ in range(
            first.rect.width + second.rect.width + first.rect.height + second.rect.height
        ):
            if not SpaceDodger.asteroids_overlap(first, second):
                break
            first.position -= normal
            second.position += normal
            first.rect.center = (
                round(first.position.x),
                round(first.position.y),
            )
            second.rect.center = (
                round(second.position.x),
                round(second.position.y),
            )

    def resolve_asteroid_collisions(self):
        exploded = set()
        for first_index, first in enumerate(self.asteroids):
            for second_index in range(first_index + 1, len(self.asteroids)):
                second = self.asteroids[second_index]
                if first in exploded or second in exploded:
                    continue
                if self.asteroids_overlap(first, second):
                    dx = second.position.x - first.position.x
                    dy = second.position.y - first.position.y
                    self.turn_away_from_each_other(first, second, dx, dy)
                    for asteroid in (first, second):
                        if asteroid.is_shooting:
                            continue
                        asteroid.collisions += 1
                        if asteroid.collisions >= asteroid.collision_limit:
                            exploded.add(asteroid)
                            self.explosions.append(
                                AsteroidExplosion(
                                    (
                                        self.grey_explosion_frames
                                        if asteroid.is_grey
                                        else self.explosion_frames
                                    ),
                                    asteroid.rect.center,
                                    asteroid.scale,
                                )
                            )

        if exploded:
            self.asteroids = [
                asteroid for asteroid in self.asteroids if asteroid not in exploded
            ]

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_SPACE:
                    if self.state in ("title", "game_over"):
                        self.start_game()
                elif self.state == "playing" and event.key == pygame.K_z:
                    self.player.try_shrink()
                elif self.state == "playing" and event.key == pygame.K_x:
                    self.player.try_shield()
                elif self.state == "playing" and event.key == pygame.K_c:
                    if self.player.try_fire_projectile():
                        self.rockets.append(
                            Rocket(
                                self.rocket_frames,
                                self.rocket_masks,
                                (self.player.rect.centerx, self.player.rect.top),
                            )
                        )
        return True

    def update(self, delta_time):
        # Explosions continue to animate even after the player loses all lives.
        for explosion in self.explosions:
            explosion.update(delta_time)
        self.explosions = [
            explosion for explosion in self.explosions if not explosion.finished
        ]

        if self.state != "playing":
            return

        self.player.invulnerability_timer = max(
            0.0, self.player.invulnerability_timer - delta_time
        )
        self.player.update_abilities(delta_time)
        keys = pygame.key.get_pressed()
        self.player.move(keys, delta_time)
        self.elapsed += delta_time
        self.spawn_timer += delta_time

        spawn_interval = max(0.4, 0.95 - self.elapsed * 0.008)
        asteroid_speed = min(480, 220 + self.elapsed * 4)
        if self.spawn_timer >= spawn_interval:
            wave_size = min(4, 1 + int(self.elapsed // 20))
            for _ in range(wave_size):
                self.spawn_asteroid(asteroid_speed)
            self.spawn_timer = 0.0

        for asteroid in self.asteroids:
            asteroid.update(delta_time)
        self.resolve_asteroid_collisions()

        for rocket in self.rockets:
            rocket.update(delta_time)
        asteroids_by_depth = (
            sorted(
                self.asteroids,
                key=lambda item: item.rect.centery,
                reverse=True,
            )
            if self.rockets
            else ()
        )
        used_rockets = set()
        destroyed_asteroids = set()
        for rocket in self.rockets:
            # Check from bottom to top so the first asteroid along the rocket's path wins.
            for asteroid in asteroids_by_depth:
                if asteroid in destroyed_asteroids:
                    continue
                offset = (
                    asteroid.rect.x - rocket.rect.x,
                    asteroid.rect.y - rocket.rect.y,
                )
                if (
                    rocket.rect.colliderect(asteroid.rect)
                    and rocket.mask.overlap(asteroid.mask, offset)
                ):
                    used_rockets.add(rocket)
                    if not asteroid.is_shooting:
                        destroyed_asteroids.add(asteroid)
                        self.explosions.append(
                            AsteroidExplosion(
                                (
                                    self.grey_explosion_frames
                                    if asteroid.is_grey
                                    else self.explosion_frames
                                ),
                                asteroid.rect.center,
                                asteroid.scale,
                            )
                        )
                    break

        if destroyed_asteroids:
            self.asteroids = [
                asteroid
                for asteroid in self.asteroids
                if asteroid not in destroyed_asteroids
            ]
        self.rockets = [
            rocket
            for rocket in self.rockets
            if rocket not in used_rockets and not rocket.is_off_screen()
        ]

        for asteroid in self.asteroids:
            offset = (
                asteroid.rect.x - self.player.rect.x,
                asteroid.rect.y - self.player.rect.y,
            )
            if (
                self.player.invulnerability_timer <= 0
                and self.player.rect.colliderect(asteroid.rect)
                and self.player.mask.overlap(asteroid.mask, offset)
            ):
                if not self.player.absorb_hit_with_shield():
                    self.player.lives -= 1
                    self.player.invulnerability_timer = 1.5
                self.asteroids.remove(asteroid)
                if self.player.lives == 0:
                    self.record_high_score()
                    self.state = "game_over"
                break

        self.asteroids = [
            asteroid for asteroid in self.asteroids if not asteroid.is_off_screen()
        ]

    def draw_background(self):
        self.screen.blit(self.background, (0, 0))
        self.screen.blit(self.star_layer, (0, 0))
        self.screen.blit(self.galaxy_layer, (0, 0))

    def draw_centered_text(self, text, font, color, center, shadow=True):
        if shadow:
            shadow_image = font.render(text, True, (11, 8, 24))
            shadow_rect = shadow_image.get_rect(center=(center[0] + 2, center[1] + 3))
            self.screen.blit(shadow_image, shadow_rect)
        image = font.render(text, True, color)
        self.screen.blit(image, image.get_rect(center=center))

    def draw_panel(self, rect):
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 10, 28, 220), panel.get_rect(), border_radius=18)
        pygame.draw.rect(
            panel,
            (115, 93, 177, 190),
            panel.get_rect(),
            width=2,
            border_radius=18,
        )
        self.screen.blit(panel, rect)

    def draw_hud(self):
        seconds = int(self.elapsed)
        self.screen.blit(self.hud_panel, (18, 16))

        score_text = self.font.render(f"TIME  {seconds:03}", True, (245, 240, 255))
        self.screen.blit(score_text, (34, 24))

        self.screen.blit(self.heart_images[self.player.lives], (34, 58))

        self.draw_ability_bar(102, self.player.shrink_progress(), (255, 211, 76))
        if self.player.shrink_ready():
            star = self.hud_icons["shrink"]
            self.screen.blit(star, star.get_rect(midleft=(180, 108)))
        self.draw_ability_bar(137, self.player.shield_progress(), (81, 226, 130))
        if self.player.shield_ready():
            shield_icon = self.hud_icons["shield"]
            self.screen.blit(shield_icon, shield_icon.get_rect(midleft=(180, 143)))
        self.draw_ability_bar(172, self.player.projectile_progress(), (91, 166, 255))
        if self.player.projectile_ready():
            projectile_icon = self.hud_icons["projectile"]
            self.screen.blit(projectile_icon, projectile_icon.get_rect(midleft=(180, 178)))

        if self.player.ability_lockout > 0:
            remaining = math.ceil(self.player.ability_lockout)
            lockout_text = self.small_font.render(
                f"SKILLS LOCKED  {remaining}s",
                True,
                (205, 198, 222),
            )
            self.screen.blit(lockout_text, (34, 205))

        self.screen.blit(
            self.hud_movement_hint,
            self.hud_movement_hint.get_rect(topright=(WIDTH - 28, 30)),
        )
        self.screen.blit(
            self.hud_ability_hint,
            self.hud_ability_hint.get_rect(topright=(WIDTH - 28, 60)),
        )

    def draw_ability_bar(self, top, progress, color):
        track = pygame.Rect(34, top, 132, 12)
        pygame.draw.rect(self.screen, (44, 43, 61), track, border_radius=6)
        fill_width = round(track.width * max(0.0, min(1.0, progress)))
        if fill_width:
            fill = pygame.Rect(track.left, track.top, fill_width, track.height)
            pygame.draw.rect(self.screen, color, fill, border_radius=6)

    def draw(self):
        self.draw_background()

        for asteroid in self.asteroids:
            asteroid.draw(self.screen)
        for rocket in self.rockets:
            rocket.draw(self.screen)
        for explosion in self.explosions:
            explosion.draw(self.screen)
        self.player.draw(self.screen)
        if self.player.shield_active:
            frame_index = pygame.time.get_ticks() // 80 % len(self.shield_frames)
            shield = self.shield_frames[frame_index]
            self.screen.blit(
                shield,
                shield.get_rect(center=self.player.rect.center),
            )

        if self.state == "playing":
            self.draw_hud()
        elif self.state == "title":
            panel = pygame.Rect(150, 160, WIDTH - 300, 420)
            self.draw_panel(panel)
            self.draw_centered_text(
                "ASTEROID RUN", self.title_font, (247, 241, 255), (WIDTH // 2, 220)
            )
            self.draw_centered_text(
                "DODGE THE FIELD", self.font, (77, 231, 211), (WIDTH // 2, 285)
            )
            self.draw_centered_text(
                "Move: A / D or the arrow keys",
                self.small_font,
                (211, 205, 230),
                (WIDTH // 2, 375),
                shadow=False,
            )
            self.draw_centered_text(
                "Shrink: Z    Shield: X    Fire: C",
                self.small_font,
                (211, 205, 230),
                (WIDTH // 2, 410),
                shadow=False,
            )
            self.draw_centered_text(
                f"High score: {self.high_score} seconds",
                self.font,
                (255, 211, 76),
                (WIDTH // 2, 465),
            )
            self.draw_centered_text(
                "Press SPACE to launch",
                self.font,
                (255, 190, 103),
                (WIDTH // 2, 525),
            )
        else:
            panel = pygame.Rect(210, 205, WIDTH - 420, 310)
            self.draw_panel(panel)
            self.draw_centered_text(
                "SHIP DESTROYED",
                self.large_font,
                (255, 132, 151),
                (WIDTH // 2, 278),
            )
            self.draw_centered_text(
                f"Survived {int(self.elapsed)} seconds",
                self.font,
                (235, 230, 249),
                (WIDTH // 2, 353),
            )
            self.draw_centered_text(
                f"High score: {self.high_score} seconds",
                self.small_font,
                (255, 211, 76),
                (WIDTH // 2, 393),
            )
            self.draw_centered_text(
                "Press SPACE to try again",
                self.small_font,
                (255, 190, 103),
                (WIDTH // 2, 445),
            )

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            delta_time = min(self.clock.tick(60) / 1000, 0.05)
            running = self.handle_events()
            self.update(delta_time)
            self.draw()

        pygame.quit() 
