"""
Tests for Card and Deck classes.
"""

import pytest
from deeppoker.core.card import Card, Deck, Rank, Suit, parse_cards


class TestCard:
    """Tests for Card class."""
    
    def test_card_creation(self):
        """Test creating a card."""
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES
    
    def test_card_from_string(self):
        """Test creating cards from string notation."""
        # Standard notation
        card1 = Card.from_string("As")
        assert card1.rank == Rank.ACE
        assert card1.suit == Suit.SPADES
        
        # With symbol
        card2 = Card.from_string("K♥")
        assert card2.rank == Rank.KING
        assert card2.suit == Suit.HEARTS
        
        # Ten
        card3 = Card.from_string("Td")
        assert card3.rank == Rank.TEN
        assert card3.suit == Suit.DIAMONDS
    
    def test_card_from_int(self):
        """Test creating cards from integer."""
        # First card (2 of clubs)
        card1 = Card.from_int(0)
        assert card1.rank == Rank.TWO
        assert card1.suit == Suit.CLUBS
        
        # Last card (Ace of spades)
        card2 = Card.from_int(51)
        assert card2.rank == Rank.ACE
        assert card2.suit == Suit.SPADES
    
    def test_card_to_int(self):
        """Test converting card to integer."""
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.to_int() == 51
        
        card2 = Card(Rank.TWO, Suit.CLUBS)
        assert card2.to_int() == 0
    
    def test_card_equality(self):
        """Test card equality."""
        card1 = Card(Rank.ACE, Suit.SPADES)
        card2 = Card(Rank.ACE, Suit.SPADES)
        card3 = Card(Rank.KING, Suit.SPADES)
        
        assert card1 == card2
        assert card1 != card3
    
    def test_card_comparison(self):
        """Test card comparison (by rank)."""
        ace = Card(Rank.ACE, Suit.SPADES)
        king = Card(Rank.KING, Suit.HEARTS)
        two = Card(Rank.TWO, Suit.CLUBS)
        
        assert two < king < ace
    
    def test_card_str(self):
        """Test card string representation."""
        card = Card(Rank.ACE, Suit.SPADES)
        assert str(card) == "A♠"
        assert card.short_str == "As"
    
    def test_card_color(self):
        """Test card color."""
        spade = Card(Rank.ACE, Suit.SPADES)
        heart = Card(Rank.KING, Suit.HEARTS)
        
        assert spade.color == "black"
        assert heart.color == "red"
    
    def test_card_hash(self):
        """Test card hashing (for use in sets/dicts)."""
        card1 = Card(Rank.ACE, Suit.SPADES)
        card2 = Card(Rank.ACE, Suit.SPADES)
        
        card_set = {card1}
        assert card2 in card_set


class TestDeck:
    """Tests for Deck class."""
    
    def test_deck_has_52_cards(self, unshuffled_deck):
        """Test that a new deck has 52 cards."""
        assert len(unshuffled_deck) == 52
        assert unshuffled_deck.remaining == 52
    
    def test_deck_deal(self, deck):
        """Test dealing cards."""
        cards = deck.deal(5)
        assert len(cards) == 5
        assert deck.remaining == 47
    
    def test_deck_deal_one(self, deck):
        """Test dealing a single card."""
        card = deck.deal_one()
        assert isinstance(card, Card)
        assert deck.remaining == 51
    
    def test_deck_burn(self, deck):
        """Test burning a card."""
        initial = deck.remaining
        burned = deck.burn()
        assert isinstance(burned, Card)
        assert deck.remaining == initial - 1
    
    def test_deck_deal_too_many(self, deck):
        """Test dealing too many cards raises error."""
        with pytest.raises(ValueError):
            deck.deal(53)
    
    def test_deck_reset(self, deck):
        """Test resetting the deck."""
        deck.deal(10)
        assert deck.remaining == 42
        
        deck.reset()
        assert deck.remaining == 52
    
    def test_deck_shuffle_changes_order(self, unshuffled_deck):
        """Test that shuffling changes card order."""
        # Get first 5 cards before shuffle
        first_cards_before = unshuffled_deck._cards[:5]
        
        unshuffled_deck.shuffle()
        first_cards_after = unshuffled_deck._cards[:5]
        
        # Very unlikely to be the same after shuffle
        # (technically could fail but probability is ~1 in 3 million)
        assert first_cards_before != first_cards_after
    
    def test_deck_dealt_cards_tracked(self, deck):
        """Test that dealt cards are tracked."""
        dealt = deck.deal(3)
        assert deck.dealt_cards == dealt


class TestParseCards:
    """Tests for parse_cards function."""
    
    def test_parse_space_separated(self):
        """Test parsing space-separated cards."""
        cards = parse_cards("As Kh Qd")
        assert len(cards) == 3
        assert cards[0].rank == Rank.ACE
        assert cards[1].rank == Rank.KING
        assert cards[2].rank == Rank.QUEEN
    
    def test_parse_no_separator(self):
        """Test parsing cards without separator."""
        cards = parse_cards("AsKhQd")
        assert len(cards) == 3
    
    def test_parse_with_symbols(self):
        """Test parsing cards with suit symbols."""
        cards = parse_cards("A♠ K♥ Q♦")
        assert len(cards) == 3
