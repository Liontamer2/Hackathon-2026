import pygame
import random
import os

if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"

# --- Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 850 # Increased screen size
TILE_WIDTH, TILE_HEIGHT = 50, 70
GRID_X, GRID_Y = 55, 75
BOARD_BOUNDARY = 550 # More space for the board
RACK_START_Y = 580    # Rack starts here
COLORS = [(200, 0, 0), (0, 0, 200), (200, 150, 0), (20, 20, 20)] 
BG_COLOR = (34, 139, 34)

class Tile:
    def __init__(self, number, color_val, x, y):
        self.number = number
        self.color_val = color_val
        self.rect = pygame.Rect(x, y, TILE_WIDTH, TILE_HEIGHT)
        self.dragging = False

    def snap(self):
        self.rect.x = round(self.rect.x / GRID_X) * GRID_X
        self.rect.y = round(self.rect.y / GRID_Y) * GRID_Y
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - TILE_WIDTH))
        self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - TILE_HEIGHT))

    def draw(self, screen, font):
        color = (255, 255, 255) if not self.dragging else (200, 200, 200)
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2, border_radius=5)
        text = font.render(str(self.number), True, self.color_val)
        screen.blit(text, text.get_rect(center=self.rect.center))

def is_valid_group(group):
    if len(group) < 3: return False
    group.sort(key=lambda t: t.number)
    # Check SET (Same number, different colors)
    if all(t.number == group[0].number for t in group):
        colors = [t.color_val for t in group]
        return len(colors) == len(set(colors))
    # Check RUN (Same color, consecutive)
    if all(t.color_val == group[0].color_val for t in group):
        return all(group[i+1].number == group[i].number + 1 for i in range(len(group)-1))
    return False

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 22, bold=True)

    # Buttons
    draw_btn = pygame.Rect(1050, 600, 120, 40)
    check_btn = pygame.Rect(1050, 650, 120, 40)
    sort_btn = pygame.Rect(1050, 700, 120, 40)
    
    tiles = []
    has_made_initial_move = False
    status_msg = "First move must be 30+ points!"
    selected_tile = None

    def add_tile():
        num = random.randint(1, 13)
        col = random.choice(COLORS)
        # Position in rack (Two rows available)
        idx = len([t for t in tiles if t.rect.y >= RACK_START_Y])
        row = idx // 15
        col_idx = idx % 15
        t = Tile(num, col, 50 + col_idx * GRID_X, RACK_START_Y + row * GRID_Y)
        t.snap()
        tiles.append(t)

    for _ in range(14): add_tile()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if sort_btn.collidepoint(event.pos):
                    # Sort tiles currently in the rack
                    rack_tiles = [t for t in tiles if t.rect.y >= RACK_START_Y]
                    rack_tiles.sort(key=lambda x: (x.color_val, x.number))
                    for i, t in enumerate(rack_tiles):
                        t.rect.x = 50 + (i % 15) * GRID_X
                        t.rect.y = RACK_START_Y + (i // 15) * GRID_Y
                        t.snap()
                
                if draw_btn.collidepoint(event.pos): add_tile()

                if check_btn.collidepoint(event.pos):
                    board_tiles = [t for t in tiles if t.rect.y < BOARD_BOUNDARY]
                    total_points = sum(t.number for t in board_tiles)
                    
                    if not is_valid_group(board_tiles):
                        status_msg = "Invalid Set/Run!"
                    elif not has_made_initial_move and total_points < 30:
                        status_msg = f"Only {total_points} pts. Need 30!"
                    else:
                        status_msg = "Move Accepted!"
                        has_made_initial_move = True

                for t in reversed(tiles):
                    if t.rect.collidepoint(event.pos):
                        selected_tile = t
                        t.dragging = True
                        offset_x, offset_y = t.rect.x - event.pos[0], t.rect.y - event.pos[1]
                        tiles.remove(t); tiles.append(t)
                        break

            if event.type == pygame.MOUSEBUTTONUP and selected_tile:
                selected_tile.dragging = False
                selected_tile.snap()
                selected_tile = None

            if event.type == pygame.MOUSEMOTION and selected_tile:
                selected_tile.rect.x = pygame.mouse.get_pos()[0] + offset_x
                selected_tile.rect.y = pygame.mouse.get_pos()[1] + offset_y

        # Draw
        screen.fill(BG_COLOR)
        pygame.draw.rect(screen, (20, 80, 20), (0, BOARD_BOUNDARY, SCREEN_WIDTH, 300)) # Larger Rack
        
        for btn, txt, color in [(draw_btn, "DRAW", (100,100,255)), (check_btn, "CHECK", (255,100,100)), (sort_btn, "SORT", (150,150,150))]:
            pygame.draw.rect(screen, color, btn, border_radius=5)
            screen.blit(font.render(txt, True, (255,255,255)), (btn.x+20, btn.y+8))

        screen.blit(font.render(status_msg, True, (255,255,0)), (20, 20))
        for t in tiles: t.draw(screen, font)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__": main()