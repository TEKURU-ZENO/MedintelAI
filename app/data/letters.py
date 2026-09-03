import math

# ------------------------------------------------------------------
# Hardcoded MVP normalized reference points for uppercase letters.
#
# Coordinate system:
# - Values are normalized between 0.0 and 1.0
# - (0,0) represents the top-left of the drawing area
# - (1,1) represents the bottom-right of the drawing area
#
# These points are used as template/reference paths for tracing,
# handwriting comparison, scoring, and guidance generation.
# ------------------------------------------------------------------

LETTER_POINTS = {
    "A": [
        # ----------------------------------------------------------
        # Left diagonal leg of the letter A
        # Starts at bottom-left and moves upward to the apex.
        # ----------------------------------------------------------
        {"x": 0.2 + (0.5 - 0.2) * (i / 10.0),
         "y": 0.8 + (0.2 - 0.8) * (i / 10.0)}
        for i in range(11)

    ] + [

        # ----------------------------------------------------------
        # Right diagonal leg of the letter A
        # Starts at the apex and moves down to bottom-right.
        # ----------------------------------------------------------
        {"x": 0.5 + (0.8 - 0.5) * (i / 10.0),
         "y": 0.2 + (0.8 - 0.2) * (i / 10.0)}
        for i in range(11)

    ] + [

        # ----------------------------------------------------------
        # Horizontal crossbar of the letter A
        # Positioned approximately at the middle height.
        # ----------------------------------------------------------
        {"x": 0.35 + (0.65 - 0.35) * (i / 5.0),
         "y": 0.5}
        for i in range(6)
    ],

    "B": [
        # ----------------------------------------------------------
        # Vertical spine of the letter B
        # Forms the main left-side stroke.
        # ----------------------------------------------------------
        {"x": 0.3,
         "y": 0.2 + 0.6 * (i / 10.0)}
        for i in range(11)

    ] + [

        # ----------------------------------------------------------
        # Bottom loop of the letter B
        # Approximated using a semicircular curve generated
        # with sine and cosine functions.
        # ----------------------------------------------------------
        {"x": 0.3 + 0.3 * math.sin(math.pi * i / 10.0),
         "y": 0.8 - 0.15 + 0.15 * math.cos(math.pi * i / 10.0)}
        for i in range(11)

    ] + [

        # ----------------------------------------------------------
        # Top loop of the letter B
        # Similar semicircular approximation positioned above
        # the bottom loop.
        # ----------------------------------------------------------
        {"x": 0.3 + 0.3 * math.sin(math.pi * i / 10.0),
         "y": 0.5 - 0.15 + 0.15 * math.cos(math.pi * i / 10.0)}
        for i in range(11)
    ],

    "C": [
        # ----------------------------------------------------------
        # Curved stroke of the letter C
        # Generated using a partial circular arc.
        # The angle range is chosen to create an open curve
        # resembling the shape of an uppercase C.
        # ----------------------------------------------------------
        {"x": 0.5 + 0.2 * math.cos(
            math.pi * 0.25 + math.pi * 1.5 * i / 20.0
        ),
         "y": 0.5 + 0.4 * math.sin(
            math.pi * 0.25 + math.pi * 1.5 * i / 20.0
        )}
        for i in range(21)
    ]
}
