import pygame
import random
import os

# --- Configuration Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 850
TILE_WIDTH, TILE_HEIGHT = 50, 70
GRID_X, GRID_Y = 55, 75
BOARD_BOUNDARY = 500
RACK_START_Y = 600
COLORS = [(220, 30, 30), (30, 30, 220), (220, 180, 0), (20, 20, 20)]
BG_COLOR = (34, 139, 34)

class Tile:
    def __init__(self, number, color_val, x, y, owner):
        self.number = number
        self.color_val = color_val
        self.rect = pygame.Rect(x, y, TILE_WIDTH, TILE_HEIGHT)
        self.dragging = False
        self.owner = owner  # 0: Board, 1: P1, 2: Bot

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
        
        # --- JOKER RENDERING ---
        if self.number == 0:
            text = font.render("J", True, (0, 0, 0, alpha))
        else:
            text_col = list(self.color_val) + [alpha]
            text = font.render(str(self.number), True, text_col)
            
        text_rect = text.get_rect(center=(TILE_WIDTH // 2, TILE_HEIGHT // 2))
        surf.blit(text, text_rect)
        screen.blit(surf, self.rect)

def find_nearest_empty_spot(target_tile, all_tiles, start_x=None, start_y=None):
    if start_x is not None: target_tile.rect.x = start_x
    if start_y is not None: target_tile.rect.y = start_y
    target_tile.snap()
    occupied = {(t.rect.x, t.rect.y) for t in all_tiles if t != target_tile and t.owner == 0}
    if (target_tile.rect.x, target_tile.rect.y) not in occupied and target_tile.rect.y < BOARD_BOUNDARY:
        return target_tile.rect.x, target_tile.rect.y
    sx, sy = target_tile.rect.x, target_tile.rect.y
    for r in range(1, 40):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if abs(dx) != r and abs(dy) != r: continue
                nx, ny = sx + (dx * GRID_X), sy + (dy * GRID_Y)
                if 0 <= nx <= SCREEN_WIDTH - TILE_WIDTH and 0 <= ny <= BOARD_BOUNDARY - TILE_HEIGHT:
                    if (nx, ny) not in occupied: return nx, ny
    return sx, sy

def validate_group(group):
    """Seamlessly handles Jokers (number 0) acting as wildcards."""
    if len(group) < 3: return False
    
    jokers = [t for t in group if t.number == 0]
    normals = [t for t in group if t.number != 0]

    if not normals: return True # Rare case of all jokers

    # --- SET CHECK ---
    is_set = True
    if len(group) > 4: 
        is_set = False
    else:
        first_num = normals[0].number
        if any(t.number != first_num for t in normals): is_set = False
        colors = [t.color_val for t in normals]
        if len(colors) != len(set(colors)): is_set = False
    if is_set: return True

    # --- RUN CHECK ---
    is_run = True
    if len(group) > 13: 
        is_run = False
    else:
        first_color = normals[0].color_val
        if any(t.color_val != first_color for t in normals): 
            is_run = False
        else:
            nums = sorted([t.number for t in normals])
            if len(nums) != len(set(nums)): 
                is_run = False # Duplicates break a run
            else:
                span = nums[-1] - nums[0] + 1
                missing_internals = span - len(nums)
                if missing_internals > len(jokers): 
                    is_run = False
    if is_run: return True

    return False

def get_all_board_groups(tiles):
    board_tiles = [t for t in tiles if t.owner == 0]
    groups, rows = [], {}
    for t in board_tiles: rows.setdefault(t.rect.y, []).append(t)
    for y in sorted(rows.keys()):
        row_tiles = sorted(rows[y], key=lambda t: t.rect.x)
        if not row_tiles: continue
        cur = [row_tiles[0]]
        for i in range(1, len(row_tiles)):
            if row_tiles[i].rect.x == row_tiles[i-1].rect.x + GRID_X: cur.append(row_tiles[i])
            else: groups.append(cur); cur = [row_tiles[i]]
        groups.append(cur)
    return groups

def draw_wrapped_text(surface, text, x, y, max_width, line_height, font):
    words = text.split(' ')
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] < max_width: current_line = test_line
        else:
            surface.blit(font.render(current_line, True, (255, 255, 255)), (x, y))
            y += line_height; current_line = word + " "
    surface.blit(font.render(current_line, True, (255, 255, 255)), (x, y))
    return y + line_height

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 22, bold=True)
    title_font = pygame.font.SysFont("Arial", 60, bold=True)

    state, previous_state = "MENU", "MENU"
    current_player, player_initials = 1, {1: False, 2: False}
    
    menu_btns = {"play": pygame.Rect(500, 350, 200, 60), "rules": pygame.Rect(500, 430, 200, 60), "quit": pygame.Rect(500, 510, 200, 60)}
    pause_btns = {"resume": pygame.Rect(480, 280, 240, 60), "restart": pygame.Rect(480, 360, 240, 60), "rules": pygame.Rect(480, 440, 240, 60), "home": pygame.Rect(480, 520, 240, 60)}
    btns = {k: pygame.Rect(1030, 540 + i * 60, 140, 45) for i, k in enumerate(["draw", "sort", "reset", "pass"])}
    back_btn_rect = pygame.Rect(50, 40, 220, 50)
    
    pool, tiles_in_play, ghost_data, turn_checkpoint = [], [], [], []
    ai_phase, ai_move_queue, ai_timer = "IDLE", [], 0
    selected_tile, status_msg = None, "P1 Turn"
    failed_attempts = []
    current_plan_sig = None

    def sort_hand(p_id):
        p_tiles = [t for t in tiles_in_play if t.owner == p_id]
        p_tiles.sort(key=lambda x: (COLORS.index(x.color_val) if x.color_val in COLORS else 99, x.number))
        for i, t in enumerate(p_tiles):
            t.rect.x, t.rect.y = 50 + ((i % 18) * GRID_X), RACK_START_Y + ((i // 18) * GRID_Y)
            t.snap()

    def reset_game():
        nonlocal pool, tiles_in_play, ghost_data, turn_checkpoint, current_player, player_initials, status_msg, failed_attempts, current_plan_sig
        pool = [(n, c) for c in COLORS for n in range(1, 14) for _ in range(2)]
        pool.extend([(0, (255, 255, 255)), (0, (255, 255, 255))]) # Jokers added
        random.shuffle(pool)
        
        tiles_in_play.clear()
        failed_attempts.clear()
        current_plan_sig = None
        for p in [1, 2]:
            for _ in range(14): n, c = pool.pop(); tiles_in_play.append(Tile(n, c, 0, 0, p))
            sort_hand(p)
        ghost_data, turn_checkpoint, current_player, player_initials = [], [], 1, {1: False, 2: False}
        status_msg = "P1 Turn"

    def restore_board(snapshot, p_id):
        for t in tiles_in_play:
            if t.owner == 0: t.owner = p_id
        for num, col, x, y in snapshot:
            t = next((tt for tt in tiles_in_play if tt.owner == p_id and tt.number == num and tt.color_val == col), None)
            if t: t.owner, t.rect.x, t.rect.y = 0, x, y
        sort_hand(p_id)

    def capture_snapshot(): return [(t.number, t.color_val, t.rect.x, t.rect.y) for t in tiles_in_play if t.owner == 0]

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        if state == "PLAYING" and current_player == 2:
            if ai_phase == "IDLE":
                ai_timer, ai_phase = pygame.time.get_ticks(), "THINKING"
                turn_checkpoint = capture_snapshot()
            
            elif ai_phase == "THINKING" and pygame.time.get_ticks() - ai_timer > 1000:
                available = [t for t in tiles_in_play if t.owner in [0, 2]]
                hand = [t for t in tiles_in_play if t.owner == 2]
                
                # --- BOT ALGORITHM TO FIND GROUPS (INCLUDES JOKERS) ---
                def find_groups(tile_pool):
                    found = []
                    temp_pool = list(tile_pool)
                    jokers = [t for t in temp_pool if t.number == 0]
                    for j in jokers: temp_pool.remove(j)

                    for color in COLORS:
                        c_tiles = sorted([t for t in temp_pool if t.color_val == color], key=lambda x: x.number)
                        run = []
                        for t in c_tiles:
                            if not run: run.append(t)
                            elif t.number == run[-1].number + 1: run.append(t)
                            elif t.number == run[-1].number + 2 and jokers:
                                run.append(jokers.pop(0)); run.append(t)
                            elif t.number != run[-1].number:
                                if len(run) == 2 and jokers: run.append(jokers.pop(0))
                                if len(run) >= 3:
                                    found.append(list(run))
                                    for rt in run: 
                                        if rt in temp_pool: temp_pool.remove(rt)
                                run = [t]
                        if len(run) == 2 and jokers: run.append(jokers.pop(0))
                        if len(run) >= 3:
                            found.append(list(run))
                            for rt in run: 
                                if rt in temp_pool: temp_pool.remove(rt)

                    for n in range(1, 14):
                        n_tiles = [t for t in temp_pool if t.number == n]
                        unique = list({t.color_val: t for t in n_tiles}.values())
                        if len(unique) == 2 and jokers: unique.append(jokers.pop(0))
                        if len(unique) >= 3:
                            found.append(unique)
                            for ut in unique: 
                                if ut in temp_pool: temp_pool.remove(ut)
                    return found

                # STRATEGY 1: Hand Only
                planned = find_groups(hand)
                hand_used = [t for g in planned for t in g if t.owner == 2]
                bot_pts = sum((30 if t.number == 0 else t.number) for t in hand_used)
                
                # STRATEGY 2: Hand + Board Manipulation (Only if Hand-Only fails or 30pts already met)
                if (not player_initials[2] and bot_pts < 30) or not planned:
                    planned_manip = find_groups(available)
                    hand_used_manip = [t for g in planned_manip for t in g if t.owner == 2]
                    pts_manip = sum((30 if t.number == 0 else t.number) for t in hand_used_manip)
                    
                    if player_initials[2] or pts_manip >= 30:
                        planned = planned_manip
                        hand_used = hand_used_manip
                        bot_pts = pts_manip

                # CHECK AGAINST FAILED MEMORY
                planned_sig = tuple(sorted([(t.number, t.color_val) for g in planned for t in g]))
                if planned_sig in failed_attempts:
                    planned = [] # Skip this plan if it previously crashed the board
                else:
                    current_plan_sig = planned_sig

                if not player_initials[2] and bot_pts < 30: ai_move_queue = []
                else: ai_move_queue = planned
                
                ai_phase, ai_timer = "ANIMATING", pygame.time.get_ticks()

            elif ai_phase == "ANIMATING" and pygame.time.get_ticks() - ai_timer > 600:
                if ai_move_queue:
                    group = ai_move_queue.pop(0)
                    sx, sy = random.randrange(GRID_X, 700, GRID_X), random.randrange(GRID_Y, 300, GRID_Y)
                    for i, t in enumerate(group):
                        t.owner, t.rect.x, t.rect.y = 0, sx + (i*GRID_X), sy
                        t.rect.x, t.rect.y = find_nearest_empty_spot(t, tiles_in_play)
                    if all(validate_group(g) for g in get_all_board_groups(tiles_in_play)): turn_checkpoint = capture_snapshot()
                    ai_timer = pygame.time.get_ticks()
                else:
                    board_now = capture_snapshot()
                    added_from_hand = [t for t in tiles_in_play if t.owner == 0 and (t.number, t.color_val, t.rect.x, t.rect.y) not in {(n,c,x,y) for n,c,x,y in ghost_data}]
                    
                    # FINAL TURN VALIDATION
                    if len(added_from_hand) > 0 and all(validate_group(g) for g in get_all_board_groups(tiles_in_play)):
                        player_initials[2] = True; ghost_data = board_now
                        status_msg = "Bot Turn Over"
                        failed_attempts.clear() # Reset memory on success
                    else:
                        if current_plan_sig is not None and current_plan_sig not in failed_attempts:
                            failed_attempts.append(current_plan_sig)

                        restore_board(ghost_data, 2)
                        if pool:
                            n, c = pool.pop()
                            tiles_in_play.append(Tile(n, c, 0, 0, 2))
                            sort_hand(2)
                        status_msg = "Bot Draw (No new tiles/Invalid)"
                    current_player, ai_phase = 1, "IDLE"

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and state == "PLAYING": state = "PAUSED"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if state == "MENU":
                    if menu_btns["play"].collidepoint(event.pos): reset_game(); state = "PLAYING"
                    elif menu_btns["rules"].collidepoint(event.pos): previous_state, state = "MENU", "RULES"
                    elif menu_btns["quit"].collidepoint(event.pos): running = False
                elif state == "PAUSED":
                    if pause_btns["resume"].collidepoint(event.pos): state = "PLAYING"
                    elif pause_btns["restart"].collidepoint(event.pos): reset_game(); state = "PLAYING"
                    elif pause_btns["rules"].collidepoint(event.pos): previous_state, state = "PAUSED", "RULES"
                    elif pause_btns["home"].collidepoint(event.pos): state = "MENU"
                elif state == "RULES" and back_btn_rect.collidepoint(event.pos): state = previous_state
                elif state == "PLAYING" and current_player == 1:
                    if btns["sort"].collidepoint(event.pos): sort_hand(1)
                    if btns["reset"].collidepoint(event.pos): restore_board(ghost_data, 1)
                    if btns["draw"].collidepoint(event.pos) and pool:
                        restore_board(ghost_data, 1); n, c = pool.pop(); tiles_in_play.append(Tile(n, c, 0, 0, 1))
                        sort_hand(1); ghost_data = capture_snapshot(); current_player = 2
                    if btns["pass"].collidepoint(event.pos):
                        groups = get_all_board_groups(tiles_in_play)
                        new_t = [t for t in tiles_in_play if t.owner == 0 and (t.number, t.color_val, t.rect.x, t.rect.y) not in {(n,c,x,y) for n,c,x,y in ghost_data}]
                        
                        p1_pts = sum((30 if t.number == 0 else t.number) for t in new_t)
                        
                        if len(new_t) > 0 and all(validate_group(g) for g in groups) and (player_initials[1] or p1_pts >= 30):
                            player_initials[1] = True; ghost_data = capture_snapshot(); current_player = 2
                        else: 
                            restore_board(ghost_data, 1)
                            if pool:
                                n, c = pool.pop(); tiles_in_play.append(Tile(n, c, 0, 0, 1)); sort_hand(1)
                            ghost_data = capture_snapshot(); current_player = 2
                    for t in reversed(tiles_in_play):
                        if t.rect.collidepoint(event.pos) and t.owner in [0, 1]:
                            selected_tile = t; t.dragging = True; off_x, off_y = t.rect.x - event.pos[0], t.rect.y - event.pos[1]
                            tiles_in_play.remove(t); tiles_in_play.append(t); break
            if event.type == pygame.MOUSEBUTTONUP and selected_tile:
                selected_tile.dragging = False; selected_tile.rect.x, selected_tile.rect.y = find_nearest_empty_spot(selected_tile, tiles_in_play)
                selected_tile.owner = 0 if selected_tile.rect.y < BOARD_BOUNDARY else 1
                selected_tile = None
            if event.type == pygame.MOUSEMOTION and selected_tile:
                selected_tile.rect.topleft = (mouse_pos[0] + off_x, mouse_pos[1] + off_y)

        screen.fill(BG_COLOR)
        if state == "MENU":
            title_text = title_font.render("RUMMIKUB", True, (255, 255, 255))
            screen.blit(title_text, title_text.get_rect(center=(SCREEN_WIDTH // 2, 200)))
            for k, r in menu_btns.items():
                pygame.draw.rect(screen, (100,100,100) if r.collidepoint(mouse_pos) else (60,60,60), r, border_radius=10)
                txt = font.render(k.upper(), True, (255,255,255)); screen.blit(txt, txt.get_rect(center=r.center))
        elif state == "RULES":
            header = title_font.render("GAME RULES", True, (255, 255, 0))
            screen.blit(header, header.get_rect(center=(SCREEN_WIDTH // 2, 80)))
            r_list = ["- The first play must total at least 30 points.", "- Sets: 3+ tiles of same number, different colors.", "- Runs: 3+ consecutive numbers of same color.", "- Jokers: Replace any tile. Worth 30 pts for initial drop.", "- A player will auto-draw if they fail to play NEW tiles legally.", "- Bot remembers failed moves to improve strategy."]
            cy = 160
            for line in r_list: cy = draw_wrapped_text(screen, line, 100, cy, 1000, 35, font); cy += 10
            pygame.draw.rect(screen, (200, 50, 50), back_btn_rect, border_radius=8); screen.blit(font.render("BACK", True, (255,255,255)), (130, 52))
        elif state in ["PLAYING", "PAUSED"]:
            pygame.draw.rect(screen, (20, 80, 20), (0, BOARD_BOUNDARY, SCREEN_WIDTH, 350))
            for n, c, x, y in ghost_data: Tile(n, c, x, y, 0).draw(screen, font, 60)
            
            p1_active = current_player == 1
            pygame.draw.circle(screen, (0, 0, 200) if p1_active else (40, 40, 40), (60, 60), 30)
            pygame.draw.circle(screen, (255, 255, 255), (60, 60), 30, 2)
            screen.blit(font.render("P1", True, (255, 255, 255)), (48, 48))
            
            bot_active = current_player == 2
            pygame.draw.rect(screen, (200, 0, 0) if bot_active else (40, 40, 40), (110, 30, 60, 60), border_radius=10)
            pygame.draw.rect(screen, (255, 255, 255), (110, 30, 60, 60), 2, border_radius=10)
            screen.blit(font.render("BOT", True, (255, 255, 255)), (120, 48))

            for k, r in btns.items():
                pygame.draw.rect(screen, (110,110,110) if r.collidepoint(mouse_pos) else (80,80,80), r, border_radius=8)
                screen.blit(font.render(k.upper(), True, (255,255,255)), (r.x + 25, r.y + 10))
            for t in tiles_in_play: 
                if t.owner in [0, 1]: t.draw(screen, font)
            if state == "PAUSED":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180)); screen.blit(overlay, (0,0))
                for k, r in pause_btns.items():
                    pygame.draw.rect(screen, (100,100,100) if r.collidepoint(mouse_pos) else (70,70,70), r, border_radius=10)
                    txt = font.render(k.upper() if k != "home" else "HOME SCREEN", True, (255,255,255)); screen.blit(txt, txt.get_rect(center=r.center))
        pygame.display.flip(); clock.tick(60)
    pygame.quit()

if __name__ == "__main__": main()