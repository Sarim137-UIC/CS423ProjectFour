import math
import pygame
from config import PLAYER_COLOR, SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE


class Player:
    """Represents the player avatar supporting grid-block distances and multi-sign."""

    def __init__(self, x: float, y: float, size: int, speed: float, step_size: int = 50):
        self.start_x, self.start_y = x, y
        self.x, self.y = x, y
        self.size = size
        self.speed = speed
        self.default_step_size = GRID_SIZE

        self.remaining_step = 0
        self.step_direction = None

        self.is_homing = False
        self.target_coords = None
        self.status_description = "IDLE"

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.size, self.size)

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.size / 2, self.y + self.size / 2)

    def handle_command(self, command_data: dict, sign_a_pos: tuple, sign_b_pos: tuple, sign_size: int):
        if not command_data:
            return

        command = command_data.get("action")
        distance = command_data.get("distance")

        # Handle Sign Anchors dynamically
        if command and command.startswith("sign_"):
            parts = command.split("_")  # e.g., ["sign", "a", "left"]
            sign_letter = parts[1]
            relative_pos = parts[2] if len(parts) > 2 else "center"

            # Select coordinates and labels based on the target
            cx, cy = sign_a_pos if sign_letter == "a" else sign_b_pos
            display_name = "SIGN A" if sign_letter == "a" else "SIGN B"

            offset = (sign_size / 2) + (self.size / 2) + 15

            if relative_pos == "left":
                self._set_homing((cx - offset, cy), f"HOMING: LEFT OF {display_name}")
            elif relative_pos == "right":
                self._set_homing((cx + offset, cy), f"HOMING: RIGHT OF {display_name}")
            elif relative_pos == "above":
                self._set_homing((cx, cy - offset), f"HOMING: ABOVE {display_name}")
            elif relative_pos == "below":
                self._set_homing((cx, cy + offset), f"HOMING: BELOW {display_name}")
            else:
                self._set_homing((cx, cy), f"HOMING: TO {display_name}")

        # Start
        elif command == "to_start":
            self._set_homing((self.start_x + self.size / 2, self.start_y + self.size / 2), "RETURNING TO START")

        # Standard Grid Controls
        elif command in ("up", "down", "left", "right"):
            self.is_homing = False
            self.target_coords = None
            self.step_direction = command

            if distance is not None:
                actual_dist = distance * GRID_SIZE
                block_count = distance
            else:
                actual_dist = GRID_SIZE
                block_count = 1

            self.remaining_step = actual_dist
            self.status_description = f"STEPPING: {command.upper()} ({block_count} BLOCKS)"

        elif command == "stop":
            self.is_homing = False
            self.target_coords = None
            self.remaining_step = 0
            self.step_direction = None
            self.status_description = "STOPPED"

    def _set_homing(self, coords, status_text):
        self.is_homing = True
        self.target_coords = coords
        self.status_description = status_text
        self.remaining_step = 0
        self.step_direction = None

    def update(self, arrival_radius: float = 8.0):
        if self.is_homing and self.target_coords is not None:
            tx, ty = self.target_coords
            dx = tx - self.center[0]
            dy = ty - self.center[1]
            dist = math.hypot(dx, dy)

            if dist <= arrival_radius:
                self.is_homing = False
                self.target_coords = None
                self.status_description = "ARRIVED"
            else:
                move_dist = min(self.speed, dist)
                self.x += (dx / dist) * move_dist
                self.y += (dy / dist) * move_dist

        elif self.remaining_step > 0 and self.step_direction:
            move_amount = min(self.speed, self.remaining_step)
            if self.step_direction == "up":
                self.y -= move_amount
            elif self.step_direction == "down":
                self.y += move_amount
            elif self.step_direction == "left":
                self.x -= move_amount
            elif self.step_direction == "right":
                self.x += move_amount

            self.remaining_step -= move_amount
            if self.remaining_step <= 0:
                self.step_direction = None
                self.status_description = "IDLE"

        self._clamp_to_bounds()

    def _clamp_to_bounds(self):
        self.x = max(0, min(self.x, SCREEN_WIDTH - self.size))
        self.y = max(0, min(self.y, SCREEN_HEIGHT - self.size))

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, PLAYER_COLOR, self.rect, border_radius=6)