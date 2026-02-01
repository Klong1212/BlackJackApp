from enum import Enum
import random
from typing import Tuple


class Action(Enum):
    HIT = "Hit"
    STAND = "Stand"
    DOUBLE = "Double"


def _draw_card() -> int:
    """Draw a card value from an infinite deck approximation.
    Returns 2-11 where 11 means Ace.
    Distribution: 2-9: 4/52 each, 10-valued: 16/52, Ace: 4/52.
    """
    population = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    weights = [4, 4, 4, 4, 4, 4, 4, 4, 16, 4]
    return random.choices(population, weights)[0]


def _apply_card(total: int, is_soft: bool, card: int) -> Tuple[int, bool]:
    """Add a drawn card to a running total, adjust for Ace (soft) handling."""
    if card == 11:  # Ace
        # prefer counting Ace as 11 if it doesn't bust
        if total + 11 <= 21:
            total += 11
            is_soft = True
        else:
            total += 1
    else:
        total += card

    # If busted but had a soft Ace, convert it to hard (subtract 10)
    if total > 21 and is_soft:
        total -= 10
        is_soft = False
    return total, is_soft


def blackjack_advisor(player_total: int, dealer_card: int, is_soft_hand: bool = False) -> Action:
    """Return recommended Action according to basic strategy (hard and soft hands).

    Inputs:
    - player_total: current total (4-21)
    - dealer_card: dealer's upcard value (2-11 where 11 is Ace)
    - is_soft_hand: True if player total includes an Ace counted as 11
    """
    # Basic validation
    if not (4 <= player_total <= 21):
        raise ValueError("player_total must be between 4 and 21")
    if not (2 <= dealer_card <= 11):
        raise ValueError("dealer_card must be between 2 and 11 (11 = Ace)")

    # Soft-hand strategy
    if is_soft_hand:
        # Soft totals: treat common rules
        if player_total <= 17:
            # Soft 13-17 cases
            if player_total in (13, 14):
                return Action.DOUBLE if 5 <= dealer_card <= 6 else Action.HIT
            if player_total in (15, 16):
                return Action.DOUBLE if 4 <= dealer_card <= 6 else Action.HIT
            if player_total == 17:
                return Action.DOUBLE if 3 <= dealer_card <= 6 else Action.HIT
        if player_total == 18:
            if dealer_card in (2, 7, 8):
                return Action.STAND
            if 3 <= dealer_card <= 6:
                return Action.DOUBLE
            return Action.HIT
        if player_total >= 19:
            return Action.STAND

    # Hard-hand strategy (default)
    if player_total <= 8:
        return Action.HIT

    if player_total == 9:
        return Action.DOUBLE if 3 <= dealer_card <= 6 else Action.HIT

    if player_total in (10, 11):
        if player_total == 11:
            return Action.DOUBLE if dealer_card <= 10 else Action.HIT
        # player_total == 10
        return Action.DOUBLE if dealer_card <= 9 else Action.HIT

    if 12 <= player_total <= 16:
        if dealer_card <= 6:
            # exception: 12 vs 2-3 -> Hit
            if player_total == 12 and dealer_card in (2, 3):
                return Action.HIT
            return Action.STAND
        return Action.HIT

    if player_total >= 17:
        return Action.STAND

    return Action.HIT


def estimate_win_probability(player_total: int,
                             dealer_card: int,
                             is_soft_hand: bool = False,
                             simulations: int = 3000) -> Tuple[float, float, float]:
    """Estimate probabilities (win, push, lose) by Monte Carlo simulation.

    Uses an infinite-deck model (draws with replacement).
    Returns fractions (win_prob, push_prob, lose_prob).
    """
    if simulations <= 0:
        raise ValueError("simulations must be > 0")

    wins = pushes = losses = 0

    for _ in range(simulations):
        # Simulate player's play
        total = player_total
        soft = is_soft_hand

        action = blackjack_advisor(total, dealer_card, soft)

        # If initial decision is to double, draw one card then stand
        if action == Action.DOUBLE:
            card = _draw_card()
            total, soft = _apply_card(total, soft, card)
        else:
            # Hit until strategy says Stand
            while action == Action.HIT and total < 22:
                card = _draw_card()
                total, soft = _apply_card(total, soft, card)
                if total > 21:
                    break
                action = blackjack_advisor(total, dealer_card, soft)

        # Check player bust
        if total > 21:
            losses += 1
            continue

        # Simulate dealer
        d_total = dealer_card
        d_soft = (dealer_card == 11)
        # draw one hidden card
        hidden = _draw_card()
        d_total, d_soft = _apply_card(d_total, d_soft, hidden)

        # Dealer hits until 17 or more; stand on soft 17 (S17)
        while d_total < 17 or (d_total == 17 and d_soft):
            card = _draw_card()
            d_total, d_soft = _apply_card(d_total, d_soft, card)

        # Determine outcome
        if d_total > 21:
            wins += 1
        elif d_total < total:
            wins += 1
        elif d_total == total:
            pushes += 1
        else:
            losses += 1

    total_sim = simulations
    return wins / total_sim, pushes / total_sim, losses / total_sim


