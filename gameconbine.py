import pygame
import random
import os

# --- Environment Setup ---
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
        self.owner = owner  # 0: Board, 1: P1, 2: P2

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


def validate_group(group):
    """Validates if a group of tiles forms a legal Set or Run."""
    if len(group) < 3:
        return False

    # Set Check: Same number, different colors
    if all(t.number == group[0].number for t in group):
        colors = [t.color_val for t in group]
        return len(colors) == len(set(colors))

    # Run Check: Same color, consecutive numbers
    if all(t.color_val == group[0].color_val for t in group):
        nums = sorted([t.number for t in group])
        return all(nums[i] + 1 == nums[i + 1] for i in range(len(nums) - 1))

    return False


def get_all_board_groups(tiles):
    """Scans the board row by row and identifies clusters separated by gaps."""
    board_tiles = [t for t in tiles if t.owner == 0]
    if not board_tiles:
        return []

    groups = []
    rows = {}
    for t in board_tiles:
        rows.setdefault(t.rect.y, []).append(t)

    for y_val in rows:
        row_tiles = sorted(rows[y_val], key=lambda t: t.rect.x)
        if not row_tiles:
            continue

        current_group = [row_tiles[0]]
        for i in range(1, len(row_tiles)):
            if row_tiles[i].rect.x == row_tiles[i - 1].rect.x + GRID_X:
                current_group.append(row_tiles[i])
            else:
                groups.append(current_group)
                current_group = [row_tiles[i]]
        groups.append(current_group)
    return groups


