import math
import random
import sys
import json
from dataclasses import dataclass

import pygame

pygame.init()
pygame.mixer.init()

# -------------------------
# Window / board settings
# -------------------------
WINDOW_WIDTH = 920
WINDOW_HEIGHT = 760
BOARD_SIZE = 8
SQUARE_SIZE = 80
BOARD_PIXEL_SIZE = BOARD_SIZE * SQUARE_SIZE
BOARD_X = 40
BOARD_Y = 70
FPS = 60

# -------------------------
# Colors
# -------------------------
BACKGROUND = (45, 30, 20)  
LIGHT_SQUARE = (233, 216, 180)
DARK_SQUARE = (90, 62, 43)
BOARD_BORDER = (200, 170, 100)
FOX_COLOR = (244, 244, 244)
FOX_OUTLINE = (210, 210, 210)
HOUND_COLOR = (30, 30, 30)
HOUND_OUTLINE = (80, 80, 80)
TEXT_COLOR = (240, 220, 170) 
SUBTEXT_COLOR = (210, 190, 140)
BUTTON_COLOR = (138, 214, 38)  
BUTTON_HOVER = (161, 235, 58)
BUTTON_SHADOW = (46, 112, 10)
BUTTON_OUTLINE = (52, 120, 12)
BUTTON_TEXT = (245, 255, 230)
POPUP_COLOR = (40, 40, 48)
POPUP_BORDER = (220, 190, 120)
GOLD_GLOW = (255, 215, 90)
SOFT_BLACK = (10, 10, 10)
TRANSPARENT_BLACK = (0, 0, 0, 150)

# -------------------------
# Piece / role names
# -------------------------
FOX = "fox"
HOUND = "hound"


@dataclass
class Move:
    #data structure to store one move.
    start_row: int
    start_col: int
    end_row: int
    end_col: int


class Piece:
    #Represents a single fox or hound piece.
    def __init__(self, row, col, piece_type):
        self.row = row
        self.col = col
        self.piece_type = piece_type

        # screen coordinates are updated after the game knows the board orientation
        self.pixel_x = 0
        self.pixel_y = 0
        self.target_x = 0
        self.target_y = 0
        self.is_animating = False

        # piece glide speed
        self.speed = 14  

    def update_screen_position(self, game):
        #Place the piece exactly on the center of its current board square.
        x, y = game.get_square_top_left(self.row, self.col)
        self.pixel_x = x + SQUARE_SIZE // 2
        self.pixel_y = y + SQUARE_SIZE // 2
        self.target_x = self.pixel_x
        self.target_y = self.pixel_y
        self.is_animating = False

    def start_animation(self, game, new_row, new_col):
        #Start a smooth glide animation to a new square.
        self.row = new_row
        self.col = new_col
        x, y = game.get_square_top_left(new_row, new_col)
        self.target_x = x + SQUARE_SIZE // 2
        self.target_y = y + SQUARE_SIZE // 2
        self.is_animating = True

    def update_animation(self):
        #Move the piece a little each frame until it reaches the target square.
        if not self.is_animating:
            return

        dx = self.target_x - self.pixel_x
        dy = self.target_y - self.pixel_y
        distance = math.hypot(dx, dy)

        if distance <= self.speed:
            self.pixel_x = self.target_x
            self.pixel_y = self.target_y
            self.is_animating = False
            return

        if distance != 0:
            self.pixel_x += (dx / distance) * self.speed
            self.pixel_y += (dy / distance) * self.speed

    def draw(self, surface):
        #Draw the piece as a flat circle with a subtle outline.
        center = (int(self.pixel_x), int(self.pixel_y))
        radius = 28

        if self.piece_type == FOX:
            outer = FOX_OUTLINE
            inner = FOX_COLOR
        else:
            outer = HOUND_OUTLINE
            inner = HOUND_COLOR

        pygame.draw.circle(surface, outer, center, radius + 3)
        pygame.draw.circle(surface, inner, center, radius)
        pygame.draw.circle(surface, (255, 255, 255, 20), center, radius, 1)


