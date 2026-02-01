from enum import Enum
import random
from typing import Tuple, List
from collections import Counter

class Action(Enum):
    HIT = "Hit"
    STAND = "Stand"
    DOUBLE = "Double"

# --- Core Logic ---

def _draw_card() -> int:
    """Draw a card value from an infinite deck approximation."""
    population = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    weights = [4, 4, 4, 4, 4, 4, 4, 4, 16, 4]
    return random.choices(population, weights)[0]

def _apply_card(total: int, is_soft: bool, card: int) -> Tuple[int, bool]:
    """Add a drawn card to a running total, adjust for Ace (soft) handling."""
    if card == 11:
        if total + 11 <= 21:
            total += 11
            is_soft = True
        else:
            total += 1
    else:
        total += card

    if total > 21 and is_soft:
        total -= 10
        is_soft = False
    return total, is_soft

def blackjack_advisor(player_total: int, dealer_card: int, is_soft_hand: bool = False) -> Action:
    """Return recommended Action according to basic strategy."""
    if not (4 <= player_total <= 21):
        # Handle bust or weird inputs gracefully by defaulting to Stand if > 21
        if player_total > 21: return Action.STAND
    
    # Soft-hand strategy
    if is_soft_hand:
        if player_total <= 17:
            if player_total in (13, 14):
                return Action.DOUBLE if 5 <= dealer_card <= 6 else Action.HIT
            if player_total in (15, 16):
                return Action.DOUBLE if 4 <= dealer_card <= 6 else Action.HIT
            if player_total == 17:
                return Action.DOUBLE if 3 <= dealer_card <= 6 else Action.HIT
        if player_total == 18:
            if dealer_card in (2, 7, 8): return Action.STAND
            if 3 <= dealer_card <= 6: return Action.DOUBLE
            return Action.HIT
        if player_total >= 19:
            return Action.STAND

    # Hard-hand strategy
    if player_total <= 8: return Action.HIT
    if player_total == 9:
        return Action.DOUBLE if 3 <= dealer_card <= 6 else Action.HIT
    if player_total in (10, 11):
        if player_total == 11:
            return Action.DOUBLE if dealer_card <= 10 else Action.HIT
        return Action.DOUBLE if dealer_card <= 9 else Action.HIT
    if 12 <= player_total <= 16:
        if dealer_card <= 6:
            if player_total == 12 and dealer_card in (2, 3): return Action.HIT
            return Action.STAND
        return Action.HIT
    if player_total >= 17: return Action.STAND

    return Action.HIT

def action_to_text(action: Action) -> str:
    if action == Action.HIT: return "Hit (จั่วเพิ่ม)"
    if action == Action.STAND: return "Stand (อยู่)"
    if action == Action.DOUBLE: return "Double (ลงเงินเพิ่ม/จั่ว 1 ใบ)"
    return "Unknown"

# --- Simulation & Shoe Management ---

def build_shoe(num_decks: int) -> list:
    """Return a list of card values representing a shoe with num_decks decks."""
    shoe = []
    for _ in range(num_decks):
        shoe.extend([2, 3, 4, 5, 6, 7, 8, 9] * 4) # 2-9
        shoe.extend([10] * 16) # 10, J, Q, K
        shoe.extend([11] * 4)  # Ace
    return shoe

def remove_known_cards(shoe: list, known_cards: list) -> None:
    """Remove known card values from the shoe in-place."""
    for card in known_cards:
        try:
            shoe.remove(card)
        except ValueError:
            pass # Card already removed or logic error in tracking

def draw_from_shoe(shoe: list) -> int:
    if not shoe: raise RuntimeError("Shoe is empty")
    card = random.choice(shoe)
    shoe.remove(card)
    return card

def compute_total_and_soft(cards: list) -> Tuple[int, bool]:
    total = 0
    soft = False
    for c in cards:
        total, soft = _apply_card(total, soft, c)
    return total, soft

def calculate_hilo(seen_cards: list) -> Tuple[int, float]:
    """Calculate Running Count and True Count."""
    running_count = 0
    for card in seen_cards:
        if 2 <= card <= 6:
            running_count += 1
        elif card == 10 or card == 11: # 10, J, Q, K, A
            running_count -= 1
        # 7, 8, 9 are 0
    return running_count

