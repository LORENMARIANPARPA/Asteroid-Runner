"""Player, asteroid, and short-lived explosion animation entities."""

import math
import random

import pygame

from settings import HEIGHT, WIDTH

SHOOTING_METEOR_SOURCE_ANGLE = 135


class Player:
    SHRINK_DURATION = 5.0
    SHRINK_COOLDOWN = 25.0
    SHIELD_COOLDOWN = 40.0
    PROJECTILE_COOLDOWN = 30.0
    ABILITY_LOCKOUT = 15.0

    def __init__(self, image):
        self.base_image = image
        self.image = image
        self.mask = pygame.mask.from_surface(self.image, threshold=0)
        self.rect = self.image.get_rect(midbottom=(WIDTH // 2, HEIGHT // 4 * 3))
        self.speed = 470
        self.lives = 3
        self.invulnerability_timer = 0.0
        self.ability_lockout = 0.0
        self.shrink_active_timer = 0.0
        self.shrink_cooldown = 0.0
        self.shrink_recharge_pending = False
        self.shield_active = False
        self.shield_cooldown = 0.0
        self.shield_recharge_pending = False
        self.projectile_cooldown = 0.0
        self.projectile_recharge_pending = False

    def try_shrink(self):
        if (
            self.ability_lockout > 0
            or self.shrink_active_timer > 0
            or self.shrink_cooldown > 0
            or self.shrink_recharge_pending
        ):
            return False

        center = self.rect.center
        size = (
            max(1, round(self.base_image.get_width() * 0.5)),
            max(1, round(self.base_image.get_height() * 0.5)),
        )
        self.image = pygame.transform.smoothscale(self.base_image, size)
        self.mask = pygame.mask.from_surface(self.image, threshold=0)
        self.rect = self.image.get_rect(center=center)
        self.shrink_active_timer = self.SHRINK_DURATION
        self.ability_lockout = self.ABILITY_LOCKOUT
        return True

    def try_shield(self):
        if (
            self.ability_lockout > 0
            or self.shield_active
            or self.shield_cooldown > 0
            or self.shield_recharge_pending
        ):
            return False

        self.shield_active = True
        self.ability_lockout = self.ABILITY_LOCKOUT
        return True

    def absorb_hit_with_shield(self):
        if not self.shield_active:
            return False

        self.shield_active = False
        self.shield_recharge_pending = True
        if self.ability_lockout <= 0:
            self.shield_recharge_pending = False
            self.shield_cooldown = self.SHIELD_COOLDOWN
        return True

    def try_fire_projectile(self):
        if (
            self.ability_lockout > 0
            or self.projectile_cooldown > 0
            or self.projectile_recharge_pending
        ):
            return False

        self.projectile_recharge_pending = True
        self.ability_lockout = self.ABILITY_LOCKOUT
        return True

    def update_abilities(self, delta_time):
        was_locked_out = self.ability_lockout > 0
        self.ability_lockout = max(0.0, self.ability_lockout - delta_time)

        if self.shrink_active_timer > 0:
            self.shrink_active_timer = max(
                0.0, self.shrink_active_timer - delta_time
            )
            if self.shrink_active_timer == 0:
                center = self.rect.center
                self.image = self.base_image
                self.mask = pygame.mask.from_surface(self.image, threshold=0)
                self.rect = self.image.get_rect(center=center)
                self.shrink_recharge_pending = True

        if not was_locked_out:
            self.shrink_cooldown = max(0.0, self.shrink_cooldown - delta_time)
            self.shield_cooldown = max(0.0, self.shield_cooldown - delta_time)
            self.projectile_cooldown = max(
                0.0, self.projectile_cooldown - delta_time
            )

        if self.ability_lockout == 0:
            if self.shrink_recharge_pending:
                self.shrink_recharge_pending = False
                self.shrink_cooldown = self.SHRINK_COOLDOWN
            if self.shield_recharge_pending:
                self.shield_recharge_pending = False
                self.shield_cooldown = self.SHIELD_COOLDOWN
            if self.projectile_recharge_pending:
                self.projectile_recharge_pending = False
                self.projectile_cooldown = self.PROJECTILE_COOLDOWN

    def shrink_progress(self):
        if self.shrink_active_timer > 0:
            return self.shrink_active_timer / self.SHRINK_DURATION
        if self.shrink_recharge_pending:
            return 0.0
        return 1.0 - self.shrink_cooldown / self.SHRINK_COOLDOWN

    def shrink_ready(self):
        return (
            self.ability_lockout <= 0
            and self.shrink_active_timer <= 0
            and self.shrink_cooldown <= 0
            and not self.shrink_recharge_pending
        )

    def shield_progress(self):
        if self.shield_active:
            return 1.0
        if self.shield_recharge_pending:
            return 0.0
        return 1.0 - self.shield_cooldown / self.SHIELD_COOLDOWN

    def shield_ready(self):
        return (
            self.ability_lockout <= 0
            and not self.shield_active
            and self.shield_cooldown <= 0
            and not self.shield_recharge_pending
        )

    def projectile_progress(self):
        if self.projectile_recharge_pending:
            return 0.0
        return 1.0 - self.projectile_cooldown / self.PROJECTILE_COOLDOWN

    def projectile_ready(self):
        return (
            self.ability_lockout <= 0
            and self.projectile_cooldown <= 0
            and not self.projectile_recharge_pending
        )

    def move(self, keys, delta_time):
        direction = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
            keys[pygame.K_LEFT] or keys[pygame.K_a]
        )
        self.rect.x += round(direction * self.speed * delta_time)
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

    def draw(self, screen):
        # Blink during the short grace period after taking a hit.
        if self.invulnerability_timer > 0 and pygame.time.get_ticks() // 100 % 2 == 0:
            return
        screen.blit(self.image, self.rect)


class Asteroid:
    def __init__(
        self,
        image,
        speed,
        diagonal=False,
        grey_image=None,
        shooting_image=None,
        shooting=False,
    ):
        self.is_shooting = shooting and shooting_image is not None
        self.is_grey = (
            not self.is_shooting
            and grey_image is not None
            and random.random() < 0.5
        )
        if self.is_shooting:
            image = shooting_image
        elif self.is_grey:
            image = grey_image
        self.scale = random.uniform(1, 1.5)
        scaled_size = (
            max(1, round(image.get_width() * self.scale)),
            max(1, round(image.get_height() * self.scale)),
        )
        self.base_image = pygame.transform.smoothscale(image, scaled_size)
        self.speed = speed
        self.collisions = 0
        self.collision_limit = random.randint(2, 3)

        # Split diagonal speed across both axes so its overall speed stays unchanged.
        horizontal_speed = speed / math.sqrt(2) if diagonal else 0
        vertical_speed = speed / math.sqrt(2) if diagonal else speed
        self.velocity = pygame.Vector2(
            random.choice((-1, 1)) * horizontal_speed if diagonal else 0,
            vertical_speed,
        )
        if self.is_shooting:
            # Pygame rotates counterclockwise; the artwork's head points down-left.
            travel_angle = math.degrees(math.atan2(self.velocity.y, self.velocity.x))
            self.angle = (SHOOTING_METEOR_SOURCE_ANGLE - travel_angle) % 360
        else:
            self.angle = random.uniform(0, 360)
        self.spinning = not self.is_shooting and random.random() < 0.05
        self.rotation_speed = random.choice((-1, 1)) * random.uniform(90, 180)
        self.image = pygame.transform.rotate(self.base_image, self.angle)
        self.mask = pygame.mask.from_surface(self.image, threshold=0)
        self.rect = self.image.get_rect(
            midtop=(
                random.randint(
                    self.image.get_width() // 2,
                    WIDTH - self.image.get_width() // 2,
                ),
                -self.image.get_height(),
            )
        )
        self.position = pygame.Vector2(self.rect.center)
        self.has_entered_screen = False

    def face_velocity(self):
        if not self.is_shooting or not self.velocity:
            return

        travel_angle = math.degrees(math.atan2(self.velocity.y, self.velocity.x))
        angle = (SHOOTING_METEOR_SOURCE_ANGLE - travel_angle) % 360
        if math.isclose(angle, self.angle, abs_tol=1e-6):
            return

        center = self.rect.center
        self.angle = angle
        self.image = pygame.transform.rotate(self.base_image, self.angle)
        self.mask = pygame.mask.from_surface(self.image, threshold=0)
        self.rect = self.image.get_rect(center=center)

    def update(self, delta_time):
        self.position += self.velocity * delta_time
        self.face_velocity()
        if self.spinning:
            self.angle = (self.angle + self.rotation_speed * delta_time) % 360
            self.image = pygame.transform.rotate(self.base_image, self.angle)
            # Rebuild the mask after rotating so collisions follow visible pixels.
            self.mask = pygame.mask.from_surface(self.image, threshold=0)
        self.rect = self.image.get_rect(
            center=(round(self.position.x), round(self.position.y))
        )
        self.has_entered_screen = self.has_entered_screen or self.rect.bottom > 0

    def is_off_screen(self):
        return self.has_entered_screen and (
            self.rect.top >= HEIGHT
            or self.rect.right <= 0
            or self.rect.left >= WIDTH
            or self.rect.bottom <= 0
        )

    def draw(self, screen):
        screen.blit(self.image, self.rect)


class AsteroidExplosion:
    def __init__(self, frames, center, scale=1.0):
        self.frames = [
            pygame.transform.smoothscale(
                frame,
                (
                    max(1, round(frame.get_width() * scale)),
                    max(1, round(frame.get_height() * scale)),
                ),
            )
            for frame in frames
        ]
        self.center = center
        self.frame_duration = 0.075
        self.elapsed = 0.0
        self.frame_index = 0

    def update(self, delta_time):
        self.elapsed += delta_time
        self.frame_index = int(self.elapsed / self.frame_duration)

    @property
    def finished(self):
        return self.frame_index >= len(self.frames)

    def draw(self, screen):
        frame = self.frames[self.frame_index]
        screen.blit(frame, frame.get_rect(center=self.center)) 


class Rocket:
    def __init__(self, frames, frame_masks, start_center, speed=700):
        self.frames = frames
        self.frame_masks = frame_masks
        self.speed = speed
        self.elapsed = 0.0
        self.frame_duration = 0.08
        self.position = pygame.Vector2(start_center)
        self.image = self.frames[0]
        self.mask = self.frame_masks[0]
        self.rect = self.image.get_rect(midbottom=start_center)

    def update(self, delta_time):
        self.position.y -= self.speed * delta_time
        self.elapsed += delta_time
        frame_index = int(self.elapsed / self.frame_duration) % len(self.frames)
        self.image = self.frames[frame_index]
        self.mask = self.frame_masks[frame_index]
        self.rect = self.image.get_rect(
            center=(round(self.position.x), round(self.position.y))
        )

    def is_off_screen(self):
        return self.rect.bottom <= 0

    def draw(self, screen):
        screen.blit(self.image, self.rect)