class Button:
    """Simple UI button for restart / new game."""

    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, surface, font, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        pressed = hovered and pygame.mouse.get_pressed()[0]

        top_color = BUTTON_HOVER if hovered else BUTTON_COLOR
        bottom_color = BUTTON_COLOR if hovered else BUTTON_SHADOW
        draw_rect = self.rect.move(0, 4 if not pressed else 8)
        shadow_rect = self.rect.move(0, 10)

        # shadow
        pygame.draw.ellipse(surface, (25, 60, 8), (shadow_rect.x + 12, shadow_rect.y + shadow_rect.height - 6, shadow_rect.width - 24, 18))

        # outer base
        pygame.draw.rect(surface, BUTTON_OUTLINE, draw_rect, border_radius=28)
        inner_rect = draw_rect.inflate(-6, -6)

        # bottom half
        pygame.draw.rect(surface, bottom_color, inner_rect, border_radius=26)

        # glossy top half
        top_half = pygame.Rect(inner_rect.x, inner_rect.y, inner_rect.width, inner_rect.height // 2 + 6)
        pygame.draw.rect(surface, top_color, top_half, border_radius=26)

        # extra shine
        shine = pygame.Surface((inner_rect.width, inner_rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(shine, (255, 255, 255, 80), (12, 6, inner_rect.width - 24, inner_rect.height // 2 - 4))
        pygame.draw.ellipse(shine, (255, 255, 255, 120), (18, 10, 55, 18))
        pygame.draw.ellipse(shine, (255, 255, 255, 100), (inner_rect.width - 82, inner_rect.height - 28, 54, 16))
        surface.blit(shine, inner_rect.topleft)

        label = font.render(self.text, True, BUTTON_TEXT)
        label_shadow = font.render(self.text, True, (80, 120, 20))
        label_rect = label.get_rect(center=inner_rect.center)
        surface.blit(label_shadow, label_rect.move(2, 2))
        surface.blit(label, label_rect)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


class FoxAndHoundsGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Fox and Hounds - AI Project")
        self.clock = pygame.time.Clock()

        # Fonts
        self.title_font = pygame.font.SysFont("georgia", 64, bold=True)
        self.main_font = pygame.font.SysFont("arial", 36, bold=True)
        self.text_font = pygame.font.SysFont("arial", 22)
        self.small_font = pygame.font.SysFont("arial", 17)
        self.popup_font = pygame.font.SysFont("georgia", 32, bold=True)

        # -------------------------
        # Sounds
        # -------------------------
        try:
            self.bg_music = pygame.mixer.music
            pygame.mixer.music.load("bg_music.mp3")
            pygame.mixer.music.set_volume(0.25)
            pygame.mixer.music.play(-1)  # loop forever
        except:
            pass

        self.click_sound = None
        self.move_sound = None
        self.fox_move_sound = None
        self.win_sound = None
        self.lose_sound = None

        try:
            self.click_sound = pygame.mixer.Sound("click.mp3")
        except:
            pass
        try:
            self.move_sound = pygame.mixer.Sound("move.mp3")
        except:
            pass
        try:
            self.fox_move_sound = pygame.mixer.Sound("fox_move.mp3")
        except:
            pass
        try:
            # try wav first, then mp3
            try:
                self.win_sound = pygame.mixer.Sound("win.wav")
            except:
                self.win_sound = pygame.mixer.Sound("win.mp3")
            self.win_sound.set_volume(1.0)
        except:
            pass
        try:
            # user said lose file is not mp3, so try wav first, then mp3
            try:
                self.lose_sound = pygame.mixer.Sound("lose.wav")
            except:
                self.lose_sound = pygame.mixer.Sound("lose.mp3")
            self.lose_sound.set_volume(1.0)
        except:
            pass

        # Piece images
        self.fox_piece_img = None
        self.hound_piece_img = None
        try:
            self.fox_piece_img = pygame.image.load("fox_icon.png").convert_alpha()
            self.fox_piece_img = pygame.transform.smoothscale(self.fox_piece_img, (64, 64))
        except:
            pass

        try:
            self.hound_piece_img = pygame.image.load("hound_icon.png").convert_alpha()
            self.hound_piece_img = pygame.transform.smoothscale(self.hound_piece_img, (80, 64))
        except:
            pass

        # Buttons
        self.restart_button = Button((700, 50, 170, 48), "Restart Match")
        self.new_game_button = Button((700, 105, 170, 48), "New Game")
        self.rules_button = Button((280, 520, 320, 75), "How to Play")
        self.reset_learning_button = Button((700, 160, 170, 48), "Reset Learning")
        self.train_button = Button((700, 215, 170, 48), "Train 10 Games")
        self.rules_close_rect = pygame.Rect(770, 90, 42, 42)
        self.show_rules_overlay = False

        # Menu state
        self.state = "menu"   # menu / playing / game_over
        self.player_side = None
        self.ai_side = None
        self.bottom_side = None  # chosen side shown at the bottom
        self.control_mode = "human_vs_ai"

        # Turn and selection state
        self.current_turn = HOUND
        self.selected_piece = None
        self.highlighted_moves = []
        self.winner = None

        # Turn banner settings
        self.turn_message = ""
        self.turn_message_timer = 0
        self.turn_message_duration = 120  # about 2 sec at 60 FPS

        # Intro heading animation when the game screen opens
        self.intro_title = ""
        self.intro_title_timer = 0
        self.intro_title_duration = 120

        # AI timing
        self.ai_wait_frames = 48  # base pause before AI moves
        self.extra_player_delay = 40  # extra delay after YOUR move
        self.ai_timer = 0
        self.game_over_delay = 120  # ~2 seconds (60 FPS)
        self.game_over_timer = 0

        # Board and piece storage
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.pieces = []
        self.fox = None
        self.hounds = []

        self.setup_menu_buttons()

        # Learning weights
        self.weights = {
            "fox_progress": 10,
            "hound_distance": 2,
            "hound_ahead": 5
        }
        self.load_weights()
        self.fox_wins = 0
        self.hound_wins = 0
        self.move_count = 0
        self.match_history = []
        self.training_games_remaining = 0

    # --------------------------------------------------------
    # Menu setup
    # --------------------------------------------------------
    def save_weights(self):
         # save current AI weights to a file 
        try:
            with open("weights.json", "w") as f:
                json.dump(self.weights, f)
        except:
            pass

    def load_weights(self):
         # load saved AI weights from file if it exists
        try:
            with open("weights.json", "r") as f:
                self.weights = json.load(f)
        except:
            pass

    def clamp_weights(self):
        # keep weights within reasonable limits to avoid extreme behavior
        self.weights["fox_progress"] = max(5, min(20, self.weights["fox_progress"]))
        self.weights["hound_distance"] = max(1, min(10, self.weights["hound_distance"]))
        self.weights["hound_ahead"] = max(1, min(10, self.weights["hound_ahead"]))

    def reset_learning(self):
        # reset AI learning progress and stats to default values
        self.weights = {
            "fox_progress": 10,
            "hound_distance": 2,
            "hound_ahead": 5
        }
        self.fox_wins = 0
        self.hound_wins = 0
        self.match_history = []
        self.training_games_remaining = 0
        self.save_weights()

    def apply_learning_result(self, winner):
         # adjust weights based on winner to improve AI strategy over time
        if self.control_mode == "ai_vs_ai":
           if winner == HOUND:
            self.weights["hound_distance"] += 2.0
            self.weights["hound_ahead"] += 2.0
           else:
            self.weights["fox_progress"] += 2.0

        if winner == FOX:
            self.fox_wins += 1
        else:
            self.hound_wins += 1

        history_line = f"{winner.capitalize()} won | W:{round(self.weights['fox_progress'],1)}/{round(self.weights['hound_distance'],1)}/{round(self.weights['hound_ahead'],1)}"
        self.match_history.insert(0, history_line)
        self.match_history = self.match_history[:5]

    def setup_menu_buttons(self):
         # initialize main menu buttons for the different game modes
        self.play_fox_button = Button((280, 320, 320, 75), "Play as Fox")
        self.play_hounds_button = Button((280, 420, 320, 75), "Play as Hounds")
        self.ai_vs_ai_button = Button((280, 620, 320, 75), "Watch AI vs AI")

    # --------------------------------------------------------
    # New game / reset
    # --------------------------------------------------------
    def setup_new_match(self, chosen_side):
        """
        Starting a fresh game.
        If player chooses FOX, fox is shown at the bottom.
        If player chooses HOUND, hounds are shown at the bottom.
        """
        self.control_mode = "human_vs_ai"
        self.player_side = chosen_side
        self.ai_side = FOX if chosen_side == HOUND else HOUND
        # Set orientation so player's side appears at bottom
        if chosen_side == FOX:
            # Fox starts at row 7 -> already bottom, so no flip
            self.bottom_side = HOUND
        else:
            # Hounds start at row 0 -> flip board to bring them to bottom
            self.bottom_side = FOX
        self.state = "playing"
        
        # standard game starts with hounds
        self.current_turn = HOUND  
        self.selected_piece = None
        self.highlighted_moves = []
        self.winner = None
        self.ai_timer = 0
        self.move_count = 0

        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.pieces = []
        self.hounds = []
        self.fox = None

        self.create_initial_pieces()
        self.place_all_pieces_on_board()
        self.update_all_piece_screen_positions()
        self.intro_title = "You are Hounds" if chosen_side == HOUND else "You are Fox"
        self.intro_title_timer = self.intro_title_duration
        self.show_turn_message()
        # if AI goes first, delay its first move
        if self.current_turn == self.ai_side:
            # adding extra delay for first move
            self.ai_timer = self.ai_wait_frames + 90  

    def setup_ai_vs_ai_match(self):
         # initialize a new AI vs AI game state and reset all game variables
        self.control_mode = "ai_vs_ai"
        self.player_side = None
        self.ai_side = None
        self.bottom_side = HOUND
        self.state = "playing"

        self.current_turn = HOUND
        self.selected_piece = None
        self.highlighted_moves = []
        self.winner = None
        self.ai_timer = 3 if self.training_games_remaining > 0 else self.ai_wait_frames + 30
        self.move_count = 0

        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.pieces = []
        self.hounds = []
        self.fox = None

        self.create_initial_pieces()
        self.place_all_pieces_on_board()
        self.update_all_piece_screen_positions()
        self.intro_title = "AI vs AI"
        self.intro_title_timer = self.intro_title_duration
        self.show_turn_message("AI vs AI Running")

    def restart_same_match(self):
        """Restart with the same chosen side."""
        if self.control_mode == "ai_vs_ai":
            self.setup_ai_vs_ai_match()
        elif self.player_side is not None:
            self.setup_new_match(self.player_side)

    def create_initial_pieces(self):
        """
        Standard layout:
        - Hounds start on row 0 at columns 1,3,5,7
        - Fox starts on row 7 at column 0
        Only dark squares are used.
        """
        for col in [1, 3, 5, 7]:
            h = Piece(0, col, HOUND)
            self.hounds.append(h)
            self.pieces.append(h)

        self.fox = Piece(7, 0, FOX)
        self.pieces.append(self.fox)

    def place_all_pieces_on_board(self):
         #place all pieces onto the board based on their coordinates
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                self.board[row][col] = None

        for piece in self.pieces:
            self.board[piece.row][piece.col] = piece

    def update_all_piece_screen_positions(self):
         # update visual positions of all pieces on the screen
        for piece in self.pieces:
            piece.update_screen_position(self)

    # --------------------------------------------------------
    # Board orientation helpers
    # --------------------------------------------------------
    def logical_to_display(self, row, col):
        """
        Convert logical board coordinates to display coordinates.

        If bottom_side == HOUND:
            show board in normal orientation.

        If bottom_side == FOX:
            rotate board 180 degrees so fox side appears at bottom.
        """
        if self.bottom_side == HOUND:
            return row, col
        return 7 - row, 7 - col

    def display_to_logical(self, display_row, display_col):
        #Reverse of logical_to_display()
        if self.bottom_side == HOUND:
            return display_row, display_col
        return 7 - display_row, 7 - display_col

    def get_square_top_left(self, logical_row, logical_col):
        #Return top-left pixel of a logical square after orientation is applied
        display_row, display_col = self.logical_to_display(logical_row, logical_col)
        x = BOARD_X + display_col * SQUARE_SIZE
        y = BOARD_Y + display_row * SQUARE_SIZE
        return x, y

    def pixel_to_logical_square(self, x, y):
        #Convert mouse click position to logical board square
        if not (BOARD_X <= x < BOARD_X + BOARD_PIXEL_SIZE and BOARD_Y <= y < BOARD_Y + BOARD_PIXEL_SIZE):
            return None

        display_col = (x - BOARD_X) // SQUARE_SIZE
        display_row = (y - BOARD_Y) // SQUARE_SIZE
        return self.display_to_logical(display_row, display_col)

    # --------------------------------------------------------
    # Board rules
    # --------------------------------------------------------
    def is_dark_square(self, row, col):
        return (row + col) % 2 == 1

    def is_inside_board(self, row, col):
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    def get_piece_at(self, row, col):
        if not self.is_inside_board(row, col):
            return None
        return self.board[row][col]

    def get_legal_moves_for_piece(self, piece):
        """
        Standard Fox and Hounds movement rules:
        - Fox moves diagonally forward and backward (4 possible directions)
        - Hounds move diagonally forward only (toward increasing row)
        - Move only one square diagonally to an empty dark square
        """
        legal_moves = []

        if piece.piece_type == FOX:
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        else:
            if piece.row > self.fox.row:
                return []
            directions = [(1, -1), (1, 1)]

        for dr, dc in directions:
            new_row = piece.row + dr
            new_col = piece.col + dc

            if self.is_inside_board(new_row, new_col) and self.is_dark_square(new_row, new_col):
                if self.board[new_row][new_col] is None:
                    legal_moves.append(Move(piece.row, piece.col, new_row, new_col))

        return legal_moves

    def get_all_legal_moves(self, side):
        #if fox has passed all hounds, hounds cannot move
        if side == HOUND:
            if all(hound.row > self.fox.row for hound in self.hounds):
                return []

        moves = []
        for piece in self.pieces:
            if piece.piece_type == side:
                moves.extend(self.get_legal_moves_for_piece(piece))
        return moves

    def move_piece(self, move):
        """
        Applying the move to the internal board and start animation.
        method does not immediately switch turn until the animation finishes.
        """
        piece = self.board[move.start_row][move.start_col]
        if piece is None:
            return

        self.board[move.start_row][move.start_col] = None
        self.board[move.end_row][move.end_col] = piece
        self.move_count += 1

        # Keep current screen position where it was, then animate to new target.
        piece.start_animation(self, move.end_row, move.end_col)

    def all_animations_finished(self):
        return all(not piece.is_animating for piece in self.pieces)

    def check_winner(self):
        # if fox reaches top, it wins
        if self.fox.row == 0:
            return FOX

        # if fox passed all hounds, fox wins
        if all(hound.row > self.fox.row for hound in self.hounds):
            return FOX
        
        if self.fox_is_unstoppable():
            return FOX

        # if fox has no moves, hounds win
        fox_moves = self.get_legal_moves_for_piece(self.fox)
        if len(fox_moves) == 0:
            return HOUND

        return None

    def choose_best_move_for_side(self, side):
         #using minimax with alpha-beta pruning to select the best move for a given side
        legal_moves = self.get_all_legal_moves(side)
        if not legal_moves:
            return None

        best_move = None
        depth = 6

        scored_moves = []

        if side == HOUND:
             #maximize evaluation score for Hounds
            best_eval = -float('inf')
            for move in legal_moves:
                self.make_move(move)
                eval = self.minimax(depth - 1, -float('inf'), float('inf'), False)
                self.undo_move(move)
                scored_moves.append((move, eval))
                if eval > best_eval:
                    best_eval = eval
                    best_move = move

            if self.control_mode == "ai_vs_ai":
              close_moves = [move for move, eval in scored_moves if eval >= best_eval - 2]
              if close_moves:
               best_move = random.choice(close_moves)
        else:
            #minimize evaluation score for Fox
            best_eval = float('inf')
            for move in legal_moves:
                self.make_move(move)
                eval = self.minimax(depth - 1, -float('inf'), float('inf'), True)
                self.undo_move(move)
                scored_moves.append((move, eval))
                if eval < best_eval:
                    best_eval = eval
                    best_move = move

            if self.control_mode == "ai_vs_ai":
                #add randomness by choosing among close scoring moves
              close_moves = [move for move, eval in scored_moves if eval <= best_eval + 2]
              if close_moves:
               best_move = random.choice(close_moves)

        return best_move

    def choose_ai_move(self):
         #get the best move for the current AI-controlled side
        return self.choose_best_move_for_side(self.ai_side)

    def side_is_ai_controlled(self, side):
         #check if a side is controlled by AI based on game mode
        if self.control_mode == "ai_vs_ai":
            return True
        return side == self.ai_side

    # --------------------------------------------------------
    # Turn / message handling
    # --------------------------------------------------------
    def format_turn_message(self):
        if self.control_mode == "ai_vs_ai":
            return "Hounds' Turn" if self.current_turn == HOUND else "Fox's Turn"

        # If it's player's turn
        if self.current_turn == self.player_side:
            return "Your Turn"

        # If it's AI turn
        if self.current_turn == HOUND:
            return "Hounds' Turn"
        else:
            return "Fox's Turn"

    def show_turn_message(self, text=None):
        if text is None:
            text = self.format_turn_message()
        self.turn_message = text
        self.turn_message_timer = self.turn_message_duration

    def switch_turn(self):
        self.current_turn = FOX if self.current_turn == HOUND else HOUND
        self.selected_piece = None
        self.highlighted_moves = []

        self.winner = self.check_winner()
        if self.winner is not None:
            self.state = "game_over"

            self.apply_learning_result(self.winner)
            self.game_over_timer = self.game_over_delay

            try:
                if self.control_mode == "human_vs_ai":
                    if self.winner == self.player_side and self.win_sound is not None:
                        self.win_sound.play()
                    elif self.winner != self.player_side and self.lose_sound is not None:
                        self.lose_sound.play()
            except:
                pass
            return

        self.show_turn_message()
        if self.side_is_ai_controlled(self.current_turn):
            #add extra delay after player's move 
            self.ai_timer = self.ai_wait_frames + self.extra_player_delay

    # --------------------------------------------------------
    # Event handling
    # --------------------------------------------------------
    def handle_events(self):
        #handle all game events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()

                if self.state == "menu":
                    self.handle_menu_click(mouse_pos)
                elif self.state in ("playing", "game_over"):
                    self.handle_button_clicks(mouse_pos)
                    if self.state == "playing":
                        self.handle_board_click(mouse_pos)

    def handle_menu_click(self, mouse_pos):
         #handle clicks in the main menu
        if self.show_rules_overlay:
            if self.rules_close_rect.collidepoint(mouse_pos):
                try:
                    self.click_sound.play()
                except:
                    pass
                self.show_rules_overlay = False
            return

        if self.play_fox_button.is_clicked(mouse_pos):
            try:
                self.click_sound.play()
            except:
                pass
            self.setup_new_match(FOX)
        elif self.play_hounds_button.is_clicked(mouse_pos):
            try:
                self.click_sound.play()
            except:
                pass
            self.setup_new_match(HOUND)
        elif self.rules_button.is_clicked(mouse_pos):
            try:
                self.click_sound.play()
            except:
                pass
            self.show_rules_overlay = True
        elif self.ai_vs_ai_button.is_clicked(mouse_pos):
            try:
                self.click_sound.play()
            except:
                pass
            self.setup_ai_vs_ai_match()

    def handle_button_clicks(self, mouse_pos):
        if self.restart_button.is_clicked(mouse_pos):
            try:
                self.click_sound.play()
            except:
                pass
            self.restart_same_match()
        elif self.new_game_button.is_clicked(mouse_pos):
            try:
                self.click_sound.play()
            except:
                pass
            self.state = "menu"
            self.player_side = None
            self.ai_side = None
            self.bottom_side = None
            self.control_mode = "human_vs_ai"
            self.training_games_remaining = 0
        elif self.reset_learning_button.is_clicked(mouse_pos):
            try:
                self.click_sound.play()
            except:
                pass
            self.reset_learning()
        elif self.train_button.is_clicked(mouse_pos):
            try:
                self.click_sound.play()
            except:
                pass
            self.training_games_remaining = 10
            self.setup_ai_vs_ai_match()

    def handle_board_click(self, mouse_pos):
         #process player interaction with the game board
        if self.control_mode == "ai_vs_ai":
            #disable user input during AI vs AI mode
            return

        # ignore clicks during animation or AI turn
        if not self.all_animations_finished():
            return
        if self.current_turn != self.player_side:
             #ignore input when it's not the player's turn
            return

        square = self.pixel_to_logical_square(*mouse_pos)
        if square is None:
            return

        row, col = square
        clicked_piece = self.get_piece_at(row, col)

        # ----------------------------------------------------
        # FOX interaction rule:
        # Do not click the fox piece first.
        # Instead, legal destination squares are always highlighted
        # on the player's fox turn, and clicking one moves the fox.
        # ----------------------------------------------------
        if self.player_side == FOX and self.current_turn == FOX:
            fox_moves = self.get_legal_moves_for_piece(self.fox)
            self.highlighted_moves = fox_moves

            for move in fox_moves:
                if move.end_row == row and move.end_col == col:
                    self.move_piece(move)
                    try:
                        if self.player_side == FOX:
                            self.fox_move_sound.play()
                        else:
                            self.move_sound.play()
                    except:
                        pass
                    return
            #ignore invalid clicks
            return  

        # ----------------------------------------------------
        # HOUND interaction rule:
        # Click a hound first, then choose highlighted destination.
        # ----------------------------------------------------
        if self.player_side == HOUND and self.current_turn == HOUND:
            if clicked_piece is not None and clicked_piece.piece_type == HOUND:
                self.selected_piece = clicked_piece
                self.highlighted_moves = self.get_legal_moves_for_piece(clicked_piece)
                return

            for move in self.highlighted_moves:
                if move.end_row == row and move.end_col == col:
                    self.move_piece(move)
                    try:
                        if self.player_side == FOX:
                            self.fox_move_sound.play()
                        else:
                            self.move_sound.play()
                    except:
                        pass
                    self.selected_piece = None
                    self.highlighted_moves = []
                    return

            # if wrong click, nothing happens
            return

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------
    def update(self):
        if self.state == "menu":
            return

        # Always update animations.
        for piece in self.pieces:
            piece.update_animation()

        # For fox player, keep possible destination squares visible during fox turn
        if self.state == "playing" and self.player_side == FOX and self.current_turn == FOX and self.all_animations_finished():
            self.highlighted_moves = self.get_legal_moves_for_piece(self.fox)

        #after animations finish, prepare to switch turn
        if self.state == "playing" and self.all_animations_finished():
            pass

        #track when a move animation is happening
        if not hasattr(self, "_awaiting_turn_switch"):
            self._awaiting_turn_switch = False

        # Set flag when any animation starts
        if any(piece.is_animating for piece in self.pieces):
            self._awaiting_turn_switch = True

        #switch turn once after animation ends
        if self._awaiting_turn_switch and self.all_animations_finished():
            self._awaiting_turn_switch = False
            self.switch_turn()

        # AI move after a short delay.
        if self.state == "playing" and self.side_is_ai_controlled(self.current_turn) and self.all_animations_finished():
            if self.ai_timer > 0:
                self.ai_timer -= 1
            else:
                ai_move = self.choose_best_move_for_side(self.current_turn)
                 #if no moves available, end game and determine winner
                if ai_move is None:
                    self.winner = FOX if self.current_turn == HOUND else HOUND
                    self.state = "game_over"
                    #apply learning and play win/lose sound 
                    self.apply_learning_result(self.winner)
                    try:
                        if self.control_mode == "human_vs_ai":
                            if self.winner == self.player_side and self.win_sound is not None:
                                self.win_sound.play()
                            elif self.winner != self.player_side and self.lose_sound is not None:
                                self.lose_sound.play()
                    except:
                        pass
                else:
                    #execute AI move and play appropriate sound
                    self.move_piece(ai_move)
                    try:
                        if self.current_turn == FOX and self.fox_move_sound is not None:
                            self.fox_move_sound.play()
                        elif self.current_turn == HOUND and self.move_sound is not None:
                            self.move_sound.play()
                    except:
                        pass
                    
        #update timers for UI messages
        if self.turn_message_timer > 0:
            self.turn_message_timer -= 1

        if self.intro_title_timer > 0:
            self.intro_title_timer -= 1

        #automatically restart games during AI training mode
        if self.state == "game_over" and self.training_games_remaining > 0:
             if self.control_mode == "ai_vs_ai":
                if self.game_over_timer > 0:
                   self.game_over_timer -= 1
                else:
                   self.training_games_remaining -= 1
                   if self.training_games_remaining > 0:
                      self.setup_ai_vs_ai_match()

    # --------------------------------------------------------
    # Draw methods
    # --------------------------------------------------------
    def draw_background(self):
        self.screen.fill(BACKGROUND)

    def draw_title_and_info(self):
        title_shadow1 = self.title_font.render("Fox and Hounds", True, (0, 0, 0))
        title_shadow2 = self.title_font.render("Fox and Hounds", True, (120, 90, 40))
        title = self.title_font.render("Fox and Hounds", True, TEXT_COLOR)

        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2 - 60, 35))
        self.screen.blit(title_shadow1, title_rect.move(5, 5))
        self.screen.blit(title_shadow2, title_rect.move(2, 2))
        self.screen.blit(title, title_rect)

        # Side panel text
        info_x = 700
        info_y = 300

        if self.control_mode == "ai_vs_ai":
            player_text = self.main_font.render("Mode: AI vs AI", True, TEXT_COLOR)
            ai_text = self.main_font.render("", True, TEXT_COLOR)
        else:
            player_text = self.main_font.render(f"You are: {self.player_side.capitalize() if self.player_side else '-'}", True, TEXT_COLOR)
            ai_text = self.main_font.render(f"AI is: {self.ai_side.capitalize() if self.ai_side else '-'}", True, TEXT_COLOR)

        # Styled current turn 
        turn_text = self.format_turn_message()

        turn_color = (255, 215, 90) if self.current_turn == self.player_side else (255, 120, 120)
        if self.control_mode == "ai_vs_ai":
            turn_color = (255, 215, 90)

        turn_line = self.main_font.render(turn_text, True, turn_color)

        self.screen.blit(player_text, (info_x, info_y))
        self.screen.blit(ai_text, (info_x, info_y + 50))

        self.screen.blit(turn_line, (info_x, info_y + 130))

        # show learning weights
        w1 = self.small_font.render(f"Fox Progress: {round(self.weights['fox_progress'],1)}", True, SUBTEXT_COLOR)
        w2 = self.small_font.render(f"Hound Dist: {round(self.weights['hound_distance'],1)}", True, SUBTEXT_COLOR)
        w3 = self.small_font.render(f"Hound Ahead: {round(self.weights['hound_ahead'],1)}", True, SUBTEXT_COLOR)

        self.screen.blit(w1, (info_x, info_y + 200))
        self.screen.blit(w2, (info_x, info_y + 230))
        self.screen.blit(w3, (info_x, info_y + 260))

        s1 = self.small_font.render(f"Fox Wins: {self.fox_wins}", True, SUBTEXT_COLOR)
        s2 = self.small_font.render(f"Hound Wins: {self.hound_wins}", True, SUBTEXT_COLOR)
        s3 = self.small_font.render(f"Moves This Match: {self.move_count}", True, SUBTEXT_COLOR)
        s4 = self.small_font.render(f"Training Left: {self.training_games_remaining}", True, SUBTEXT_COLOR)
        self.screen.blit(s1, (info_x, info_y + 305))
        self.screen.blit(s2, (info_x, info_y + 330))
        self.screen.blit(s3, (info_x, info_y + 355))
        self.screen.blit(s4, (info_x, info_y + 380))

        history_title = self.small_font.render("Recent History:", True, TEXT_COLOR)
        self.screen.blit(history_title, (info_x, info_y + 415))
        for i, entry in enumerate(self.match_history[:5]):
            h = self.small_font.render(entry, True, SUBTEXT_COLOR)
            self.screen.blit(h, (info_x, info_y + 440 + i * 22))

        return

        for i, line in enumerate(lines):
            color = TEXT_COLOR if i in [0, 1, 2, 4] else SUBTEXT_COLOR
            label = self.small_font.render(line, True, color)
            self.screen.blit(label, (info_x, info_y + i * 24))

    def draw_board(self):
        # Border around board
        border_rect = pygame.Rect(BOARD_X - 4, BOARD_Y - 4, BOARD_PIXEL_SIZE + 8, BOARD_PIXEL_SIZE + 8)
        pygame.draw.rect(self.screen, BOARD_BORDER, border_rect, border_radius=8)

        # Squares
        for logical_row in range(BOARD_SIZE):
            for logical_col in range(BOARD_SIZE):
                display_row, display_col = self.logical_to_display(logical_row, logical_col)
                x = BOARD_X + display_col * SQUARE_SIZE
                y = BOARD_Y + display_row * SQUARE_SIZE
                color = DARK_SQUARE if self.is_dark_square(logical_row, logical_col) else LIGHT_SQUARE
                pygame.draw.rect(self.screen, color, (x, y, SQUARE_SIZE, SQUARE_SIZE))

    def draw_highlights(self):
        """Draw gradient golden borders (dark edges → lighter inner glow)."""
        for move in self.highlighted_moves:
            x, y = self.get_square_top_left(move.end_row, move.end_col)

            # Create layered gradient border effect
            # thickness layers
            for i in range(6):  
                # increasing brightness inward
                alpha = int(60 + i * 30)  
                color = (GOLD_GLOW[0], GOLD_GLOW[1], GOLD_GLOW[2], alpha)

                glow_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                pygame.draw.rect(
                    glow_surface,
                    color,
                    (i, i, SQUARE_SIZE - 2 * i, SQUARE_SIZE - 2 * i),
                    width=2,
                    border_radius=10
                )
                self.screen.blit(glow_surface, (x, y))

            # subtle inner fill glow 
            inner_glow = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(inner_glow, (255, 230, 140, 25), (8, 8, SQUARE_SIZE - 16, SQUARE_SIZE - 16), border_radius=10)
            self.screen.blit(inner_glow, (x, y))

    def draw_pieces(self):
        #draw all pieces on the board
        for piece in self.pieces:
            center_x = int(piece.pixel_x)
            center_y = int(piece.pixel_y)
            
            # draw fox using image if available
            if piece.piece_type == FOX and self.fox_piece_img is not None:
                rect = self.fox_piece_img.get_rect(center=(center_x, center_y))
                self.screen.blit(self.fox_piece_img, rect)
            
            #draw hound using image if available
            elif piece.piece_type == HOUND and self.hound_piece_img is not None:
                rect = self.hound_piece_img.get_rect(center=(center_x, center_y))
                self.screen.blit(self.hound_piece_img, rect)

             #fallback drawing if no image is provided
            else:
                piece.draw(self.screen)

    def draw_turn_banner(self):
        #display intro title with fade effect
        if False:
            pass

        if self.intro_title_timer > 0 and self.intro_title:
            alpha_ratio = self.intro_title_timer / self.intro_title_duration
            alpha = int(255 * min(1.0, alpha_ratio * 1.4))

            #create shadow and main text
            title_shadow = self.title_font.render(self.intro_title, True, (0, 0, 0))
            title_text = self.title_font.render(self.intro_title, True, TEXT_COLOR)
            title_shadow.set_alpha(alpha)
            title_text.set_alpha(alpha)

            #draw centered title with shadow
            title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2 - 120, WINDOW_HEIGHT // 2 - 20))
            self.screen.blit(title_shadow, title_rect.move(5, 5))
            self.screen.blit(title_text, title_rect)

    def draw_popup(self):
        if self.state != "game_over":
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill(TRANSPARENT_BLACK)
        self.screen.blit(overlay, (0, 0))

        popup_rect = pygame.Rect(240, 250, 440, 180)
        pygame.draw.rect(self.screen, POPUP_COLOR, popup_rect, border_radius=22)
        pygame.draw.rect(self.screen, POPUP_BORDER, popup_rect, width=3, border_radius=22)

        if self.winner == FOX:
            message = "Fox Wins!"
        else:
            message = "Hounds Win!"

        line1 = self.popup_font.render(message, True, TEXT_COLOR)
        line2 = self.text_font.render("Press Restart Match or New Game", True, SUBTEXT_COLOR)

        self.screen.blit(line1, line1.get_rect(center=(popup_rect.centerx, popup_rect.y + 62)))
        self.screen.blit(line2, line2.get_rect(center=(popup_rect.centerx, popup_rect.y + 112)))

    def draw_menu(self):
        # dark modern background (blackish-grey gradient)
        for y in range(WINDOW_HEIGHT):
            ratio = y / WINDOW_HEIGHT
            r = int(22 + (48 - 22) * ratio)
            g = int(22 + (48 - 22) * ratio)
            b = int(28 + (62 - 28) * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        # faded background image support
        try:
            bg = pygame.image.load("bg.png").convert_alpha()
            bg = pygame.transform.scale(bg, (WINDOW_WIDTH, WINDOW_HEIGHT))
            bg.set_alpha(45)
            self.screen.blit(bg, (0, 0))
        except:
            pass

        # soft center glow
        glow = pygame.Surface((760, 520), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 255, 255, 28), (0, 0, 760, 520))
        self.screen.blit(glow, (80, 85))

        # title
        title_shadow1 = self.title_font.render("Fox and Hounds", True, (0, 0, 0))
        title_shadow2 = self.title_font.render("Fox and Hounds", True, (130, 130, 130))
        title = self.title_font.render("Fox and Hounds", True, (255, 255, 255))
        fun_line = self.text_font.render("Choose your side and start the chase!", True, (210, 210, 210))

        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 165))
        self.screen.blit(title_shadow1, title_rect.move(6, 6))
        self.screen.blit(title_shadow2, title_rect.move(2, 2))
        self.screen.blit(title, title_rect)
        self.screen.blit(fun_line, fun_line.get_rect(center=(WINDOW_WIDTH // 2, 248)))

        # decorative side glows behind characters
        left_glow = pygame.Surface((240, 240), pygame.SRCALPHA)
        pygame.draw.circle(left_glow, (255, 255, 255, 24), (120, 120), 120)
        self.screen.blit(left_glow, (70, 255))

        right_glow = pygame.Surface((290, 290), pygame.SRCALPHA)
        pygame.draw.circle(right_glow, (255, 255, 255, 24), (145, 145), 145)
        self.screen.blit(right_glow, (560, 230))

        mouse_pos = pygame.mouse.get_pos()
        self.play_fox_button.draw(self.screen, self.main_font, mouse_pos)
        self.play_hounds_button.draw(self.screen, self.main_font, mouse_pos)
        self.rules_button.draw(self.screen, self.main_font, mouse_pos)
        self.ai_vs_ai_button.draw(self.screen, self.main_font, mouse_pos)

        # fox image 
        try:
            fox_img = pygame.image.load("fox_menu.png").convert_alpha()
            fox_img = pygame.transform.smoothscale(fox_img, (220, 220))
            offset = int(5 * math.sin(pygame.time.get_ticks() * 0.005))
            self.screen.blit(fox_img, (75, 270 + offset))
        except:
            pass

        # hound image 
        try:
            hound_img = pygame.image.load("hounds_menu.png").convert_alpha()
            hound_img = pygame.transform.smoothscale(hound_img, (280, 280))
            offset = int(5 * math.sin(pygame.time.get_ticks() * 0.005 + 2))
            self.screen.blit(hound_img, (600, 245 + offset))
        except:
            pass

        if self.show_rules_overlay:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 185))
            self.screen.blit(overlay, (0, 0))

            panel_rect = pygame.Rect(110, 85, 700, 560)
            panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
            # gradient panel 
            for i in range(panel_rect.height):
                shade = 30 + int(20 * (i / panel_rect.height))
                pygame.draw.line(panel, (shade, shade, shade + 10, 245), (0, i), (panel_rect.width, i))

            # soft golden border
            pygame.draw.rect(panel, (255, 215, 120), (0, 0, panel_rect.width, panel_rect.height), width=2, border_radius=26)
            self.screen.blit(panel, panel_rect.topleft)

            close_hover = self.rules_close_rect.collidepoint(mouse_pos)
            close_color = (235, 90, 90) if close_hover else (185, 185, 195)
            pygame.draw.circle(self.screen, close_color, self.rules_close_rect.center, 18)
            x_font = pygame.font.SysFont("arial", 26, bold=True)
            x_label = x_font.render("×", True, (25, 25, 25))
            self.screen.blit(x_label, x_label.get_rect(center=self.rules_close_rect.center))

            rules_title_shadow = self.popup_font.render("How to Play", True, (0, 0, 0))
            rules_title = self.popup_font.render("How to Play", True, (255, 230, 180))
            self.screen.blit(rules_title_shadow, (147, 122))
            self.screen.blit(rules_title, (145, 120))

            rule_lines = [
                "• Hounds move first.",
                "• Fox can move diagonally forward and backward.",
                "• Hounds can move diagonally forward only.",
                "• Fox wins by reaching the opposite side of the board.",
                "• Hounds win by trapping the fox so it cannot move.",
                "• If you play as Fox, just click a glowing destination square.",
                "• If you play as Hounds, click a hound first, then a glowing square.",
                "• Green buttons on the game screen let you restart or start over."
            ]

            y = 195
            for line in rule_lines:
                color = (235, 235, 245) if (y // 48) % 2 == 0 else (200, 200, 210)
                label = self.text_font.render(line, True, color)
                self.screen.blit(label, (145, y))
                y += 48

    def draw_game(self):
        self.draw_background()
        self.draw_title_and_info()
        self.draw_board()
        self.draw_highlights()
        self.draw_pieces()
        self.draw_turn_banner()

        mouse_pos = pygame.mouse.get_pos()
        self.restart_button.draw(self.screen, self.text_font, mouse_pos)
        self.new_game_button.draw(self.screen, self.text_font, mouse_pos)
        self.reset_learning_button.draw(self.screen, self.text_font, mouse_pos)
        self.train_button.draw(self.screen, self.text_font, mouse_pos)

        if self.state == "game_over":
            self.draw_popup()
            # redraw buttons after popup overlay so they stay bright
            self.restart_button.draw(self.screen, self.text_font, mouse_pos)
            self.new_game_button.draw(self.screen, self.text_font, mouse_pos)
            self.reset_learning_button.draw(self.screen, self.text_font, mouse_pos)
            self.train_button.draw(self.screen, self.text_font, mouse_pos)

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    #implement minimax with alpha-beta pruning
    def minimax(self, depth, alpha, beta, is_maximizing):
        winner = self.check_winner()
        if winner == HOUND:
            return 1000 + depth
        if winner == FOX:
            return -1000 - depth
        if depth == 0:
            #evaluate board when max depth is reached
            return self.evaluate_for_hounds() - self.evaluate_for_fox()

        if is_maximizing:
            #hounds try to maximize the score
            max_eval = -float('inf')
            for move in self.get_all_legal_moves(HOUND):
                self.make_move(move)
                eval = self.minimax(depth - 1, alpha, beta, False)
                self.undo_move(move)

                #update best score and alpha value
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)

                # Alpha-beta pruning
                if beta <= alpha:
                    break
            return max_eval
        else:
            # Fox tries to minimize the score
            min_eval = float('inf')
            for move in self.get_all_legal_moves(FOX):
                self.make_move(move)
                eval = self.minimax(depth - 1, alpha, beta, True)
                self.undo_move(move)

                 #update best score and beta value
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                 #alpha-beta pruning
                if beta <= alpha:
                    break
            return min_eval

    def evaluate_for_hounds(self):
     score = 0
     fox = self.fox
     fox_moves = self.get_legal_moves_for_piece(fox)

     # Hounds want fox far from top
     score += fox.row * 18

     # Limit fox mobility
     score += (4 - len(fox_moves)) * 20

     # Hounds ahead = good
     hounds_ahead = sum(1 for h in self.hounds if h.row <= fox.row)
     score += hounds_ahead * 15

     # Closer hounds = better trap
     for hound in self.hounds:
        dist = abs(hound.row - fox.row) + abs(hound.col - fox.col)
        score += max(0, 10 - dist) * 3

     return score


    def evaluate_for_fox(self):
     #evaluate board position from fox's perspective
     score = 0
     fox = self.fox
     fox_moves = self.get_legal_moves_for_piece(fox)

     # Fox wants to reach top
     score -= fox.row * 20

     # More available moves = better mobility
     score += len(fox_moves) * 15

     #reward forward moves
     forward_moves = sum(1 for m in fox_moves if m.end_row < fox.row)
     score += forward_moves * 20

     # Penalize having hounds blocking ahead
     hounds_ahead = sum(1 for h in self.hounds if h.row <= fox.row)
     score -= hounds_ahead * 20

     return score

    # Helper methods for Minimax simulation
    def make_move(self, move):
        piece = self.board[move.start_row][move.start_col]
        self.board[move.start_row][move.start_col] = None
        self.board[move.end_row][move.end_col] = piece
        piece.row, piece.col = move.end_row, move.end_col

    def undo_move(self, move):
        piece = self.board[move.end_row][move.end_col]
        self.board[move.end_row][move.end_col] = None
        self.board[move.start_row][move.start_col] = piece
        piece.row, piece.col = move.start_row, move.start_col

    def fox_is_unstoppable(self):
        #check if the fox has a guaranteed forward path to win
        fox_moves = self.get_legal_moves_for_piece(self.fox)

        has_forward_move = False

        for move in fox_moves:
             #look for forward moves
            if move.end_row < self.fox.row:  
                has_forward_move = True
                can_be_blocked = False

                #check if any hound can block this move
                for hound in self.hounds:
                    if hound.row <= move.end_row and abs(hound.col - move.end_col) <= 1:
                        can_be_blocked = True
                        break
                #if a forward move can be blocked, fox is not unstoppable
                if can_be_blocked:
                    return False

        # Only unstoppable if all forward moves are safe
        return has_forward_move

    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------
    def run(self):
        #main game loop (runs continuously)
        while True:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()


if __name__ == "__main__":
    #start the game
    game = FoxAndHoundsGame()
    game.run()

