import pygame
from voice_input import VoiceController
from config import SCREEN_WIDTH, SCREEN_HEIGHT


class SpeechCorrector:
    """Handles the interactive word banner, typing overrides, and countdown execution."""

    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.pending_words = []
        self.pending_cmd = None
        self.editing_word_idx = None
        self.just_clicked_edit = False
        self.word_rects = []
        self.action_time = 0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            if self.editing_word_idx is not None:
                if event.key == pygame.K_RETURN:
                    self.pending_words = [w for w in self.pending_words if w.strip()]
                    combined_phrase = " ".join(self.pending_words)
                    self.pending_cmd = VoiceController._parse_full_phrase(combined_phrase)

                    self.editing_word_idx = None
                    if self.pending_cmd:
                        self.action_time = pygame.time.get_ticks() + 3000
                    return True

                elif event.key == pygame.K_ESCAPE:
                    self.editing_word_idx = None
                    if self.pending_cmd:
                        self.action_time = pygame.time.get_ticks() + 3000
                    return True

                elif event.key == pygame.K_BACKSPACE:
                    self.just_clicked_edit = False
                    self.pending_words[self.editing_word_idx] = self.pending_words[self.editing_word_idx][:-1]
                    return True

                else:
                    if self.just_clicked_edit:
                        self.pending_words[self.editing_word_idx] = ""
                        self.just_clicked_edit = False
                    self.pending_words[self.editing_word_idx] += event.unicode
                    return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked_a_word = False
                for i, rect in enumerate(self.word_rects):
                    if rect.collidepoint(event.pos):
                        self.editing_word_idx = i
                        self.just_clicked_edit = True
                        clicked_a_word = True
                        return True

                if not clicked_a_word and self.editing_word_idx is not None:
                    self.editing_word_idx = None
                    if self.pending_cmd:
                        self.action_time = pygame.time.get_ticks() + 3000
                    return True

        return False

    def update(self, new_voice_data: tuple, current_time: int) -> dict | None:
        if new_voice_data:
            cmd_dict, phrase = new_voice_data

            if self.editing_word_idx is not None and self.editing_word_idx < len(self.pending_words):
                new_words = phrase.split()
                self.pending_words = (
                        self.pending_words[:self.editing_word_idx] +
                        new_words +
                        self.pending_words[self.editing_word_idx + 1:]
                )
                combined_phrase = " ".join(self.pending_words)
                self.pending_cmd = VoiceController._parse_full_phrase(combined_phrase)
                self.editing_word_idx = None
            else:
                self.pending_words = phrase.split()
                self.pending_cmd = cmd_dict
                self.editing_word_idx = None

            # Start a countdown ONLY if it's a valid recognized command.
            if self.pending_cmd:
                self.action_time = current_time + 3000

        # Execute if timer runs out AND the command is fully valid.
        if self.pending_words and self.editing_word_idx is None:
            if self.pending_cmd is not None and current_time >= self.action_time:
                cmd_to_run = self.pending_cmd

                self.pending_words = []
                self.pending_cmd = None
                self.word_rects = []

                return cmd_to_run

        return None

    def draw(self, screen: pygame.Surface, current_time: int):
        if not self.pending_words:
            return

        base_color = (100, 255, 120) if self.pending_cmd else (255, 100, 100)
        word_surfaces = []

        for i, word in enumerate(self.pending_words):
            color = (255, 230, 100) if i == self.editing_word_idx else base_color
            display_word = word

            if i == self.editing_word_idx and (current_time // 500) % 2 == 0:
                display_word += "|"

            word_surfaces.append(self.font.render(display_word, True, color))

        # Status Suffix
        if self.editing_word_idx is not None:
            suffix_surf = self.font.render(" [Type or Speak...]", True, (255, 230, 100))
        elif self.pending_cmd is None:
            # Tell the user to fix it!
            suffix_surf = self.font.render(" [Unknown - Click to fix]", True, (255, 100, 100))
        else:
            seconds_left = max(0, (self.action_time - current_time) // 1000) + 1
            suffix_surf = self.font.render(f" (in {seconds_left}s)", True, base_color)

        space_w = self.font.size(" ")[0]
        total_width = sum(s.get_width() for s in word_surfaces) + (
                    len(word_surfaces) - 1) * space_w + suffix_surf.get_width()
        max_h = max([s.get_height() for s in word_surfaces] + [suffix_surf.get_height()])

        start_x = (SCREEN_WIDTH / 2) - (total_width / 2)
        start_y = SCREEN_HEIGHT - 60

        bg_rect = pygame.Rect(start_x - 20, start_y - 15, total_width + 40, max_h + 30)
        pygame.draw.rect(screen, (30, 32, 42), bg_rect, border_radius=10)
        pygame.draw.rect(screen, base_color, bg_rect, width=2, border_radius=10)

        curr_x = start_x
        self.word_rects.clear()

        for i, surf in enumerate(word_surfaces):
            rect = surf.get_rect(topleft=(curr_x, start_y))
            screen.blit(surf, rect)
            self.word_rects.append(rect.inflate(12, 20))
            curr_x += surf.get_width() + space_w

        screen.blit(suffix_surf, (curr_x, start_y))