def estimate_win_probabilities_multi(players_hands: list,
                                     dealer_upcard: int,
                                     num_decks: int = 6,
                                     simulations: int = 5000,
                                     cards_seen_history: list = None) -> Tuple[list, Counter, Counter]:
    """
    Simulate outcomes considering BOTH current hands AND previously seen cards (cards_seen_history).
    """
    if cards_seen_history is None:
        cards_seen_history = []

    num_players = len(players_hands)
    wins = [0] * num_players
    pushes = [0] * num_players
    losses = [0] * num_players
    dealer_totals = Counter()
    hidden_card_counts = Counter()

    # Create the base shoe logic
    base_shoe_full = build_shoe(num_decks)
    
    # Identify cards currently on table
    current_round_cards = [dealer_upcard]
    for h in players_hands:
        current_round_cards.extend(h)

    # Validate that our history + current cards don't exceed the deck
    # (Simple check, in a real game we assume input is correct)
    
    for _ in range(simulations):
        # 1. Reconstruct the shoe state at the START of this round
        shoe = base_shoe_full.copy()
        
        # 2. Remove cards from previous rounds (History)
        remove_known_cards(shoe, cards_seen_history)
        
        # 3. Remove cards currently on the table
        remove_known_cards(shoe, current_round_cards)

        # 4. Dealer draws hidden card
        try:
            hidden = draw_from_shoe(shoe)
        except RuntimeError:
            hidden = _draw_card() # Fallback
        
        hidden_card_counts[hidden] += 1

        # 5. Simulate Players
        player_results = [] # (busted, total)
        for idx, hand in enumerate(players_hands):
            total, soft = compute_total_and_soft(hand)
            action = blackjack_advisor(total, dealer_upcard, soft)

            if action == Action.DOUBLE:
                try:
                    card = draw_from_shoe(shoe)
                except RuntimeError: card = _draw_card()
                total, soft = _apply_card(total, soft, card)
            else:
                while action == Action.HIT and total < 22:
                    try:
                        card = draw_from_shoe(shoe)
                    except RuntimeError: card = _draw_card()
                    total, soft = _apply_card(total, soft, card)
                    if total > 21: break
                    action = blackjack_advisor(total, dealer_upcard, soft)
            
            player_results.append((total > 21, total))

        # 6. Simulate Dealer
        d_total = dealer_upcard
        d_soft = (dealer_upcard == 11)
        d_total, d_soft = _apply_card(d_total, d_soft, hidden)
        
        while d_total < 17 or (d_total == 17 and d_soft):
            try:
                card = draw_from_shoe(shoe)
            except RuntimeError: card = _draw_card()
            d_total, d_soft = _apply_card(d_total, d_soft, card)

        dealer_totals[d_total] += 1

        # 7. Score
        for i, (busted, p_total) in enumerate(player_results):
            if busted:
                losses[i] += 1
            else:
                if d_total > 21: wins[i] += 1
                elif d_total < p_total: wins[i] += 1
                elif d_total == p_total: pushes[i] += 1
                else: losses[i] += 1

    results = []
    for i in range(num_players):
        results.append((wins[i]/simulations, pushes[i]/simulations, losses[i]/simulations))

    return results, dealer_totals, hidden_card_counts

# --- Main Interaction Loop ---

