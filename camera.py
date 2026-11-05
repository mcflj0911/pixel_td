import math

import numpy as np
import pygame

from config import (SCREEN_WIDTH, RENDER_W, RENDER_H, CAM_POS, CAM_TARGET, CAM_FOV, SKY, FOG_COLOUR,
                    FOG_START, FOG_END, MAP_COLS, MAP_ROWS, TILE_COLOURS)
from world import make_map

SCALE = SCREEN_WIDTH // RENDER_W  # Screen pixels per render pixel
MAX_CACHED_FLOORS = 8  # Floor images are kept for the last few maps, so switching back is instant


class Camera:
    """A perspective camera looking down on the map.

    The floor is ray-cast for every render pixel (the same idea as the zombie game's column rays, but
    against the ground plane, since this map has no walls). Sprites are billboards placed with project().
    """

    def __init__(self, game_map=None):
        self.pos = np.array(CAM_POS, dtype=float)
        f = np.array(CAM_TARGET, dtype=float) - self.pos
        self.f = f / np.linalg.norm(f)  # Forward
        r = np.cross([0.0, 0.0, 1.0], self.f)  # Right: +x points to the right of the screen, as on the radar
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.f, self.r)  # Up
        self.cx, self.cy = RENDER_W / 2, RENDER_H / 2
        self.focal = self.cx / math.tan(math.radians(CAM_FOV) / 2)
        self._build_rays()
        self._floors = {}
        self.image = None
        self.use_map(game_map or make_map(0))

    def _build_rays(self):
        # Ray direction through the middle of every render pixel, then where each ray meets the floor.
        # This does not depend on the map, so it is done once
        xs = (np.arange(RENDER_W) + 0.5 - self.cx) / self.focal
        ys = (np.arange(RENDER_H) + 0.5 - self.cy) / self.focal
        d = (self.f[None, None, :] + xs[:, None, None] * self.r[None, None, :]
             - ys[None, :, None] * self.u[None, None, :])
        dz = d[..., 2]
        self.floor_mask = dz < -1e-6  # Rays pointing down hit the floor. The rest see sky
        t = -self.pos[2] / np.where(self.floor_mask, dz, -1.0)
        self._hx = self.pos[0] + t * d[..., 0]
        self._hy = self.pos[1] + t * d[..., 1]
        self._depth = t * (d @ self.f)

    def use_map(self, game_map):
        if game_map.index not in self._floors:
            if len(self._floors) >= MAX_CACHED_FLOORS:
                self._floors.pop(next(iter(self._floors)))
            self._floors[game_map.index] = self._make_floor(game_map)
        self.image = self._floors[game_map.index]

    def _make_floor(self, game_map):
        hx, hy = self._hx, self._hy
        if not hasattr(self, "_grain"):
            self._grain = np.random.default_rng(11).random(hx.shape)
        col = np.floor(hx).astype(int)
        row = np.floor(hy).astype(int)
        inside = (col >= 0) & (col < MAP_COLS) & (row >= 0) & (row < MAP_ROWS)
        cc = np.clip(col, 0, MAP_COLS - 1)
        rr = np.clip(row, 0, MAP_ROWS - 1)
        on_path = game_map.mask[cc, rr] & inside
        alt = (cc + rr) % 2
        # Palette index: 0/1 grass, 2/3 path (checkered), 4 outside the map
        kind = np.where(inside, np.where(on_path, 2, 0) + alt, 4)

        # Thin darker lines on tile edges, and a little variation per tile
        edge = (np.abs(hx - np.round(hx)) < 0.04) | (np.abs(hy - np.round(hy)) < 0.04)
        variation = np.where(inside, game_map.variation[cc, rr], 1.0)
        shade = variation * np.where(edge & inside, 0.8, 1.0)
        grain = 1 + 0.07 * (self._grain - 0.5)  # Same grain every map: a fixed pattern of light specks
        shade = np.where(inside, shade * grain, shade)

        fog = np.clip((self._depth - FOG_START) / (FOG_END - FOG_START), 0, 1) * self.floor_mask

        # The lighting never changes, so the whole floor and sky are worked out once per map
        palette = np.array(TILE_COLOURS, dtype=np.float32)
        fog_colour = np.array(FOG_COLOUR, dtype=np.float32)
        rgb = palette[kind] * shade[..., None]
        rgb = rgb * (1 - fog[..., None]) + fog_colour * fog[..., None]
        grad = 0.82 + 0.18 * (np.arange(RENDER_H) / RENDER_H)  # Sky is a little darker at the top
        sky = np.array(SKY, dtype=np.float32)[None, None, :] * grad[None, :, None].astype(np.float32)
        sky = np.broadcast_to(sky, (RENDER_W, RENDER_H, 3))
        image = np.where(self.floor_mask[..., None], rgb, sky)
        return np.clip(image, 0, 255).astype(np.uint8)

    def render_floor(self, surface):
        """Fill a render-sized surface with the floor and sky of the current map."""
        pygame.surfarray.blit_array(surface, self.image)

    def project(self, x, y, z=0.0):
        """World point to render pixel: (x, y, depth), or None if it is behind the camera."""
        v = np.array([x, y, z], dtype=float) - self.pos
        depth = float(v @ self.f)
        if depth < 0.1:
            return None
        sx = self.cx + self.focal * float(v @ self.r) / depth
        sy = self.cy - self.focal * float(v @ self.u) / depth
        return sx, sy, depth

    def screen_to_tile(self, sx, sy):
        """The (col, row) of the map tile under a full-size screen pixel, or None if off the map."""
        px, py = sx / SCALE, sy / SCALE
        d = self.f + ((px - self.cx) / self.focal) * self.r - ((py - self.cy) / self.focal) * self.u
        if d[2] >= -1e-9:
            return None  # Above the horizon
        t = -self.pos[2] / d[2]
        col = math.floor(self.pos[0] + t * d[0])
        row = math.floor(self.pos[1] + t * d[1])
        if 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS:
            return col, row
        return None
