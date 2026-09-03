"""
app/data/modules/alphabet_en.py — English Alphabet Tracing Data v1

Structure per letter:
  svg_path         — SVG path 'd' attribute for rendering the letter outline
  strokes          — ordered list of strokes with tracing points
    id             — 1-indexed stroke order (enforced in Phase 3)
    points         — [[x, y], ...] normalized to 100×100 grid
    direction      — human-readable direction hint
    hint           — text shown to user if they trace this stroke incorrectly
  difficulty_modifier  — multiplier on the base accuracy threshold
                         <1.0 = easier, >1.0 = harder (used in Phase 11)
  stroke_order_required — whether strokes must be drawn in order
  start_point      — [x, y] where the first stroke begins

Coordinate system: 0,0 = top-left, 100,100 = bottom-right
All paths designed for a 100×100 viewBox.

VERSION = "v1"  — bump when paths or strokes change so ML datasets stay consistent
"""

VERSION = "v1"

ALPHABET: dict[str, dict] = {
    "A": {
        "svg_path": "M 50 5 L 5 95 M 50 5 L 95 95 M 20 65 L 80 65",
        "strokes": [
            {
                "id": 1,
                "points": [[50, 5], [5, 95]],
                "direction": "down-left",
                "hint": "Start at the top and draw down to the left",
            },
            {
                "id": 2,
                "points": [[50, 5], [95, 95]],
                "direction": "down-right",
                "hint": "Start at the top and draw down to the right",
            },
            {
                "id": 3,
                "points": [[20, 65], [80, 65]],
                "direction": "right",
                "hint": "Draw the crossbar from left to right",
            },
        ],
        "difficulty_modifier": 1.2,
        "stroke_order_required": True,
        "start_point": [50, 5],
    },
    "B": {
        "svg_path": "M 20 5 L 20 95 M 20 5 Q 70 5 70 30 Q 70 50 20 50 M 20 50 Q 75 50 75 72 Q 75 95 20 95",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw a straight vertical line downward",
            },
            {
                "id": 2,
                "points": [[20, 5], [70, 5], [70, 30], [20, 50]],
                "direction": "curve-right-down",
                "hint": "Draw the top bump curving to the right and back",
            },
            {
                "id": 3,
                "points": [[20, 50], [75, 50], [75, 72], [20, 95]],
                "direction": "curve-right-down",
                "hint": "Draw the bottom bump — slightly wider than the top",
            },
        ],
        "difficulty_modifier": 1.3,
        "stroke_order_required": True,
        "start_point": [20, 5],
    },
    "C": {
        "svg_path": "M 85 20 Q 50 -5 15 50 Q 50 105 85 80",
        "strokes": [
            {
                "id": 1,
                "points": [[85, 20], [50, 5], [15, 50], [50, 95], [85, 80]],
                "direction": "curve-left",
                "hint": "Draw a large open curve from top-right to bottom-right",
            },
        ],
        "difficulty_modifier": 0.9,
        "stroke_order_required": False,
        "start_point": [85, 20],
    },
    "D": {
        "svg_path": "M 20 5 L 20 95 M 20 5 Q 90 5 90 50 Q 90 95 20 95",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw a straight vertical line",
            },
            {
                "id": 2,
                "points": [[20, 5], [90, 5], [90, 50], [90, 95], [20, 95]],
                "direction": "curve-right",
                "hint": "Draw the large curve from top to bottom on the right side",
            },
        ],
        "difficulty_modifier": 1.0,
        "stroke_order_required": True,
        "start_point": [20, 5],
    },
    "E": {
        "svg_path": "M 80 5 L 20 5 L 20 95 L 80 95 M 20 50 L 65 50",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw the vertical backbone straight down",
            },
            {
                "id": 2,
                "points": [[20, 5], [80, 5]],
                "direction": "right",
                "hint": "Draw the top horizontal line to the right",
            },
            {
                "id": 3,
                "points": [[20, 50], [65, 50]],
                "direction": "right",
                "hint": "Draw the middle bar — slightly shorter than the top",
            },
            {
                "id": 4,
                "points": [[20, 95], [80, 95]],
                "direction": "right",
                "hint": "Draw the bottom horizontal line to the right",
            },
        ],
        "difficulty_modifier": 1.0,
        "stroke_order_required": False,
        "start_point": [20, 5],
    },
    "F": {
        "svg_path": "M 20 5 L 20 95 M 20 5 L 80 5 M 20 50 L 65 50",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw the vertical line straight down",
            },
            {
                "id": 2,
                "points": [[20, 5], [80, 5]],
                "direction": "right",
                "hint": "Draw the top bar to the right",
            },
            {
                "id": 3,
                "points": [[20, 50], [65, 50]],
                "direction": "right",
                "hint": "Draw the middle bar — shorter than the top",
            },
        ],
        "difficulty_modifier": 0.9,
        "stroke_order_required": False,
        "start_point": [20, 5],
    },
    "G": {
        "svg_path": "M 85 20 Q 50 -5 15 50 Q 50 105 85 80 L 85 50 L 55 50",
        "strokes": [
            {
                "id": 1,
                "points": [[85, 20], [50, 5], [15, 50], [50, 95], [85, 80]],
                "direction": "curve-left",
                "hint": "Draw a C-shape curve first",
            },
            {
                "id": 2,
                "points": [[85, 80], [85, 50], [55, 50]],
                "direction": "left",
                "hint": "Draw the shelf going inward at mid-height",
            },
        ],
        "difficulty_modifier": 1.2,
        "stroke_order_required": True,
        "start_point": [85, 20],
    },
    "H": {
        "svg_path": "M 20 5 L 20 95 M 80 5 L 80 95 M 20 50 L 80 50",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw the left vertical line",
            },
            {
                "id": 2,
                "points": [[80, 5], [80, 95]],
                "direction": "down",
                "hint": "Draw the right vertical line",
            },
            {
                "id": 3,
                "points": [[20, 50], [80, 50]],
                "direction": "right",
                "hint": "Connect the two lines with a crossbar at the middle",
            },
        ],
        "difficulty_modifier": 0.9,
        "stroke_order_required": False,
        "start_point": [20, 5],
    },
    "I": {
        "svg_path": "M 50 5 L 50 95 M 30 5 L 70 5 M 30 95 L 70 95",
        "strokes": [
            {
                "id": 1,
                "points": [[50, 5], [50, 95]],
                "direction": "down",
                "hint": "Draw a straight vertical line in the center",
            },
            {
                "id": 2,
                "points": [[30, 5], [70, 5]],
                "direction": "right",
                "hint": "Add the top serif bar",
            },
            {
                "id": 3,
                "points": [[30, 95], [70, 95]],
                "direction": "right",
                "hint": "Add the bottom serif bar",
            },
        ],
        "difficulty_modifier": 0.7,
        "stroke_order_required": False,
        "start_point": [50, 5],
    },
    "J": {
        "svg_path": "M 65 5 L 65 75 Q 65 95 45 95 Q 25 95 25 75",
        "strokes": [
            {
                "id": 1,
                "points": [[65, 5], [65, 75], [45, 95], [25, 75]],
                "direction": "down-curve-left",
                "hint": "Draw down then curve left at the bottom like a hook",
            },
        ],
        "difficulty_modifier": 0.9,
        "stroke_order_required": False,
        "start_point": [65, 5],
    },
    "K": {
        "svg_path": "M 20 5 L 20 95 M 20 50 L 80 5 M 20 50 L 80 95",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw the vertical backbone",
            },
            {
                "id": 2,
                "points": [[20, 50], [80, 5]],
                "direction": "up-right",
                "hint": "Draw the upper diagonal up and to the right",
            },
            {
                "id": 3,
                "points": [[20, 50], [80, 95]],
                "direction": "down-right",
                "hint": "Draw the lower diagonal down and to the right",
            },
        ],
        "difficulty_modifier": 1.1,
        "stroke_order_required": False,
        "start_point": [20, 5],
    },
    "L": {
        "svg_path": "M 20 5 L 20 95 L 80 95",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw the vertical line down",
            },
            {
                "id": 2,
                "points": [[20, 95], [80, 95]],
                "direction": "right",
                "hint": "Draw the foot to the right at the bottom",
            },
        ],
        "difficulty_modifier": 0.7,
        "stroke_order_required": True,
        "start_point": [20, 5],
    },
    "M": {
        "svg_path": "M 10 95 L 10 5 L 50 55 L 90 5 L 90 95",
        "strokes": [
            {
                "id": 1,
                "points": [[10, 95], [10, 5]],
                "direction": "up",
                "hint": "Draw the left vertical line upward",
            },
            {
                "id": 2,
                "points": [[10, 5], [50, 55]],
                "direction": "down-right",
                "hint": "Diagonal down to the center valley",
            },
            {
                "id": 3,
                "points": [[50, 55], [90, 5]],
                "direction": "up-right",
                "hint": "Diagonal up to the right peak",
            },
            {
                "id": 4,
                "points": [[90, 5], [90, 95]],
                "direction": "down",
                "hint": "Draw the right vertical line down",
            },
        ],
        "difficulty_modifier": 1.3,
        "stroke_order_required": True,
        "start_point": [10, 95],
    },
    "N": {
        "svg_path": "M 20 95 L 20 5 L 80 95 L 80 5",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 95], [20, 5]],
                "direction": "up",
                "hint": "Draw the left vertical line upward",
            },
            {
                "id": 2,
                "points": [[20, 5], [80, 95]],
                "direction": "down-right",
                "hint": "Draw the diagonal down to the right",
            },
            {
                "id": 3,
                "points": [[80, 95], [80, 5]],
                "direction": "up",
                "hint": "Draw the right vertical line upward",
            },
        ],
        "difficulty_modifier": 1.1,
        "stroke_order_required": True,
        "start_point": [20, 95],
    },
    "O": {
        "svg_path": "M 50 5 Q 95 5 95 50 Q 95 95 50 95 Q 5 95 5 50 Q 5 5 50 5",
        "strokes": [
            {
                "id": 1,
                "points": [[50, 5], [95, 50], [50, 95], [5, 50], [50, 5]],
                "direction": "clockwise-oval",
                "hint": "Draw a smooth oval — keep it even on all sides",
            },
        ],
        "difficulty_modifier": 1.0,
        "stroke_order_required": False,
        "start_point": [50, 5],
    },
    "P": {
        "svg_path": "M 20 5 L 20 95 M 20 5 Q 75 5 75 30 Q 75 55 20 55",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw the vertical backbone",
            },
            {
                "id": 2,
                "points": [[20, 5], [75, 5], [75, 30], [20, 55]],
                "direction": "curve-right",
                "hint": "Draw the bump curving to the right and back to mid-height",
            },
        ],
        "difficulty_modifier": 1.0,
        "stroke_order_required": True,
        "start_point": [20, 5],
    },
    "Q": {
        "svg_path": "M 50 5 Q 95 5 95 50 Q 95 95 50 95 Q 5 95 5 50 Q 5 5 50 5 M 65 70 L 90 95",
        "strokes": [
            {
                "id": 1,
                "points": [[50, 5], [95, 50], [50, 95], [5, 50], [50, 5]],
                "direction": "clockwise-oval",
                "hint": "Draw the O first",
            },
            {
                "id": 2,
                "points": [[65, 70], [90, 95]],
                "direction": "down-right",
                "hint": "Add the small tail in the lower-right",
            },
        ],
        "difficulty_modifier": 1.2,
        "stroke_order_required": True,
        "start_point": [50, 5],
    },
    "R": {
        "svg_path": "M 20 5 L 20 95 M 20 5 Q 75 5 75 30 Q 75 55 20 55 M 20 55 L 80 95",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 95]],
                "direction": "down",
                "hint": "Draw the vertical backbone",
            },
            {
                "id": 2,
                "points": [[20, 5], [75, 5], [75, 30], [20, 55]],
                "direction": "curve-right",
                "hint": "Draw the bump (same as P)",
            },
            {
                "id": 3,
                "points": [[20, 55], [80, 95]],
                "direction": "down-right",
                "hint": "Draw the leg diagonally down to the right",
            },
        ],
        "difficulty_modifier": 1.2,
        "stroke_order_required": True,
        "start_point": [20, 5],
    },
    "S": {
        "svg_path": "M 80 15 Q 50 -5 20 20 Q 5 40 50 50 Q 95 60 80 80 Q 60 100 20 85",
        "strokes": [
            {
                "id": 1,
                "points": [[80, 15], [50, 5], [20, 20], [5, 40], [50, 50],
                           [95, 60], [80, 80], [50, 95], [20, 85]],
                "direction": "s-curve",
                "hint": "Draw a smooth S-curve — top curves left, bottom curves right",
            },
        ],
        "difficulty_modifier": 1.4,
        "stroke_order_required": False,
        "start_point": [80, 15],
    },
    "T": {
        "svg_path": "M 50 5 L 50 95 M 10 5 L 90 5",
        "strokes": [
            {
                "id": 1,
                "points": [[10, 5], [90, 5]],
                "direction": "right",
                "hint": "Draw the top bar first",
            },
            {
                "id": 2,
                "points": [[50, 5], [50, 95]],
                "direction": "down",
                "hint": "Draw the vertical line from the center downward",
            },
        ],
        "difficulty_modifier": 0.8,
        "stroke_order_required": False,
        "start_point": [10, 5],
    },
    "U": {
        "svg_path": "M 20 5 L 20 70 Q 20 95 50 95 Q 80 95 80 70 L 80 5",
        "strokes": [
            {
                "id": 1,
                "points": [[20, 5], [20, 70], [50, 95], [80, 70], [80, 5]],
                "direction": "down-curve-up",
                "hint": "Draw down the left, curve at the bottom, and back up",
            },
        ],
        "difficulty_modifier": 0.9,
        "stroke_order_required": False,
        "start_point": [20, 5],
    },
    "V": {
        "svg_path": "M 10 5 L 50 95 L 90 5",
        "strokes": [
            {
                "id": 1,
                "points": [[10, 5], [50, 95]],
                "direction": "down-right",
                "hint": "Draw the left diagonal down to the center point",
            },
            {
                "id": 2,
                "points": [[50, 95], [90, 5]],
                "direction": "up-right",
                "hint": "Draw the right diagonal up and to the right",
            },
        ],
        "difficulty_modifier": 0.9,
        "stroke_order_required": True,
        "start_point": [10, 5],
    },
    "W": {
        "svg_path": "M 5 5 L 25 95 L 50 50 L 75 95 L 95 5",
        "strokes": [
            {
                "id": 1,
                "points": [[5, 5], [25, 95]],
                "direction": "down-right",
                "hint": "Draw the first diagonal down",
            },
            {
                "id": 2,
                "points": [[25, 95], [50, 50]],
                "direction": "up-right",
                "hint": "Draw up to the center valley",
            },
            {
                "id": 3,
                "points": [[50, 50], [75, 95]],
                "direction": "down-right",
                "hint": "Draw down to the second valley",
            },
            {
                "id": 4,
                "points": [[75, 95], [95, 5]],
                "direction": "up-right",
                "hint": "Draw up to the top right",
            },
        ],
        "difficulty_modifier": 1.3,
        "stroke_order_required": True,
        "start_point": [5, 5],
    },
    "X": {
        "svg_path": "M 10 5 L 90 95 M 90 5 L 10 95",
        "strokes": [
            {
                "id": 1,
                "points": [[10, 5], [90, 95]],
                "direction": "down-right",
                "hint": "Draw the first diagonal from top-left to bottom-right",
            },
            {
                "id": 2,
                "points": [[90, 5], [10, 95]],
                "direction": "down-left",
                "hint": "Cross it with a diagonal from top-right to bottom-left",
            },
        ],
        "difficulty_modifier": 0.8,
        "stroke_order_required": False,
        "start_point": [10, 5],
    },
    "Y": {
        "svg_path": "M 10 5 L 50 50 M 90 5 L 50 50 L 50 95",
        "strokes": [
            {
                "id": 1,
                "points": [[10, 5], [50, 50]],
                "direction": "down-right",
                "hint": "Draw the left arm down to the center",
            },
            {
                "id": 2,
                "points": [[90, 5], [50, 50]],
                "direction": "down-left",
                "hint": "Draw the right arm down to the center",
            },
            {
                "id": 3,
                "points": [[50, 50], [50, 95]],
                "direction": "down",
                "hint": "Draw the tail straight down",
            },
        ],
        "difficulty_modifier": 1.0,
        "stroke_order_required": True,
        "start_point": [10, 5],
    },
    "Z": {
        "svg_path": "M 10 5 L 90 5 L 10 95 L 90 95",
        "strokes": [
            {
                "id": 1,
                "points": [[10, 5], [90, 5]],
                "direction": "right",
                "hint": "Draw the top bar left to right",
            },
            {
                "id": 2,
                "points": [[90, 5], [10, 95]],
                "direction": "down-left",
                "hint": "Draw the diagonal down to the lower-left",
            },
            {
                "id": 3,
                "points": [[10, 95], [90, 95]],
                "direction": "right",
                "hint": "Draw the bottom bar left to right",
            },
        ],
        "difficulty_modifier": 1.0,
        "stroke_order_required": True,
        "start_point": [10, 5],
    },
}


def get_letter(letter: str) -> dict:
    """Return tracing data for a single uppercase letter."""
    key = letter.upper()
    if key not in ALPHABET:
        raise KeyError(f"Letter '{key}' not found in English alphabet data.")
    return {"letter": key, "version": VERSION, **ALPHABET[key]}


def get_all_letters() -> list[str]:
    """Return sorted list of all available letters."""
    return sorted(ALPHABET.keys())


def get_letters_by_difficulty(modifier_max: float) -> list[str]:
    """Return letters where difficulty_modifier <= modifier_max (easier letters first)."""
    return sorted(
        [k for k, v in ALPHABET.items() if v["difficulty_modifier"] <= modifier_max],
        key=lambda k: ALPHABET[k]["difficulty_modifier"]
    )
