import pygame
import random
import os

# --- Environment Setup for Codespaces ---
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"

# --- Configuration Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 850
TILE_WIDTH, TILE_HEIGHT = 50, 70
GRID_X, GRID_Y = 55, 75
BOARD_BOUNDARY = 500
RACK_START_Y = 600
SAFE_WIDTH = SCREEN_WIDTH - 180 
COLORS = [(220, 30, 30), (30, 30, 220), (220, 180, 0), (20, 20, 20)] 
BG_COLOR = (34, 139, 34)

class Tile:
    def __init__(self, number, color_val, x, y, owner):
        self.number = number
        self.color_val = color_val
        self.rect = pygame.Rect(x, y, TILE_WIDTH, TILE_HEIGHT)
        self.dragging = False
        self.owner = owner # 0: Board, 1: P1, 2: P2

    def snap(self):
        self.rect.x = round(self.rect.x / GRID_X) * GRID_X
        self.rect.y = round(self.rect.y / GRID_Y) * GRID_Y
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - TILE_WIDTH))
        self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - TILE_HEIGHT))

    def draw(self, screen, font, alpha=255):
        surf = pygame.Surface((TILE_WIDTH, TILE_HEIGHT), pygame.SRCALPHA)
        bg_col = (255, 255, 255, alpha) if not self.dragging else (200, 200, 200, alpha)
        pygame.draw.rect(surf, bg_col, (0, 0, TILE_WIDTH, TILE_HEIGHT), border_radius=5)
        pygame.draw.rect(surf, (0, 0, 0, alpha), (0, 0, TILE_WIDTH, TILE_HEIGHT), 2, border_radius=5)
        text_col = list(self.color_val) + [alpha]
        text = font.render(str(self.number), True, text_col)
        text_rect = text.get_rect(center=(TILE_WIDTH // 2, TILE_HEIGHT // 2))
        surf.blit(text, text_rect)
        screen.blit(surf, self.rect)

def create_pool():
    pool = []
    for color in COLORS:
        for num in range(1, 14):
            pool.extend([(num, color), (num, color)])
    random.shuffle(pool)
    return pool

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2-Player Rummikub")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 22, bold=True)
    big_font = pygame.font.SysFont("Arial", 50, bold=True)

    # --- UI Elements & States ---
    state = "MENU"
    menu_btns = {
        "play": pygame.Rect(SCREEN_WIDTH//2 - 100, 350, 200, 60),
        "rules": pygame.Rect(SCREEN_WIDTH//2 - 100, 430, 200, 60),
        "quit": pygame.Rect(SCREEN_WIDTH//2 - 100, 510, 200, 60)
    }
    back_btn = pygame.Rect(50, 40, 220, 50)

    # --- Game Variables ---
    pool, tiles_in_play, ghost_tiles = [], [], []
    current_player = 1
    player_initials = {1: False, 2: False}
    status_msg = ""
    selected_tile = None
    game_over = False

    game_btns = {
        "draw": pygame.Rect(1030, 540, 140, 45),
        "sort": pygame.Rect(1030, 600, 140, 45),
        "reset": pygame.Rect(1030, 660, 140, 45),
        "pass": pygame.Rect(1030, 720, 140, 45)
    }

    # --- Helper Functions ---
    def draw_wrapped_text(surface, text, x, y, max_width, line_height):
        words = text.split(' ')
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] < max_width:
                current_line = test_line
            else:
                line_surf = font.render(current_line, True, (255, 255, 255))
                surface.blit(line_surf, (x, y))
                y += line_height
                current_line = word + " "
        line_surf = font.render(current_line, True, (255, 255, 255))
        surface.blit(line_surf, (x, y))
        return y + line_height

    def sort_hand(p_id):
        p_tiles = [t for t in tiles_in_play if t.owner == p_id]
        p_tiles.sort(key=lambda x: (x.color_val, x.number))
        tiles_per_row = (SAFE_WIDTH - 50) // GRID_X
        for i, t in enumerate(p_tiles):
            row, col = i // tiles_per_row, i % tiles_per_row
            t.rect.x = 50 + (col * GRID_X)
            t.rect.y = RACK_START_Y + (row * GRID_Y)
            t.snap()

    def update_ghosts():
        nonlocal ghost_tiles
        ghost_tiles = [Tile(t.number, t.color_val, t.rect.x, t.rect.y, 0) for t in tiles_in_play if t.owner == 0]

    def reset_game():
        nonlocal pool, tiles_in_play, ghost_tiles, current_player, player_initials, status_msg, game_over
        pool = create_pool()
        tiles_in_play, current_player, game_over = [], 1, False
        player_initials = {1: False, 2: False}
        status_msg = "P1: Lay 30 pts or Draw"
        for p in [1, 2]:
            for _ in range(14):
                n, c = pool.pop()
                tiles_in_play.append(Tile(n, c, 0, 0, p))
            sort_hand(p)
        update_ghosts()

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if state == "MENU":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if menu_btns["play"].collidepoint(event.pos):
                        reset_game()
                        state = "PLAYING"
                    elif menu_btns["rules"].collidepoint(event.pos):
                        state = "RULES"
                    elif menu_btns["quit"].collidepoint(event.pos):
                        running = False

            elif state == "RULES":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_btn.collidepoint(event.pos):
                        state = "MENU"

            elif state == "PLAYING":
                if not game_over:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if game_btns["sort"].collidepoint(event.pos): sort_hand(current_player)
                        if game_btns["pass"].collidepoint(event.pos):
                            current_player = 2 if current_player == 1 else 1
                            status_msg = f"Player {current_player}'s Turn"
                        # Handle tile selection
                        for t in reversed(tiles_in_play):
                            if t.rect.collidepoint(event.pos) and (t.owner == current_player or t.owner == 0):
                                selected_tile, t.dragging = t, True
                                off_x, off_y = t.rect.x - event.pos[0], t.rect.y - event.pos[1]
                                tiles_in_play.remove(t); tiles_in_play.append(t)
                                break

                    if event.type == pygame.MOUSEBUTTONUP and selected_tile:
                        selected_tile.dragging = False; selected_tile.snap()
                        selected_tile.owner = 0 if selected_tile.rect.y < BOARD_BOUNDARY else current_player
                        selected_tile = None

                    if event.type == pygame.MOUSEMOTION and selected_tile:
                        selected_tile.rect.x, selected_tile.rect.y = mouse_pos[0] + off_x, mouse_pos[1] + off_y

        # --- Rendering ---
        screen.fill(BG_COLOR)

        if state == "MENU":
            title = big_font.render("RUMMIKUB", True, (255, 255, 255))
            screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 200)))
            
            for key, rect in menu_btns.items():
                color = (100, 100, 100) if rect.collidepoint(mouse_pos) else (60, 60, 60)
                pygame.draw.rect(screen, color, rect, border_radius=10)
                txt = font.render(key.upper(), True, (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=rect.center))

        elif state == "RULES":
            # Header
            header = big_font.render("GAME RULES", True, (255, 255, 0))
            screen.blit(header, header.get_rect(center=(SCREEN_WIDTH//2, 80)))

            rules_list = [
                "1. Each player starts with 14 tiles.",
                "2. Drag tiles to the board to play them.",
                "3. First play must be worth 30+ points.",
                "4. All plays must be sets or runs.",
                "5. Sets are 3+ tiles of same number, but different colors. No duplicate tiles are allowed.",
                "6. Runs are 3+ tiles of consecutive numbers with the same color.",
                "7. You are allowed to manipulate all tiles on the board as long as the end result is legal.",
                "8. A legal board means every tile is in a set or run with no mistakes."
            ]
            
            # Draw wrapped rules
            curr_y = 160
            margin_left = 100
            wrap_width = SCREEN_WIDTH - 200
            for line in rules_list:
                curr_y = draw_wrapped_text(screen, line, margin_left, curr_y, wrap_width, 32)
                curr_y += 12 # Gap between rules

            # Back Button with Hover
            b_color = (150, 50, 50) if back_btn.collidepoint(mouse_pos) else (200, 50, 50)
            pygame.draw.rect(screen, b_color, back_btn, border_radius=8)
            screen.blit(font.render("BACK TO MENU", True, (255, 255, 255)), (back_btn.x + 15, back_btn.y + 12))

        elif state == "PLAYING":
            # Rack area
            pygame.draw.rect(screen, (20, 80, 20), (0, BOARD_BOUNDARY, SCREEN_WIDTH, 350))
            
            # Board/Rack separator shadow
            pygame.draw.line(screen, (10, 40, 10), (0, BOARD_BOUNDARY), (SCREEN_WIDTH, BOARD_BOUNDARY), 3)

            # Tiles
            for g in ghost_tiles: g.draw(screen, font, alpha=80)
            for t in tiles_in_play:
                if t.owner == 0 or t.owner == current_player: t.draw(screen, font)

            # Game Buttons with Hover
            for k, r in game_btns.items():
                g_color = (120, 120, 120) if r.collidepoint(mouse_pos) else (80, 80, 80)
                pygame.draw.rect(screen, g_color, r, border_radius=8)
                screen.blit(font.render(k.upper(), True, (255, 255, 255)), (r.x+25, r.y+10))
            
            screen.blit(font.render(f"Pool: {len(pool)}", True, (255, 255, 255)), (SCREEN_WIDTH - 230, 95))
            screen.blit(font.render(status_msg, True, (255, 255, 0)), (20, 20))

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__": main()