"""
app/services/spelling/spelling_state_machine.py — Literacy State Machine

Instead of binary correct/incorrect, this tracks the sequence of spelling cognition:
idle -> listening -> attempting -> partial_success -> correct -> retrying -> celebrating.
"""

from typing import List, Dict, Any, Literal

SpellingState = Literal[
    "idle", 
    "listening", 
    "attempting", 
    "partial_success", 
    "correct", 
    "retrying", 
    "celebrating"
]

class SpellingProgression:
    def __init__(self, target_word: str):
        self.target = target_word.upper()
        self.progress: List[str] = []
        self.state: SpellingState = "idle"
        self.accuracy: float = 0.0
        self.attempts_on_current: int = 0
        
    def get_next_expected(self) -> str | None:
        if len(self.progress) < len(self.target):
            return self.target[len(self.progress)]
        return None
        
    def process_attempt(self, letter: str) -> Dict[str, Any]:
        """Processes a traced letter and transitions the literacy state machine."""
        expected = self.get_next_expected()
        letter = letter.upper()
        
        self.attempts_on_current += 1
        
        if not expected:
            # Word already complete
            return self.snapshot()
            
        if letter == expected:
            self.progress.append(letter)
            self.attempts_on_current = 0
            
            if len(self.progress) == len(self.target):
                self.state = "correct"
            else:
                self.state = "partial_success"
                
        else:
            self.state = "retrying"
            
        self.accuracy = len(self.progress) / len(self.target)
        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "progress": self.progress,
            "next_expected": self.get_next_expected(),
            "state": self.state,
            "accuracy": round(self.accuracy, 2),
            "attempts_on_current": self.attempts_on_current
        }
