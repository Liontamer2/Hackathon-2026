# rummikub_ai.py
from itertools import combinations, permutations

# Colors are represented as simple ids; you can map your RGB tuples to small ints
# in the main game when calling these functions.

def is_valid_set(group):
    if len(group) < 3:
        return False
    nums = [t[0] for t in group]
    cols = [t[1] for t in group]
    if len(set(nums)) != 1:
        return False
    if len(set(cols)) != len(cols):
        return False
    return True


def is_valid_run(group):
    if len(group) < 3:
        return False
    nums = sorted(t[0] for t in group)
    cols = [t[1] for t in group]
    if len(set(cols)) != 1:
        return False
    return all(nums[i] + 1 == nums[i+1] for i in range(len(nums) - 1))


def all_valid_groups(groups):
    return all(is_valid_set(g) or is_valid_run(g) for g in groups)


def flatten_board(groups):
    flat = []
    for idx, g in enumerate(groups):
        for pos, tile in enumerate(g):
            flat.append((idx, pos, tile))
    return flat


def build_groups_from_assignment(flat_tiles, assignment):
    # assignment: list of (group_id, position) pairs parallel to flat_tiles
    grouped = {}
    for (_, _, tile), (gid, pos) in zip(flat_tiles, assignment):
        grouped.setdefault(gid, []).append((pos, tile))
    result = []
    for gid in sorted(grouped.keys()):
        tiles_with_pos = sorted(grouped[gid], key=lambda x: x[0])
        result.append([t for _, t in tiles_with_pos])
    return result


def generate_simple_insertions(board_groups, hand_tiles):
    """
    Very simplified: try to insert single hand tiles into existing groups
    or create new groups out of hand only. Returns a list of candidate boards
    and remaining hand sets.

    board_groups: list of list of (num, color_id)
    hand_tiles: list of (num, color_id)
    """
    candidates = []

    # 1) Try new sets/runs from hand alone (no board rearrange yet)
    hand_unique = list(set(hand_tiles))
    for r in range(3, min(7, len(hand_unique)) + 1):
        for combo in combinations(hand_unique, r):
            group = list(combo)
            if is_valid_set(group) or is_valid_run(group):
                new_board = board_groups + [group]
                remaining = list(hand_tiles)
                for t in group:
                    if t in remaining:
                        remaining.remove(t)
                candidates.append((new_board, remaining))

    # 2) Try inserting single tiles into existing groups without breaking them
    for idx, g in enumerate(board_groups):
        for tile in set(hand_tiles):
            # try inserting tile at all positions and see if group is still valid
            for pos in range(len(g) + 1):
                new_group = g[:pos] + [tile] + g[pos:]
                if is_valid_set(new_group) or is_valid_run(new_group):
                    new_board = [list(gr) for gr in board_groups]
                    new_board[idx] = new_group
                    remaining = list(hand_tiles)
                    if tile in remaining:
                        remaining.remove(tile)
                    candidates.append((new_board, remaining))

    return candidates


def choose_best_move(board_groups, hand_tiles, initial_done):
    """
    Entry point for bot.
    board_groups: list of list of (num, color_id)
    hand_tiles: list of (num, color_id)
    initial_done: bool for whether bot already satisfied 30+ requirement

    Returns:
      (new_board_groups, new_hand_tiles, points_played) or (None, hand_tiles, 0) if draw/pass.
    """
    cand_moves = generate_simple_insertions(board_groups, hand_tiles)
    if not cand_moves:
        return None, hand_tiles, 0

    best = None
    best_score = -1

    for new_board, remaining in cand_moves:
        played = [t for t in hand_tiles if t not in remaining]
        points = sum(t[0] for t in played)
        # If initial_done is False, enforce 30+ in one move
        if not initial_done and points < 30:
            continue
        # simple heuristic: maximize points played, then minimize remaining tiles
        score = (points, -len(remaining))
        if score > best_score:
            best_score = score
            best = (new_board, remaining, points)

    if best is None:
        return None, hand_tiles, 0
    return best
