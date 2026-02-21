"""Camera system for infinite scrolling world."""

import math
import random


class Camera:
    """Viewport that smooth-follows the player through infinite world space.

    All game entities store world-space coordinates. The camera converts
    world-space to screen-space for rendering and provides culling helpers.
    """

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        # Camera position = world coords of the viewport center
        self.x = 0.0
        self.y = 0.0
        # Velocity (for parallax/speed lines)
        self.vx = 0.0
        self.vy = 0.0
        # Smoothing factor (0 = no follow, 1 = instant snap)
        self.lerp_speed = 0.08

    def follow(self, target_x, target_y):
        """Smooth-follow a world-space target (usually the player center)."""
        prev_x, prev_y = self.x, self.y
        self.x += (target_x - self.x) * self.lerp_speed
        self.y += (target_y - self.y) * self.lerp_speed
        self.vx = self.x - prev_x
        self.vy = self.y - prev_y

    def snap_to(self, target_x, target_y):
        """Instantly center on target (used at game start / wormhole exit)."""
        self.x = target_x
        self.y = target_y
        self.vx = 0.0
        self.vy = 0.0

    def world_to_screen(self, wx, wy):
        """Convert world coordinates to screen coordinates."""
        sx = wx - self.x + self.screen_width / 2
        sy = wy - self.y + self.screen_height / 2
        return sx, sy

    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates."""
        wx = sx + self.x - self.screen_width / 2
        wy = sy + self.y - self.screen_height / 2
        return wx, wy

    def is_visible(self, wx, wy, margin=200):
        """Check if a world-space point is within the visible viewport + margin."""
        sx, sy = self.world_to_screen(wx, wy)
        return (-margin <= sx <= self.screen_width + margin and
                -margin <= sy <= self.screen_height + margin)

    def get_visible_rect(self, margin=0):
        """Return (left, top, right, bottom) in world-space for the visible area."""
        half_w = self.screen_width / 2 + margin
        half_h = self.screen_height / 2 + margin
        return (self.x - half_w, self.y - half_h,
                self.x + half_w, self.y + half_h)

    def follow_midpoint(self, x1, y1, x2, y2):
        """Smooth-follow the midpoint between two world-space targets."""
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        self.follow(mx, my)

    def get_spawn_ring(self, min_dist=400, max_dist=600):
        """Get a random world-space position on a ring around the viewport.

        Used by the spawner to place new enemies just off-screen.
        """
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(min_dist, max_dist)
        # Offset from camera center, biased by viewport shape
        # so spawns appear at roughly equal screen-edge distance
        half_w = self.screen_width / 2
        half_h = self.screen_height / 2
        # Scale the ring to account for rectangular viewport
        wx = self.x + math.cos(angle) * (half_w + dist)
        wy = self.y + math.sin(angle) * (half_h + dist)
        return wx, wy

    def get_spawn_ring_for_coop(self, p1_pos, p2_pos, min_dist=400, max_dist=600):
        """Get a spawn position outside BOTH players' viewports.

        Used in co-op mode so enemies don't pop in on either player's screen.
        """
        half_w = self.screen_width / 2
        half_h = self.screen_height / 2
        for _ in range(10):  # Try up to 10 times
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(min_dist, max_dist)
            # Pick a random center between the two players
            cx = (p1_pos[0] + p2_pos[0]) / 2
            cy = (p1_pos[1] + p2_pos[1]) / 2
            wx = cx + math.cos(angle) * (half_w + dist)
            wy = cy + math.sin(angle) * (half_h + dist)
            # Check that it's outside both viewports
            d1 = max(abs(wx - p1_pos[0]) - half_w, abs(wy - p1_pos[1]) - half_h)
            d2 = max(abs(wx - p2_pos[0]) - half_w, abs(wy - p2_pos[1]) - half_h)
            if d1 > 100 and d2 > 100:
                return wx, wy
        # Fallback: just use camera center
        return self.get_spawn_ring(min_dist, max_dist)
