class DifficultyService:
    def get_level(self, user):
        streak = user.user_streak if user and user.user_streak else 0
        if streak < 3:
            return "beginner"
        elif streak < 7:
            return "intermediate"
        return "advanced"
