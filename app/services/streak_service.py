from datetime import date, timedelta

class StreakService:
    def update_streak(self, user):
        today = date.today()
        
        if user.last_active_date is None:
            user.user_streak = 1
        elif user.last_active_date == today:
            # already counted today
            return user.user_streak
        elif user.last_active_date == today - timedelta(days=1):
            user.user_streak += 1
        else:
            # missed a day → reset
            user.user_streak = 1
            
        user.last_active_date = today
        return user.user_streak
