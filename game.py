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
SAFE_WIDTH = SCREEN_WIDTH - 180 # Margin to protect UI buttons
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
        # Support for transparency (for Ghost system)
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
    big_font = pygame.font.SysFont("Arial", 40, bold=True)

    btns = {
        "draw": pygame.Rect(1030, 540, 140, 45),
        "sort": pygame.Rect(1030, 600, 140, 45),
        "reset": pygame.Rect(1030, 660, 140, 45),
        "pass": pygame.Rect(1030, 720, 140, 45)
    }
    
    pool = create_pool()
    tiles_in_play = []
    ghost_tiles = []
    current_player = 1
    player_initials = {1: False, 2: False}
    status_msg = "P1: Lay 30 pts or Draw"
    selected_tile = None
    game_over = False

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
        ghost_tiles = [Tile(t.number, t.color_val, t.rect.x, t.rect.y, 0) 
                       for t in tiles_in_play if t.owner == 0]

    def reset_logic():
        nonlocal tiles_in_play
        new_list = [t for t in tiles_in_play if t.owner != 0]
        for t in tiles_in_play:
            if t.owner == 0:
                match = any(g.number == t.number and g.color_val == t.color_val and 
                            g.rect.topleft == t.rect.topleft for g in ghost_tiles)
                if not match:
                    t.owner = current_player
                    new_list.append(t)
        for g in ghost_tiles:
            still_there = any(t.number == g.number and t.color_val == g.color_val and 
                              t.rect.topleft == g.rect.topleft and t.owner == 0 for t in new_list)
            if not still_there:
                new_list.append(Tile(g.number, g.color_val, g.rect.x, g.rect.y, 0))
        tiles_in_play = new_list
        sort_hand(current_player)

    # Setup 14 Initial Tiles
    for p in [1, 2]:
        for _ in range(14):
            n, c = pool.pop(); tiles_in_play.append(Tile(n, c, 0, 0, p))
        sort_hand(p)
    update_ghosts()

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if not game_over:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if btns["sort"].collidepoint(event.pos): sort_hand(current_player)
                    if btns["reset"].collidepoint(event.pos): reset_logic()
                    if btns["draw"].collidepoint(event.pos) and pool:
                        reset_logic()
                        n, c = pool.pop()
                        tiles_in_play.append(Tile(n, c, 50, RACK_START_Y, current_player))
                        current_player = 2 if current_player == 1 else 1
                        sort_hand(current_player); update_ghosts()
                    if btns["pass"].collidepoint(event.pos):
                        board_tiles = [t for t in tiles_in_play if t.owner == 0]
                        pts = sum(t.number for t in board_tiles)
                        # Simplified 30pt logic: checks total tiles on board vs snapshot pts
                        if not player_initials[current_player] and pts < 30 and pts > 0:
                            status_msg = f"Need 30 pts! (Current: {pts})"
                        else:
                            if pts >= 30: player_initials[current_player] = True
                            update_ghosts()
                            current_player = 2 if current_player == 1 else 1
                            status_msg = f"Player {current_player}'s Turn"

                    for t in reversed(tiles_in_play):
                        if t.rect.collidepoint(event.pos) and (t.owner == current_player or t.owner == 0):
                            selected_tile = t; t.dragging = True
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
        pygame.draw.rect(screen, (20, 80, 20), (0, BOARD_BOUNDARY, SCREEN_WIDTH, 350)) # Rack
        
        # Top Right Indicator
        turn_bg = pygame.Rect(SCREEN_WIDTH - 250, 20, 230, 65)
        pygame.draw.rect(screen, (0, 0, 0, 100), turn_bg, border_radius=12)
        p_col = (255, 100, 100) if current_player == 1 else (100, 100, 255)
        t_surf = big_font.render(f"P{current_player} TURN", True, p_col)
        screen.blit(t_surf, t_surf.get_rect(center=turn_bg.center))

        # UI
        for k, r in btns.items():
            pygame.draw.rect(screen, (80, 80, 80), r, border_radius=8)
            screen.blit(font.render(k.upper(), True, (255, 255, 255)), (r.x+25, r.y+10))
        screen.blit(font.render(f"Pool: {len(pool)}", True, (255, 255, 255)), (SCREEN_WIDTH - 230, 95))
        screen.blit(font.render(status_msg, True, (255, 255, 0)), (20, 20))

        for g in ghost_tiles: g.draw(screen, font, alpha=80)
        for t in tiles_in_play:
            if t.owner == 0 or t.owner == current_player: t.draw(screen, font)

        # Win Check
        p1_c = len([t for t in tiles_in_play if t.owner == 1])
        p2_c = len([t for t in tiles_in_play if t.owner == 2])
        if (p1_c == 0 or p2_c == 0) and not game_over:
            game_over = True
            winner = 1 if p1_c == 0 else 2
            penalty = sum(t.number for t in tiles_in_play if t.owner != 0 and t.owner != winner)
            print(f"PLAYER {winner} WINS! Opponent Penalty: {penalty}")

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__": main()