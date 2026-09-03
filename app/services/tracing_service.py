import math

class TracingService:
    def evaluate(self, strokes, expected_points, W=400, H=400):
        # flatten + normalize user points to 0–1
        user_points = []
        for s in strokes:
            for p in s:
                user_points.append({"x": p["x"]/W, "y": p["y"]/H})

        if not user_points or not expected_points:
            return {"trace_score": 0, "feedback": ["Try again!"]}

        n = min(len(user_points), len(expected_points))
        total_dist = 0.0

        for i in range(n):
            u = user_points[i]
            e = expected_points[i]
            d = math.hypot(u["x"] - e["x"], u["y"] - e["y"])
            total_dist += d
            
        avg_dist = total_dist / n if n > 0 else 1.0

        score = max(0, min(100, 100 - avg_dist * 120))

        return {
            "trace_score": score,
            "feedback": self._feedback(score)
        }

    def _feedback(self, score):
        if score >= 85: return ["Excellent tracing!"]
        if score >= 65: return ["Nice! Stay a bit closer to the guide."]
        return ["Follow the dotted path more carefully."]