def main():
    print("=== Blackjack Pro Advisor & Simulator (ต่อเนื่อง) ===")
    print("ระบบจะจำไพ่ที่ออกไปแล้ว เพื่อความแม่นยำในรอบถัดไป (Card Counting)")
    
    try:
        num_decks = int(input("จำนวนเด็ค (เช่น 6, 8): ") or "6")
        num_players = int(input("จำนวนผู้เล่น (รวมคุณ): ") or "1")
        sims = int(input("จำนวนการจำลองต่อรอบ (Default 3000): ") or "3000")
    except ValueError:
        print("ค่าเริ่มต้นไม่ถูกต้อง")
        return

    # Game State
    cards_history = []  # Cards seen in previous rounds
    round_num = 1
    
    while True:
        print(f"\n--- Round {round_num} ---")
        
        # Calculate Hi-Lo info
        running_count = calculate_hilo(cards_history)
        # Estimate remaining decks roughly
        total_cards = num_decks * 52
        cards_left = max(1, total_cards - len(cards_history))
        decks_left = cards_left / 52
        true_count = running_count / decks_left if decks_left > 0 else 0
        
        print(f" สถานะสำรับ: ออกไปแล้ว {len(cards_history)}/{total_cards} ใบ")
        print(f" Card Counting: Running = {running_count}, True = {true_count:.2f}")
        if true_count >= 1.5:
            print(" [!] True Count สูง: ผู้เล่นเริ่มได้เปรียบ (ควรเพิ่มเงินเดิมพัน)")
        elif true_count <= -1.5:
            print(" [!] True Count ต่ำ: เจ้ามือได้เปรียบ (ควรลดเงินเดิมพัน)")

        print("-" * 30)

        # Get inputs for this round
        players_hands = []
        current_round_cards = [] # To add to history later

        try:
            dealer_input = input("ไพ่หงายเจ้ามือ (2-11): ").strip()
            if dealer_input.lower() in ['q', 'quit', 'exit']: break
            if dealer_input.lower() == 'r': 
                print("\n*** สับไพ่ใหม่ (Reshuffling) ***")
                cards_history = []
                round_num = 1
                continue
                
            dealer_upcard = int(dealer_input)
            current_round_cards.append(dealer_upcard)

            for i in range(num_players):
                raw = input(f"ไพ่ผู้เล่น {i+1} (เช่น '10 6'): ").strip()
                if raw:
                    cards = [int(x) for x in raw.split()]
                    players_hands.append(cards)
                    current_round_cards.extend(cards)
                else:
                    players_hands.append([]) # No cards? Skip logic

        except ValueError:
            print("ข้อมูลไพ่ผิดพลาด กรุณาลองใหม่")
            continue

        # Advice Phase
        print("\n>> คำแนะนำเบื้องต้น (Basic Strategy):")
        for idx, hand in enumerate(players_hands):
            if not hand: continue
            total, soft = compute_total_and_soft(hand)
            action = blackjack_advisor(total, dealer_upcard, soft)
            print(f" ผู้เล่น {idx+1} ({total} {'Soft' if soft else ''}): \033[1m{action_to_text(action)}\033[0m")

        # Simulation Phase
        print(f"\n>> กำลังจำลองผลลัพธ์ {sims} ครั้ง (อิงจากไพ่ที่เหลือ)...")
        results, d_totals, hidden_counts = estimate_win_probabilities_multi(
            players_hands, 
            dealer_upcard, 
            num_decks=num_decks, 
            simulations=sims,
            cards_seen_history=cards_history # Pass history here
        )

        for idx, (w, p, l) in enumerate(results):
            if not players_hands[idx]: continue
            print(f" ผู้เล่น {idx+1}: โอกาสชนะ {w*100:.1f}% | เสมอ {p*100:.1f}% | แพ้ {l*100:.1f}%")

        # Update History
        # ในความเป็นจริง เราควรถามไพ่ที่จั่วเพิ่ม (Hit cards) ด้วยเพื่อให้แม่นยำที่สุด
        # แต่เพื่อความง่าย เราจะบันทึกไพ่เริ่มต้นลง History ก่อน
        cards_history.extend(current_round_cards)
        
        # Optional: Ask for extra cards seen (Hits)
        extra = input("\nจบรอบ - มีไพ่อื่นๆ โผล่มาเพิ่มหรือไม่? (ระบุเลข หรือ Enter ผ่าน): ").strip()
        if extra:
            try:
                extra_cards = [int(x) for x in extra.split()]
                cards_history.extend(extra_cards)
                print(f" บันทึกไพ่เพิ่ม {len(extra_cards)} ใบ")
            except:
                print(" ใส่ผิด ข้ามไป...")

        print("\n" + "="*40)
        round_num += 1

if __name__ == "__main__":
    main()