def action_to_text(action: Action) -> str:
    if action == Action.HIT:
        return "Hit (ขอไพ่เพิ่ม)"
    if action == Action.STAND:
        return "Stand (หยุด)"
    if action == Action.DOUBLE:
        return "Double Down (ถ้าทำได้) มิฉะนั้น Hit"
    return "Unknown"


# --- Finite-shoe utilities and multi-player simulation ---
from collections import Counter


def build_shoe(num_decks: int) -> list:
    """Return a list of card values representing a shoe with num_decks decks."""
    shoe = []
    for _ in range(num_decks):
        shoe.extend([2] * 4)
        shoe.extend([3] * 4)
        shoe.extend([4] * 4)
        shoe.extend([5] * 4)
        shoe.extend([6] * 4)
        shoe.extend([7] * 4)
        shoe.extend([8] * 4)
        shoe.extend([9] * 4)
        shoe.extend([10] * 16)
        shoe.extend([11] * 4)
    return shoe


def remove_known_cards(shoe: list, known_cards: list) -> None:
    """Remove known card values from the shoe in-place (if present)."""
    for card in known_cards:
        try:
            shoe.remove(card)
        except ValueError:
            # Card not found - already removed or shoe doesn't have it
            pass


def draw_from_shoe(shoe: list) -> int:
    """Draw a random card from the shoe (without replacement)."""
    if not shoe:
        raise RuntimeError("Shoe is empty")
    card = random.choice(shoe)
    shoe.remove(card)
    return card


def compute_total_and_soft(cards: list) -> Tuple[int, bool]:
    """Compute total and whether it's soft from a list of card values."""
    total = 0
    soft = False
    for c in cards:
        total, soft = _apply_card(total, soft, c)
    return total, soft


def estimate_win_probabilities_multi(players_hands: list,
                                     dealer_upcard: int,
                                     num_decks: int = 6,
                                     simulations: int = 5000) -> Tuple[list, Counter]:
    """Estimate per-player (win,push,lose) probabilities using a finite shoe and simulating all players sequentially.

    Returns:
    - results: list of tuples (win_prob, push_prob, lose_prob) per player
    - dealer_totals: Counter mapping dealer final total to counts (can be converted to probabilities)
    """
    if num_decks <= 0:
        raise ValueError("num_decks must be >= 1 for finite-shoe simulation")
    if simulations <= 0:
        raise ValueError("simulations must be > 0")

    num_players = len(players_hands)
    wins = [0] * num_players
    pushes = [0] * num_players
    losses = [0] * num_players
    dealer_totals = Counter()

    base_shoe = build_shoe(num_decks)
    known_cards_initial = [dealer_upcard]
    for h in players_hands:
        known_cards_initial.extend(h)

    # Track empirical hidden-card distribution across simulations
    hidden_card_counts = Counter()

    for _ in range(simulations):
        shoe = base_shoe.copy()
        # Remove initial known cards (players' cards and dealer upcard)
        remove_known_cards(shoe, known_cards_initial)

        # Draw dealer's hidden card now (before players play) and remove it from shoe
        try:
            hidden = draw_from_shoe(shoe)
        except RuntimeError:
            hidden = _draw_card()
        hidden_card_counts[hidden] += 1

        # Simulate each player's play sequentially (their actions consume cards)
        player_results = []  # (busted, total)
        for idx, hand in enumerate(players_hands):
            total, soft = compute_total_and_soft(hand)
            action = blackjack_advisor(total, dealer_upcard, soft)

            if action == Action.DOUBLE:
                # draw one card and stand
                try:
                    card = draw_from_shoe(shoe)
                except RuntimeError:
                    card = _draw_card()  # fallback to infinite model
                total, soft = _apply_card(total, soft, card)
            else:
                while action == Action.HIT and total < 22:
                    try:
                        card = draw_from_shoe(shoe)
                    except RuntimeError:
                        card = _draw_card()
                    total, soft = _apply_card(total, soft, card)
                    if total > 21:
                        break
                    action = blackjack_advisor(total, dealer_upcard, soft)

            busted = total > 21
            player_results.append((busted, total))

        # Simulate dealer: start with upcard + hidden (hidden already removed from shoe)
        d_total = dealer_upcard
        d_soft = (dealer_upcard == 11)
        d_total, d_soft = _apply_card(d_total, d_soft, hidden)
        while d_total < 17 or (d_total == 17 and d_soft):
            try:
                card = draw_from_shoe(shoe)
            except RuntimeError:
                card = _draw_card()
            d_total, d_soft = _apply_card(d_total, d_soft, card)

        dealer_totals[d_total] += 1

        # Compare outcomes for each player
        for i, (busted, p_total) in enumerate(player_results):
            if busted:
                losses[i] += 1
            else:
                if d_total > 21:
                    wins[i] += 1
                elif d_total < p_total:
                    wins[i] += 1
                elif d_total == p_total:
                    pushes[i] += 1
                else:
                    losses[i] += 1

    results = []
    for i in range(num_players):
        total_sim = simulations
        results.append((wins[i] / total_sim, pushes[i] / total_sim, losses[i] / total_sim))

    return results, dealer_totals, hidden_card_counts


