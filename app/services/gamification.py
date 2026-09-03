class GamificationService:

    LEVEL_CONFIG = {
        1: {"spacing_weight": 0.1, "difficulty": 0.7},
        2: {"spacing_weight": 0.25, "difficulty": 1.0},
        3: {"spacing_weight": 0.3, "difficulty": 1.2},
    }

    def apply(self, scores: dict, level: int = 2):
        """
        Main entry point for gamification logic.
        """
        overall = scores.get("overall_score", scores.get("overall", 0))

        # Adjust based on difficulty
        config = self.LEVEL_CONFIG.get(level, self.LEVEL_CONFIG[2])
        difficulty = config["difficulty"]
        
        adjusted_score = max(0, min(100, overall * difficulty))

        stars = self._to_stars(adjusted_score)
        grade = self._to_grade(adjusted_score)

        return {
            "adjusted_score": adjusted_score,
            "stars": stars,
            "grade": grade,
            "level": level,
        }

    def _to_stars(self, score):
        if score >= 85:
            return 5
        elif score >= 70:
            return 4
        elif score >= 55:
            return 3
        elif score >= 40:
            return 2
        else:
            return 1

    def _to_grade(self, score):
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        else:
            return "D"
