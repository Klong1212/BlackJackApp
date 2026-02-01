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


if __name__ == "__main__":
    print("--- Blackjack Real-time Advisor + Win Estimator ---")
    try:
        p_score = int(input("แต้มรวมของคุณ: "))
        d_card = int(input("ไพ่ใบเดียวของเจ้ามือ (2-11, 11=Ace): "))
        s = input("เป็น soft hand ไหม (y/n): ").strip().lower() == 'y'
    except ValueError:
        print("ค่าไม่ถูกต้อง — กรุณาใส่ตัวเลขตามคำแนะนำ")
        raise

    decision = blackjack_advisor(p_score, d_card, s)
    win, push, lose = estimate_win_probability(p_score, d_card, s, simulations=3000)

    print(f"คำแนะนำ: {action_to_text(decision)}")
    print(f"ประมาณความน่าจะเป็น: ชนะ {win*100:.1f}%, เสมอ {push*100:.1f}%, แพ้ {lose*100:.1f}%")
