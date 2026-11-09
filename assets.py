"""Asset loading helpers for sprites, backgrounds, and animation sheets."""

import pygame

from settings import ASSET_DIR, HEIGHT, WIDTH


def load_trimmed_image(filename, size):
    """Scale an image after cropping transparent padding around its artwork."""
    image = pygame.image.load(str(ASSET_DIR / filename)).convert_alpha()
    bounds = image.get_bounding_rect()
    image = image.subsurface(bounds).copy()
    return pygame.transform.smoothscale(image, size)


def load_background(filename):
    """Center-crop a wide background image to the game window's aspect ratio."""
    image = pygame.image.load(str(ASSET_DIR / filename)).convert_alpha()
    source_width, source_height = image.get_size()
    crop_width = min(source_width, round(source_height * WIDTH / HEIGHT))
    crop = pygame.Rect(0, 0, crop_width, source_height)
    crop.centerx = source_width // 2
    image = image.subsurface(crop).copy()
    return pygame.transform.smoothscale(image, (WIDTH, HEIGHT))


def load_explosion_frames(filename):
    """Slice the horizontal sprite sheet into square, enlarged animation frames."""
    return load_sprite_sheet_frames(filename)


def load_sprite_sheet_frames(filename, display_scale=1.5):
    """Slice a horizontal sheet of square frames and scale them for display."""
    sheet = pygame.image.load(str(ASSET_DIR / filename)).convert_alpha()
    frame_size = sheet.get_height()
    if frame_size == 0 or sheet.get_width() % frame_size:
        raise ValueError(f"Sprite sheet must contain square frames: {filename}")

    display_size = round(frame_size * display_scale)
    return [
        pygame.transform.smoothscale(
            sheet.subsurface(
                pygame.Rect(index * frame_size, 0, frame_size, frame_size)
            ),
            (display_size, display_size),
        )
        for index in range(sheet.get_width() // frame_size)
    ]