if __name__ == "__main__":
    print("--- Blackjack Multi-player Finite-shoe Estimator ---")
    try:
        num_decks = int(input("จำนวนเด็ค (เช่น 6): ") or "6")
        num_players = int(input("จำนวนผู้เล่น (รวมคุณ): ") or "1")
        players_hands = []
        for i in range(num_players):
            raw = input(f"ไพ่ของผู้เล่น {i+1} (ค่าสัญลักษณ์เป็นตัวเลข 2-11 คั่นด้วยช่องว่าง, เช่น '10 7' หรือ '11 6'): ").strip()
            if raw == "":
                cards = []
            else:
                cards = [int(x) for x in raw.split()]
            players_hands.append(cards)

        dealer_upcard = int(input("ไพ่หงายของเจ้ามือ (2-11, 11=Ace): "))
        sims = int(input("จำนวนการจำลอง (ค่าเริ่มต้น 5000): ") or "5000")
    except ValueError:
        print("ค่าไม่ถูกต้อง — กรุณาใส่ตัวเลขตามคำแนะนำ")
        raise

    # Compute start totals and basic advice
    for idx, hand in enumerate(players_hands):
        total, soft = compute_total_and_soft(hand)
        action = blackjack_advisor(total, dealer_upcard, soft)
        print(f"ผู้เล่น {idx+1}: ไพ่={hand} -> แต้ม={total} {'soft' if soft else 'hard'}  คำแนะนำ: {action_to_text(action)}")

    results, dealer_totals, hidden_card_counts = estimate_win_probabilities_multi(players_hands, dealer_upcard, num_decks=num_decks, simulations=sims)

    print("\n--- ประมาณความน่าจะเป็นผลลัพธ์สำหรับแต่ละผู้เล่น ---")
    for idx, (w, p, l) in enumerate(results):
        print(f"ผู้เล่น {idx+1}: ชนะ {w*100:.1f}%, เสมอ {p*100:.1f}%, แพ้ {l*100:.1f}%")

    print("\n--- การแจกแจงไพ่ที่เจ้ามืออาจได้ (จากการ์ดที่ยังเหลือในเด็ค) ---")
    total_hidden = sum(hidden_card_counts.values())
    if total_hidden > 0:
        for val in sorted(hidden_card_counts.keys()):
            print(f"ไพ่ {val}: {hidden_card_counts[val]/total_hidden*100:.1f}%")
    else:
        print("ไม่พบการ์ดที่เหลือ (อาจเป็นเพราะการคำนวณจำนวนการ์ดผิดพลาด)")

    print("\n--- การแจกแจงแต้มสุดท้ายของเจ้ามือ (การจำลอง) ---")
    total_dt = sum(dealer_totals.values()) or 1
    for k in sorted(dealer_totals.keys()):
        print(f"เจ้ามือได้ {k}: {dealer_totals[k]/total_dt*100:.1f}%")

    print("\nเสร็จสิ้น")
