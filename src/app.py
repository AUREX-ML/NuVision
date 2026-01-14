import streamlit as st
from google import genai
from PIL import Image
import json

# --- CLASS 1: THE BIOLOGICAL ENGINE ---
class BioEngine:
    def __init__(self, age, gender, weight_kg, height_cm, activity_level, goal):
        self.age = age
        self.gender = gender
        self.weight = weight_kg
        self.height = height_cm
        self.activity_level = activity_level
        self.goal = goal

    def calculate_bmr(self):
        if self.gender == "Male":
            return (10 * self.weight) + (6.25 * self.height) - (5 * self.age) + 5
        else:
            return (10 * self.weight) + (6.25 * self.height) - (5 * self.age) - 161

    def calculate_tdee(self):
        bmr = self.calculate_bmr()
        activity_multipliers = {
            "Sedentary (Office job)": 1.2,
            "Lightly Active (1-3 days/week)": 1.375,
            "Moderately Active (3-5 days/week)": 1.55,
            "Very Active (6-7 days/week)": 1.725
        }
        return bmr * activity_multipliers.get(self.activity_level, 1.2)

    def get_daily_target_calories(self):
        tdee = self.calculate_tdee()
        if self.goal == "Lose Weight":
            return tdee - 500
        elif self.goal == "Gain Weight":
            return tdee + 500
        return tdee

# --- CLASS 2: THE VISION ENGINE (AI) ---
class VisionEngine:
    def __init__(self, api_key):

        self.client = genai.Client(api_key=api_key)

    def analyze_plate(self, image):
        """
        1. Classify food
        2. Analyze context (Fried vs Raw)
        3. Estimate Mass based on standard plate size
        4. Return Structured JSON
        """
        prompt = """
        You are a nutritional computer vision engine. 
        Analyze this image assuming the food is on a standard 10-inch dinner plate.
        
        Perform these steps:
        1. CLASSIFY: Identify every distinct food item.
        2. CONTEXT: Analyze texture/sheen to detect cooking method (e.g., Deep Fried = high density, Steamed = low density).
        3. CALCULATE: Estimate the mass (grams) of each item based on visual volume relative to the plate.
        4. SUMMARIZE: Calculate total calories based on mass and type.

        Return ONLY a JSON string in this exact format, no markdown:
        {
            "food_items": [
                {"name": "Food Name", "cooking_method": "Method", "estimated_grams": 0, "calories": 0}
            ],
            "total_calories": 0,
            "health_score": 0 
        }
        """
        try:

            response = self.client.models.generate_content(
                model='gemini-3-flash-preview', 
                contents=[prompt, image]
            )
            
            clean_text = response.text.strip().replace("```json", "").replace("```", "")
            return json.loads(clean_text)
        except Exception as e:
            return {"error": str(e)}

# --- MAIN APP INTERFACE ---
def main():
    st.set_page_config(page_title="NuVision", layout="wide")
    st.title("🍎 NuVision: Bio-Metric Food Scanner")

    # --- SIDEBAR ---
    st.sidebar.header("1. Settings")
    
    # 1. GET API KEY FIRST
    api_key = st.sidebar.text_input("Enter Google Gemini API Key", type="password")
    
    st.sidebar.divider()
    
    gender = st.sidebar.selectbox("Gender", ["Male", "Female"])
    age = st.sidebar.number_input("Age", min_value=18, max_value=100, value=25)
    height = st.sidebar.number_input("Height (cm)", 100, 250, 175)
    weight = st.sidebar.number_input("Weight (kg)", 40, 200, 70)
    activity = st.sidebar.selectbox("Activity Level", [
        "Sedentary (Office job)", 
        "Lightly Active (1-3 days/week)",
        "Moderately Active (3-5 days/week)", 
        "Very Active (6-7 days/week)"
    ])
    goal = st.sidebar.selectbox("Goal", ["Lose Weight", "Maintain Weight", "Gain Weight"])

    # Bio Calculations
    user_bio = BioEngine(age, gender, weight, height, activity, goal)
    target_calories = user_bio.get_daily_target_calories()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("TDEE", f"{int(user_bio.calculate_tdee())} kcal")
    with col2:
        st.metric(f"Target ({goal})", f"{int(target_calories)} kcal")

    st.divider()

    # --- MAIN CAMERA ---
    st.header("2. Visual Analysis")
    camera_image = st.camera_input("Scan your meal")

    # ONLY RUN AI IF WE HAVE AN IMAGE AND A KEY
    if camera_image:
        if not api_key:
            st.error("⚠️ Please enter your API Key in the sidebar to process the image.")
        else:
            img = Image.open(camera_image)
            
            # Pass the key to the engine only now
            vision_bot = VisionEngine(api_key)
            
            with st.spinner("Analyzing..."):
                data = vision_bot.analyze_plate(img)

            if "error" in data:
                st.error(f"AI Error: {data['error']}")
            else:
                meal_cals = data.get('total_calories', 0)
                st.subheader("🍽️ Meal Breakdown")
                
                items = data.get('food_items', [])
                for item in items:
                    st.write(f"**{item.get('name', 'Unknown')}**")
                    st.caption(f"{item.get('estimated_grams', 0)}g | {item.get('calories', 0)} kcal")
                
                st.divider()
                st.metric("Total Meal Calories", f"{meal_cals} kcal")
                
                remaining = target_calories - meal_cals
                if remaining > 0:
                    st.success(f"You have {int(remaining)} kcal remaining today.")
                else:
                    st.warning(f"You exceeded your daily limit by {abs(int(remaining))} kcal.")

if __name__ == "__main__":
    main()