def draw_wrapped_text(surface, text, x, y, max_width, line_height, font):
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


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2-Player Rummikub")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 22, bold=True)
    big_font = pygame.font.SysFont("Arial", 40, bold=True)
    title_font = pygame.font.SysFont("Arial", 50, bold=True)

    # --- Menu / Rules / Pause states ---
    state = "MENU"  # MENU, RULES, PLAYING, PAUSED
    menu_btns = {
        "play": pygame.Rect(SCREEN_WIDTH // 2 - 100, 350, 200, 60),
        "rules": pygame.Rect(SCREEN_WIDTH // 2 - 100, 430, 200, 60),
        "quit": pygame.Rect(SCREEN_WIDTH // 2 - 100, 510, 200, 60),
    }
    back_btn = pygame.Rect(50, 40, 220, 50)

    # Pause menu buttons (visible when state == "PAUSED")
    pause_btns = {
        "resume": pygame.Rect(SCREEN_WIDTH // 2 - 120, 280, 240, 60),
        "restart": pygame.Rect(SCREEN_WIDTH // 2 - 120, 360, 240, 60),
        "rules": pygame.Rect(SCREEN_WIDTH // 2 - 120, 440, 240, 60),
        "home": pygame.Rect(SCREEN_WIDTH // 2 - 120, 520, 240, 60),
    }

    # --- Game variables ---
    btns = {k: pygame.Rect(1030, 540 + i * 60, 140, 45)
            for i, k in enumerate(["draw", "sort", "reset", "pass"])}
    pool = [(n, c) for c in COLORS for n in range(1, 14) for _ in range(2)]
    random.shuffle(pool)

    tiles_in_play = []
    ghost_data = []      # last legal board snapshot (only board tiles)
    current_player = 1
    player_initials = {1: False, 2: False}
    status_msg = "P1: Lay 30 pts or Draw"
    selected_tile = None
    off_x = 0
    off_y = 0
    game_started = False

    # sort-mode popup controls
    sort_mode_select = False
    sort_btn_number = pygame.Rect(400, 300, 160, 60)
    sort_btn_color = pygame.Rect(640, 300, 160, 60)

    # ---- helper functions ----

    def sort_hand(p_id, mode="number"):
        p_tiles = [t for t in tiles_in_play if t.owner == p_id]
        if mode == "number":
            p_tiles.sort(key=lambda x: (x.number, x.color_val))
        else:
            p_tiles.sort(key=lambda x: (x.color_val, x.number))
        for i, t in enumerate(p_tiles):
            t.rect.x, t.rect.y = 50 + ((i % 18) * GRID_X), RACK_START_Y + ((i // 18) * GRID_Y)
            t.snap()

    def reset_pool_and_hands():
        nonlocal pool, tiles_in_play, ghost_data, current_player, player_initials, status_msg
        pool = [(n, c) for c in COLORS for n in range(1, 14) for _ in range(2)]
        random.shuffle(pool)
        tiles_in_play.clear()
        ghost_data = []
        current_player = 1
        player_initials = {1: False, 2: False}
        status_msg = "P1: Lay 30 pts or Draw"

    def deal_initial_hands():
        """Deal 14 tiles to each player and reset board snapshot."""
        nonlocal ghost_data
        tiles_in_play.clear()
        for p in [1, 2]:
            for _ in range(14):
                n, c = pool.pop()
                tiles_in_play.append(Tile(n, c, 0, 0, p))
            sort_hand(p, "number")
        ghost_data = []  # empty board at the very start

    def snapshot_board():
        """Save current board layout (only board tiles)."""
        return [(t.number, t.color_val, t.rect.x, t.rect.y)
                for t in tiles_in_play if t.owner == 0]

    def restore_board_from_snapshot(snapshot):
        """
        Restore board to previous legal snapshot and return all
        non-snapshot board tiles to current player's hand.
        """
        for t in tiles_in_play:
            if t.owner == 0:
                t.owner = current_player

        for num, col, x, y in snapshot:
            t = next(
                (tt for tt in tiles_in_play
                 if tt.owner == current_player and tt.number == num and tt.color_val == col),
                None
            )
            if t:
                t.owner = 0
                t.rect.x = x
                t.rect.y = y

        sort_hand(current_player, "number")

    def find_nearest_empty_grid(tile):
        """Find nearest empty snapped grid cell and return (x, y)."""
        base_x = tile.rect.x
        base_y = tile.rect.y

        occupied = set()
        for t in tiles_in_play:
            if t is tile:
                continue
            occupied.add((t.rect.x, t.rect.y))

        if (base_x, base_y) not in occupied:
            return base_x, base_y

        max_radius = 20
        best_pos = None
        best_dist_sq = None

        for r in range(1, max_radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    x = base_x + dx * GRID_X
                    y = base_y + dy * GRID_Y

                    if x < 0 or x > SCREEN_WIDTH - TILE_WIDTH:
                        continue
                    if y < 0 or y > SCREEN_HEIGHT - TILE_HEIGHT:
                        continue

                    if (x, y) in occupied:
                        continue

                    dist_sq = dx * dx + dy * dy
                    if best_pos is None or dist_sq < best_dist_sq:
                        best_pos = (x, y)
                        best_dist_sq = dist_sq

            if best_pos is not None:
                break

        if best_pos is None:
            return base_x, base_y
        return best_pos

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # global pause toggle (Esc) when playing
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state == "PLAYING":
                    state = "PAUSED"
                elif state == "PAUSED":
                    state = "PLAYING"

            # --- MENU ---
            if state == "MENU":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if menu_btns["play"].collidepoint(event.pos):
                        reset_pool_and_hands()
                        deal_initial_hands()
                        game_started = True
                        state = "PLAYING"
                    elif menu_btns["rules"].collidepoint(event.pos):
                        state = "RULES"
                    elif menu_btns["quit"].collidepoint(event.pos):
                        running = False

            # --- RULES ---
            elif state == "RULES":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_btn.collidepoint(event.pos):
                        state = "MENU"

            # --- PAUSED ---
            elif state == "PAUSED":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if pause_btns["resume"].collidepoint(event.pos):
                        state = "PLAYING"
                    elif pause_btns["restart"].collidepoint(event.pos):
                        reset_pool_and_hands()
                        deal_initial_hands()
                        state = "PLAYING"
                    elif pause_btns["rules"].collidepoint(event.pos):
                        state = "RULES"
                    elif pause_btns["home"].collidepoint(event.pos):
                        state = "MENU"

            # --- PLAYING ---
            elif state == "PLAYING":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # sort mode popup
                    if sort_mode_select:
                        if sort_btn_number.collidepoint(event.pos):
                            sort_hand(current_player, "number")
                            sort_mode_select = False
                        elif sort_btn_color.collidepoint(event.pos):
                            sort_hand(current_player, "color")
                            sort_mode_select = False
                        else:
                            sort_mode_select = False
                    else:
                        # normal buttons
                        if btns["sort"].collidepoint(event.pos):
                            sort_mode_select = True

                        if btns["reset"].collidepoint(event.pos):
                            restore_board_from_snapshot(ghost_data)

                        if btns["draw"].collidepoint(event.pos) and pool:
                            restore_board_from_snapshot(ghost_data)
                            n, c = pool.pop()
                            tiles_in_play.append(Tile(n, c, 50, RACK_START_Y, current_player))
                            current_player = 3 - current_player
                            sort_hand(current_player, "number")
                            ghost_data = snapshot_board()

                        if btns["pass"].collidepoint(event.pos):
                            all_groups = get_all_board_groups(tiles_in_play)
                            is_board_valid = all(validate_group(g) for g in all_groups)

                            board_tiles_now = [t for t in tiles_in_play if t.owner == 0]
                            prev_board_positions = {(n, c, x, y) for (n, c, x, y) in ghost_data}

                            new_tiles = []
                            for t in board_tiles_now:
                                key = (t.number, t.color_val, t.rect.x, t.rect.y)
                                if key not in prev_board_positions:
                                    new_tiles.append(t)

                            new_pts = sum(t.number for t in new_tiles)

                            if not is_board_valid:
                                status_msg = "Invalid Board! Rearrangement failed."
                                restore_board_from_snapshot(ghost_data)
                            elif not player_initials[current_player] and new_pts < 30:
                                status_msg = f"First move needs 30 pts! ({new_pts}/30)"
                                restore_board_from_snapshot(ghost_data)
                            else:
                                if not player_initials[current_player] and new_pts >= 30:
                                    player_initials[current_player] = True

                                ghost_data = snapshot_board()
                                current_player = 3 - current_player
                                status_msg = f"P{current_player}'s Turn"

                        # tile pick up
                        for t in reversed(tiles_in_play):
                            if t.rect.collidepoint(event.pos) and t.owner in [0, current_player]:
                                selected_tile = t
                                t.dragging = True
                                off_x = t.rect.x - event.pos[0]
                                off_y = t.rect.y - event.pos[1]
                                tiles_in_play.remove(t)
                                tiles_in_play.append(t)
                                break

                # drop tile with nearest empty grid
                if event.type == pygame.MOUSEBUTTONUP and selected_tile:
                    selected_tile.dragging = False
                    selected_tile.snap()
                    selected_tile.owner = 0 if selected_tile.rect.y < BOARD_BOUNDARY else current_player

                    new_x, new_y = find_nearest_empty_grid(selected_tile)
                    selected_tile.rect.x = new_x
                    selected_tile.rect.y = new_y
                    selected_tile.owner = 0 if selected_tile.rect.y < BOARD_BOUNDARY else current_player

                    selected_tile = None

                if event.type == pygame.MOUSEMOTION and selected_tile:
                    selected_tile.rect.topleft = (
                        pygame.mouse.get_pos()[0] + off_x,
                        pygame.mouse.get_pos()[1] + off_y,
                    )

        # --- RENDERING ---
        screen.fill(BG_COLOR)

        if state == "MENU":
            title = title_font.render("RUMMIKUB", True, (255, 255, 255))
            screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 200)))
            for key, rect in menu_btns.items():
                color = (100, 100, 100) if rect.collidepoint(mouse_pos) else (60, 60, 60)
                pygame.draw.rect(screen, color, rect, border_radius=10)
                txt = font.render(key.upper(), True, (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=rect.center))

        elif state == "RULES":
            header = title_font.render("GAME RULES", True, (255, 255, 0))
            screen.blit(header, header.get_rect(center=(SCREEN_WIDTH // 2, 80)))
            rules_list = [
                "1. Each player starts with 14 tiles.",
                "2. Drag tiles to the board to play them.",
                "3. First play must be worth 30+ points.",
                "4. All plays must be sets or runs.",
                "5. Sets are 3+ tiles of same number, but different colors. No duplicate tiles are allowed.",
                "6. Runs are 3+ tiles of consecutive numbers with the same color.",
                "7. You are allowed to manipulate all tiles on the board as long as the end result is legal.",
                "8. A legal board means every tile is in a set or run with no mistakes.",
            ]
            curr_y = 160
            margin_left = 100
            wrap_width = SCREEN_WIDTH - 200
            for line in rules_list:
                curr_y = draw_wrapped_text(screen, line, margin_left, curr_y, wrap_width, 32, font)
                curr_y += 12
            b_color = (150, 50, 50) if back_btn.collidepoint(mouse_pos) else (200, 50, 50)
            pygame.draw.rect(screen, b_color, back_btn, border_radius=8)
            screen.blit(font.render("BACK TO MENU", True, (255, 255, 255)),
                        (back_btn.x + 15, back_btn.y + 12))

        elif state == "PLAYING":
            pygame.draw.rect(screen, (20, 80, 20), (0, BOARD_BOUNDARY, SCREEN_WIDTH, 350))

            # ghost board tiles (last legal snapshot)
            for n, c, x, y in ghost_data:
                Tile(n, c, x, y, 0).draw(screen, font, 60)

            # player turn indicator and initial-30 status
            p_col = (255, 100, 100) if current_player == 1 else (100, 100, 255)
            indicator_rect = pygame.Rect(SCREEN_WIDTH - 240, 20, 220, 95)
            pygame.draw.rect(screen, (0, 0, 0), indicator_rect, border_radius=10)
            screen.blit(big_font.render(f"P{current_player} TURN", True, p_col),
                        (SCREEN_WIDTH - 230, 30))

            for i in [1, 2]:
                label = "30+ OK" if player_initials[i] else "Need 30"
                color = (0, 255, 0) if player_initials[i] else (200, 200, 200)
                screen.blit(font.render(f"P{i}: {label}", True, color),
                            (SCREEN_WIDTH - 230, 75 + (i - 1) * 20))

            # buttons
            for k, r in btns.items():
                pygame.draw.rect(screen, (80, 80, 80), r, border_radius=8)
                screen.blit(font.render(k.upper(), True, (255, 255, 255)),
                            (r.x + 25, r.y + 10))

            screen.blit(font.render(status_msg, True, (255, 255, 0)), (20, 20))

            # tiles (current view)
            for t in tiles_in_play:
                if t.owner in [0, current_player]:
                    t.draw(screen, font)

            # sort mode popup overlay
            if sort_mode_select:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                screen.blit(overlay, (0, 0))

                prompt = big_font.render("SORT TILES BY:", True, (255, 255, 255))
                screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, 230)))

                pygame.draw.rect(screen, (80, 80, 80), sort_btn_number, border_radius=10)
                pygame.draw.rect(screen, (80, 80, 80), sort_btn_color, border_radius=10)
                txt_num = font.render("NUMBER", True, (255, 255, 255))
                txt_col = font.render("COLOR", True, (255, 255, 255))
                screen.blit(txt_num, txt_num.get_rect(center=sort_btn_number.center))
                screen.blit(txt_col, txt_col.get_rect(center=sort_btn_color.center))

        elif state == "PAUSED":
            # dim the current screen
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            title = title_font.render("PAUSED", True, (255, 255, 255))
            screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 200)))

            for key, rect in pause_btns.items():
                color = (100, 100, 100) if rect.collidepoint(mouse_pos) else (70, 70, 70)
                pygame.draw.rect(screen, color, rect, border_radius=10)
                label = key.upper()
                if key == "home":
                    label = "HOME SCREEN"
                elif key == "rules":
                    label = "RULES"
                elif key == "resume":
                    label = "RESUME"
                elif key == "restart":
                    label = "RESTART"
                txt = font.render(label, True, (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=rect.center))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()


