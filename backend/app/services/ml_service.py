import joblib
import os

class MLService:
    def __init__(self):
        # We need to find the model file regardless of where the app is executed from
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../model.pkl')
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            print(f"Warning: ML model not found at {model_path}. Shadow scoring disabled.")
            self.model = None

    def predict(self, features):
        if not self.model or not features:
            return 0.0
            
        x = [[
            features.get("slant_std", 0),
            features.get("spacing_std", 0),
            features.get("baseline_var", 0),
            features.get("stroke_var", 0),
        ]]
        return float(self.model.predict(x)[0])
