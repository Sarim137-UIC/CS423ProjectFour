import sys
import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR,
    GRID_COLOR, GRID_SIZE, TEXT_COLOR, SUBTEXT_COLOR,
    PLAYER_SIZE, PLAYER_SPEED, PLAYER_STEP_SIZE,
    SIGN_SIZE, SIGN_A_COLOR, SIGN_B_COLOR
)
from player import Player
from voice_input import VoiceController
from corrector import SpeechCorrector


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Voice your Adventure")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("Arial", 18, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.large_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.bottom_font = pygame.font.SysFont("Arial", 32, bold=True)

        # Assign grid-aligned positions for the new signs
        self.sign_a_pos = (180, 180)  # Top Left area
        self.sign_b_pos = (620, 180)  # Top Right area

        self.player = Player(
            x=(SCREEN_WIDTH - PLAYER_SIZE) / 2,
            y=(SCREEN_HEIGHT - PLAYER_SIZE) / 2,
            size=PLAYER_SIZE,
            speed=PLAYER_SPEED,
            step_size=PLAYER_STEP_SIZE
        )
        self.voice_controller = VoiceController()
        self.corrector = SpeechCorrector(self.bottom_font)

        self.is_running = False
        self.is_paused = False

    def run(self):
        self.voice_controller.start()
        self.is_running = True

        while self.is_running:
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(FPS)

        self._cleanup()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False

            # 1. corrector
            elif self.corrector.handle_event(event):
                continue

            # 2. game binds
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False
                elif event.key == pygame.K_m:
                    self.voice_controller.cycle_microphone()

    def _update(self):
        new_data = self.voice_controller.get_latest_command()
        current_time = pygame.time.get_ticks()

        command_to_execute = self.corrector.update(new_data, current_time)

        if command_to_execute:
            action_str = command_to_execute.get("action")

            if action_str == "exit_game":
                self.is_running = False
            elif action_str == "pause_game":
                self.is_paused = True
            elif action_str == "resume_game":
                self.is_paused = False
            elif not self.is_paused:
                self.player.handle_command(
                    command_data=command_to_execute,
                    sign_a_pos=self.sign_a_pos,
                    sign_b_pos=self.sign_b_pos,
                    sign_size=SIGN_SIZE
                )

        if not self.is_paused:
            self.player.update()

    def _draw_environment(self):
        self.screen.fill(BG_COLOR)
        for x in range(0, SCREEN_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))

    def _draw_signs(self):
        # Draw Sign A (Red)
        rect_a = pygame.Rect(0, 0, SIGN_SIZE, SIGN_SIZE)
        rect_a.center = self.sign_a_pos
        pygame.draw.rect(self.screen, SIGN_A_COLOR, rect_a, border_radius=6)
        text_a = self.font.render("A", True, (255, 255, 255))
        self.screen.blit(text_a, text_a.get_rect(center=self.sign_a_pos))

        # Draw Sign B (Blue)
        rect_b = pygame.Rect(0, 0, SIGN_SIZE, SIGN_SIZE)
        rect_b.center = self.sign_b_pos
        pygame.draw.rect(self.screen, SIGN_B_COLOR, rect_b, border_radius=6)
        text_b = self.font.render("B", True, (255, 255, 255))
        self.screen.blit(text_b, text_b.get_rect(center=self.sign_b_pos))

    def _draw_hud(self):
        status_text = "PAUSED" if self.is_paused else self.player.status_description
        mic_name = self.voice_controller.active_mic_name

        status_surf = self.font.render(f"Status: {status_text}", True, TEXT_COLOR)
        mic_surf = self.small_font.render(f"Mic [Press M to switch]: {mic_name}", True, (130, 204, 221))

        self.screen.blit(status_surf, (20, 20))
        self.screen.blit(mic_surf, (20, 48))

        self.corrector.draw(self.screen, pygame.time.get_ticks())

        if self.is_paused:
            pause_text = self.large_font.render("GAME PAUSED", True, (255, 100, 100))
            text_rect = pause_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(pause_text, text_rect)

    def _render(self):
        self._draw_environment()
        self._draw_signs()
        self.player.draw(self.screen)
        self._draw_hud()
        pygame.display.flip()

    def _cleanup(self):
        self.voice_controller.stop()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()