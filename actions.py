# actions.py
import requests
from typing import Any, Text, Dict, List
from rasa_sdk.types import DomainDict
from word2number import w2n
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


API_KEY = '460bddcc77a24c31990ed30e14a1d648'

class ActionSearchRecipesByIngredients(Action):

    def name(self) -> Text:
        return "action_search_recipes_by_ingredients"

    def get_recipe_details(self, recipe_id):
        url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
        params = {
            'apiKey': API_KEY
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return None

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        #ingredients = tracker.get_slot('ingredients')
        ingredients = list(tracker.get_latest_entity_values("ingredients"))
        number = tracker.get_slot('number')
        
        if not ingredients:
            dispatcher.utter_message(text="Please provide ingredients.")
            return []

        if not number:
            number = 10  # Default to 10 if not provided
        else:
            try:
                # Convert number from word to digit if it's in word form
                number = w2n.word_to_num(str(number))
            except ValueError:
                dispatcher.utter_message(text="Please provide a valid number.")
                return []
        
        # Assuming ingredients is a string of comma-separated values
        #ingredients_list = ingredients.split(", ")

        # Convert list to comma-separated string for the API request
        ingredients_str = ",".join(ingredients)

        params = {
            'ingredients': ingredients_str,
            'apiKey': API_KEY,
            'number': number
        }

        response = requests.get("https://api.spoonacular.com/recipes/findByIngredients", params=params)
        data = response.json()

        if response.status_code == 200 and data:
            recipes = []
            for recipe in data:
                recipe_id = recipe['id']
                recipe_details = self.get_recipe_details(recipe_id)
                if recipe_details:
                    title = recipe_details.get('title', 'Title not available')
                    source_url = recipe_details.get('sourceUrl', 'URL not available')
                    recipes.append(f"{title} - {source_url}")
                else:
                    recipes.append(f"{recipe['title']} - URL not available")
            
            #dispatcher.utter_message(text=f"Here are some recipes with {ingredients}:\n" + "\n".join(recipes))
            dispatcher.utter_message(text=f"Here are some recipes with {', '.join(ingredients)}:\n" + "\n".join(recipes))
        else:
            dispatcher.utter_message(text="I couldn't find any recipes with those ingredients.")
        
        return []

class ActionRecipeInformation(Action):

    def name(self) -> Text:
        return "action_recipe_information"

    def get_recipe_information(self, recipe_id=None, recipe_name=None) -> Text:
        # Check if either recipe ID or name is provided
        if not recipe_id and not recipe_name:
            return "Please provide a recipe ID or name to get the recipe information."

        # If recipe name is provided but not recipe ID, perform a search to get the recipe ID
        if not recipe_id and recipe_name:
            search_response = requests.get(
                f"https://api.spoonacular.com/recipes/complexSearch?query={recipe_name}&number=1&apiKey={API_KEY}"
            )
            if search_response.status_code != 200:
                return "There was an error while searching for the recipe."

            search_data = search_response.json()
            if search_data and 'results' in search_data and search_data['results']:
                recipe_id = search_data['results'][0]['id']
            else:
                return f"I couldn't find any recipe with the name '{recipe_name}'."

        # Call the Spoonacular API to get recipe information
        response = requests.get(
            f"https://api.spoonacular.com/recipes/{recipe_id}/information?apiKey={API_KEY}"
        )
        if response.status_code != 200:
            return "There was an error while retrieving the recipe information."

        data = response.json()
        if data:
            title = data.get('title', 'N/A')
            summary = data.get('summary', 'N/A')
            instructions = data.get('instructions', 'N/A')
            ingredients = [ingredient['original'] for ingredient in data.get('extendedIngredients', [])]
            ingredients_text = "\n".join(ingredients) if ingredients else "N/A"
            source_url = data.get('sourceUrl', 'N/A')

            message = (
                f"Recipe Information:\n"
                f"Title: {title}\n"
                f"Summary: {summary}\n"
                f"Ingredients:\n{ingredients_text}\n"
                f"Instructions: {instructions}\n"
                f"Source URL: {source_url}"
            )
            return message
        else:
            return "I couldn't retrieve information for that recipe."

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        recipe_id = tracker.get_slot("recipe_id")
        recipe_name = tracker.get_slot("recipe_name")

        message = self.get_recipe_information(recipe_id=recipe_id, recipe_name=recipe_name)
        dispatcher.utter_message(text=message)

        return []

class ActionGetRandomRecipes(Action):

    def name(self) -> Text:
        return "action_get_random_recipes"
    
    def get_random_recipes(self, number=1, include_tags=None, exclude_tags=None, limit_license=True, include_nutrition=True) -> Text:
        params = {
            'apiKey': API_KEY,
            'number': number if number else 1,  # Default to 1 recipe if number is not provided or invalid
            'limitLicense': str(limit_license).lower(),  # Convert boolean to lowercase string 'true'/'false'
            'includeNutrition': str(include_nutrition).lower()  # Convert boolean to lowercase string 'true'/'false'
        }

        #if include_tags:
            #params['include-tags'] = ','.join(include_tags)
        #if exclude_tags:
            #params['exclude-tags'] = ','.join(exclude_tags)

        if include_tags:
            if isinstance(include_tags, list):
                params['include-tags'] = ','.join(include_tags)
            else:
                params['include-tags'] = include_tags  # Single value case
        if exclude_tags:
            if isinstance(exclude_tags, list):
                params['exclude-tags'] = ','.join(exclude_tags)
            else:
                params['exclude-tags'] = exclude_tags  # Single value case

        response = requests.get("https://api.spoonacular.com/recipes/random", params=params)
        if response.status_code != 200:
            return "There was an error while retrieving random recipes."

        data = response.json()
        if data and 'recipes' in data:
            recipes = data['recipes']
            recipe_messages = [f"Title: {recipe['title']}\nLink: {recipe['sourceUrl']}" for recipe in recipes]
            return "Random Recipe:\n" + "\n\n".join(recipe_messages)
        else:
            return "I couldn't find any random recipes."

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        number = next(tracker.get_latest_entity_values("number"), None)
        #include_tags = list(tracker.get_latest_entity_values("include_tags"))
        #exclude_tags = list(tracker.get_latest_entity_values("exclude_tags"))
        include_tags = tracker.get_slot("include_tags")
        exclude_tags = tracker.get_slot("exclude_tags")

        # Convert number from words to digits if necessary
        if number:
            try:
                number = w2n.word_to_num(number)
            except ValueError:
                try:
                    number = int(number)
                except ValueError:
                    number = None

        # Ensure include_tags and exclude_tags are lists or single values
        if include_tags and not isinstance(include_tags, list):
            include_tags = [include_tags]
        if exclude_tags and not isinstance(exclude_tags, list):
            exclude_tags = [exclude_tags]

        recipe_info = self.get_random_recipes(number=number, include_tags=include_tags, exclude_tags=exclude_tags)
        dispatcher.utter_message(text=recipe_info)
        
        return []

class ActionAnalyzeRecipeNutrition(Action):

    def name(self) -> Text:
        return "action_analyze_recipe_nutrition"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        recipe_id = tracker.get_slot("recipe_id")
        recipe_name = tracker.get_slot("recipe_name")

        # Check if the recipe_id or recipe_name slot is provided
        if not recipe_id and not recipe_name:
            dispatcher.utter_message(text="Please provide a recipe ID or recipe name to get the nutritional information.")
            return []

        # If recipe_name is provided but not recipe_id, perform a search to get the recipe_id
        if not recipe_id and recipe_name:
            search_response = requests.get(
                f"https://api.spoonacular.com/recipes/complexSearch?query={recipe_name}&apiKey={API_KEY}"
            )
            if search_response.status_code != 200:
                dispatcher.utter_message(text="There was an error while searching for the recipe.")
                return []

            search_data = search_response.json()
            if search_data and 'results' in search_data and search_data['results']:
                recipe_id = search_data['results'][0]['id']
            else:
                dispatcher.utter_message(text=f"I couldn't find any recipe with the name '{recipe_name}'.")
                return []

        # Call the API to get nutritional information
        response = requests.get(
            f"https://api.spoonacular.com/recipes/{recipe_id}/nutritionWidget.json?apiKey={API_KEY}"
        )
        if response.status_code != 200:
            if response.status_code == 404:
                dispatcher.utter_message(text="The recipe was not found.")
            else:
                dispatcher.utter_message(text="There was an error while retrieving the nutritional information.")
            return []

        data = response.json()
        if data:
            nutrition_info = (
                f"Calories: {data.get('calories', 'N/A')}\n"
                f"Carbs: {data.get('carbs', 'N/A')}\n"
                f"Fat: {data.get('fat', 'N/A')}\n"
                f"Protein: {data.get('protein', 'N/A')}"
            )
            dispatcher.utter_message(text="Nutritional Information:\n" + nutrition_info)
        else:
            dispatcher.utter_message(text="I couldn't retrieve nutritional information for that recipe.")

        return [SlotSet("recipe_id", recipe_id), SlotSet("recipe_name", recipe_name)]


class ActionGetDishPairingForWine(Action):

    def name(self) -> Text:
        return "action_get_dish_pairing_for_wine"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        wine_type = tracker.get_slot("wine_type")
        #wine_type = tracker.get_latest_entity_values("exclude")

        # Check if the wine_type slot is provided
        if not wine_type:
            dispatcher.utter_message(text="Please specify the type of wine for which you need pairing suggestions.")
            return []

        # Call the API to get dish pairing suggestions
        response = requests.get(
            f"https://api.spoonacular.com/food/wine/dishes?wine={wine_type}&apiKey={API_KEY}"
        )

        # Handle the API response
        if response.status_code == 200:
            data = response.json()
            pairing_text = data.get('text', "I couldn't find any pairing suggestions for that wine.")
            dispatcher.utter_message(text=pairing_text)
        else:
            dispatcher.utter_message(text="There was an error while retrieving pairing suggestions.")
        
        return []

# List of valid diets
valid_diets = [
    "gluten free", "ketogenic", "vegetarian", "lacto-vegetarian", 
    "ovo-vegetarian", "vegan", "pescetarian", "paleo", 
    "primal", "whole30"
]

def generate_meal_plan(time_frame=None, target_calories=2000, diet=None, exclude=None):
    # Default to 'day' if time_frame is not provided or is invalid
    if not time_frame:
        time_frame = 'day'
    else:
        # Convert numeric time_frame to 'day' or 'week'
        try:
            time_frame = int(time_frame)
            if time_frame == 1:
                time_frame = 'day'
            elif time_frame >= 7:
                time_frame = 'week'
            else:
                time_frame = 'day'  # Default to day for any other number
        except ValueError:
            time_frame = time_frame.lower()
            if time_frame not in ['day', 'week']:
                time_frame = 'day'  # Default to day for any invalid string
    
    # Check if the provided diet is valid
    if diet and diet.lower() not in valid_diets:
        print(f"The diet '{diet}' is not valid. Defaulting to a balanced diet.")
        diet = None  # Default to balanced diet if the provided diet is not valid
    
    # Base URL for the API endpoint
    url = "https://api.spoonacular.com/mealplanner/generate"
    
    # Parameters for the API request
    params = {
        'apiKey': API_KEY,
        'timeFrame': time_frame,
        'targetCalories': target_calories
    }
    
    if diet:
        params['diet'] = diet
    #if exclude:
        #params['exclude'] = exclude
    if exclude:
        if isinstance(exclude, list):
            exclude = ','.join(exclude)
        params['exclude'] = exclude

    # Call the API to generate meal plans
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        # Debugging purposes
        # print("Response Data:", data)

        if time_frame == 'day':
            if 'meals' in data:
                meal_plan = "\n".join([f"Meal {i+1}: {meal['title']} - {meal['sourceUrl']}" for i, meal in enumerate(data['meals'])])
                return f"Here's a {diet if diet else 'balanced'} meal plan for the day:\n{meal_plan}"
            else:
                return "I couldn't generate a meal plan."
        
        elif time_frame == 'week':
            if 'week' in data:
                week_data = data['week']
                meal_plan = ""
                for day, day_data in week_data.items():
                    meals = day_data.get('meals', [])
                    meal_plan += f"{day.capitalize()}:\n"
                    for meal in meals:
                        meal_plan += f"  - {meal['title']} - {meal['sourceUrl']}\n"
                return f"Here's a {diet if diet else 'balanced'} meal plan for the week:\n{meal_plan}"
            else:
                return "I couldn't generate a meal plan."
        
        else:
            return "Invalid time frame. Please use 'day' or 'week'."
    
    else:
        return f"Failed to retrieve meal plan. Status code: {response.status_code}\nResponse: {response.text}"

class ActionGenerateMealPlan(Action):

    def name(self) -> str:
        return "action_generate_meal_plans"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> list:
        
        time_frame = tracker.get_slot("time_frame")
        target_calories = tracker.get_slot("target_calories")
        diet = tracker.get_slot("diet")
        #exclude = tracker.get_slot("exclude")
        exclude_entities = tracker.get_latest_entity_values("exclude")
        exclude = [entity for entity in exclude_entities]

        meal_plan = generate_meal_plan(time_frame, target_calories, diet, exclude)
        
        dispatcher.utter_message(text=meal_plan)

        return [SlotSet("time_frame", time_frame), SlotSet("target_calories", target_calories), SlotSet("diet", diet), SlotSet("exclude", exclude)]


