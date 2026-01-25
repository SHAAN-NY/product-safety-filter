#Complete project so far

#Libraries
import sqlite3
import hashlib
from collections import deque
from abc import ABC, abstractmethod
import requests
from googletrans import Translator




# Database management 
class Database:
    def __init__(self, db_name="users.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Users table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                email TEXT UNIQUE NOT NULL,
                                password TEXT NOT NULL
                            )''')
        # Recipes table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS recipes (
                                recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                instructions TEXT
                            )''')
        # User-Recipe linking table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS user_recipes (
                                user_id INTEGER,
                                recipe_id INTEGER,
                                FOREIGN KEY (user_id) REFERENCES users(id),
                                FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id)
                            )''')
        self.conn.commit()

    def close(self):
        self.conn.close()

# Abstract Recipe Component Interface 
class RecipeComponent(ABC):
    @abstractmethod
    def display(self):
        pass

# Recipe Step, demonstrating inheritance and polymorphism
class RecipeStep(RecipeComponent):
    def __init__(self, step_number, instruction):
        self.step_number = step_number
        self.instruction = instruction

    def display(self):
        return f"Step {self.step_number}: {self.instruction}"

# Recipe class
class Recipe:
    def __init__(self, name, db: Database):
        self.name = name
        self.instructions_queue = deque()
        self.db = db

    def add_step(self, instruction):
        step = RecipeStep(len(self.instructions_queue) + 1, instruction)
        self.instructions_queue.append(step)

    def save_to_db(self, user_id):
        # Combine instructions
        instructions_text = "\n".join([step.display() for step in self.instructions_queue])
        self.db.cursor.execute("INSERT INTO recipes (name, instructions) VALUES (?, ?)", (self.name, instructions_text))
        recipe_id = self.db.cursor.lastrowid
        self.db.cursor.execute("INSERT INTO user_recipes (user_id, recipe_id) VALUES (?, ?)", (user_id, recipe_id))
        self.db.conn.commit()
        print(f"Recipe '{self.name}' created with Recipe ID {recipe_id}.")

# User class, handling sign-up, login, and recipes
class User:
    def __init__(self, db: Database):
        self.db = db
        self.user_id = None

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def sign_up(self, email, password):
        hashed_password = self.hash_password(password)
        try:
            self.db.cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
            self.db.conn.commit()
            print(f"User signed up successfully! Your ID is {self.db.cursor.lastrowid}.")
        except sqlite3.IntegrityError:
            print("Error: Username already exists.")

    def log_in(self, email, password):
        hashed_password = self.hash_password(password)
        self.db.cursor.execute("SELECT id FROM users WHERE email = ? AND password = ?", (email, hashed_password))
        user = self.db.cursor.fetchone()

        if user:
            self.user_id = user[0]
            print(f"Login successful! Welcome, user {self.user_id}.")
            return True
        else:
            print("Error: Incorrect username or password.")
            return False

    def create_recipe(self, name, num_steps):
        recipe = Recipe(name, self.db)
        for step_num in range(1, num_steps + 1):
            instruction = input(f"Step {step_num}: ")
            recipe.add_step(instruction)
        recipe.save_to_db(self.user_id)

    def view_recipes(self):
        self.db.cursor.execute('''SELECT r.name 
                                  FROM recipes r
                                  JOIN user_recipes ur ON r.recipe_id = ur.recipe_id
                                  WHERE ur.user_id = ?''', (self.user_id,))
        recipes = self.db.cursor.fetchall()

        if recipes:
            print("\nYour Recipes:")
            for recipe in recipes:
                print(f"- {recipe[0]}")  # Display only recipe names

            while True:
                recipe_name = input("\nEnter the recipe name to view details (or type 'exit' to go back): ").strip()
                if recipe_name.lower() == "exit":
                    break

                # Fetch and display the details of the specified recipe
                self.db.cursor.execute('''SELECT r.recipe_id, r.name, r.instructions 
                                          FROM recipes r
                                          JOIN user_recipes ur ON r.recipe_id = ur.recipe_id
                                          WHERE ur.user_id = ? AND r.name = ?''', (self.user_id, recipe_name))
                recipe_details = self.db.cursor.fetchone()

                if recipe_details:
                    print(f"\nRecipe ID: {recipe_details[0]}")
                    print(f"Recipe Name: {recipe_details[1]}")
                    print(f"Instructions: {recipe_details[2]}")
                else:
                    print("Recipe not found. Please try again.")
        else:
            print("No recipes found.")

# Menu class to display options
class Menu:
    def __init__(self, user: User):
        self.user = user

    def display(self):
        while True:
            print("\nOptions:")
            print("1. Create Recipe")
            print("2. View Recipes")
            print("3. Food Scanner")
            print("4. Log Out")

            choice = input("Enter your choice: ")

            if choice == '1':
                name = input("What will you call your recipe?: ")
                try:
                    num_steps = int(input("How many steps will it have?: "))
                    if num_steps <= 0:
                        print("Please enter a positive number for steps.")
                        continue
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    continue
                self.user.create_recipe(name, num_steps)

            elif choice == '2':
                self.user.view_recipes()

            elif choice == '3':
                interface = ProductInterface()
                interface.run()

            elif choice == '4':
                print("Logging out...")
                break
            else:
                print("Invalid choice. Please try again.")

# Main program
def main():
    db = Database()
    user = User(db)
    
    while True:
        print("\nMenu:")
        print("1. Sign Up")
        print("2. Log In")
        print("3. Exit")
        

        choice = input("Enter your choice: ")

        if choice == '1':
            email = input("Enter your username here: ")
            password = input("Enter your password here: ")
            user.sign_up(email, password)
        
        elif choice == '2':
            email = input("Enter your username here: ")
            password = input("Enter your password here: ")
            if user.log_in(email, password):
                menu = Menu(user)
                menu.display()
        
        elif choice == '3':
            print("Exiting...")
            db.close()
            break

        else:
            print("Invalid choice. Please try again.")

# Interface for translatable objects
class Translatable(ABC):
    @abstractmethod
    def translate(self, text):
        pass

# Translator service using composition
class TranslatorService(Translatable):
    def __init__(self):
        self.translator = Translator()

    def translate(self, text):
        try:
            return self.translator.translate(text, dest='en').text
        except Exception as e:
            print(f"Translation error: {e}")
            return text  # Returns original if translation fails

# Base class for a product
class Product:
    def __init__(self, barcode, name=None, ingredients=None, nutrients=None):
        self.barcode = barcode
        self.name = name
        self.ingredients = ingredients or []
        self.nutrients = nutrients or {}

    def display(self):
        print(f"Product Name: {self.name}")
        print("Ingredients:")
        for ingredient in self.ingredients:
            print(ingredient)
        print("\nNutritional Information:")
        for nutrient, amount in self.nutrients.items():
            print(f"{nutrient}: {amount}")

# Specialized class for translatable products
class TranslatableProduct(Product):
    def __init__(self, barcode, name=None, ingredients=None, nutrients=None, translator=None):
        super().__init__(barcode, name, ingredients, nutrients)
        self.translator = translator or TranslatorService()

    def translate_details(self):
        self.name = self.translator.translate(self.name)
        self.ingredients = [self.translator.translate(ingredient) for ingredient in self.ingredients]
        self.nutrients = {self.translator.translate(nutrient): amount for nutrient, amount in self.nutrients.items()}

# Fetcher class for products
class ProductFetcher: 
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org/api/v0/product"

    def fetch_product_details(self, barcode):
        response = requests.get(f"{self.base_url}/{barcode}.json")
        if response.status_code != 200:
            print("Failed to retrieve product details.")
            return None

        data = response.json()
        product_data = data.get("product", {})
        
        # Extract name, ingredients, and nutrients
        name = product_data.get("product_name", "No Name Found")
        ingredients_data = product_data.get("ingredients_text", "")
        nutrients_data = product_data.get("nutriments", {})

        # Process ingredients list
        ingredients_list = ingredients_data.split(", ")

        # Process nutrients dictionary
        nutrients = {
            "Energy": f"{nutrients_data.get('energy-kcal_value', 'N/A')} kcal",
            "Fat": f"{nutrients_data.get('fat_value', 'N/A')}g",
            "Carbohydrates": f"{nutrients_data.get('carbohydrates_value', 'N/A')}g",
            "Protein": f"{nutrients_data.get('proteins_value', 'N/A')}g"
        }

        return TranslatableProduct(barcode=barcode, name=name, ingredients=ingredients_list, nutrients=nutrients)

# Abstract Filter base class
class Filter(ABC):
    @abstractmethod
    def apply(self, product):
        pass

# Base class for all filters that involve specific terms
class TermFilter(Filter):
    def __init__(self, term):
        self.term = term.lower()

    @abstractmethod
    def apply(self, product):
        pass

# Specialized allergen filter
class AllergenFilter(TermFilter):
    def apply(self, product):
        has_allergen = any(self.term in ingredient.lower() for ingredient in product.ingredients)
        if has_allergen:
            print(f"Warning: Product contains allergen '{self.term}'!")
        return has_allergen

# Specialized ingredient filter
class IngredientFilter(TermFilter):
    def apply(self, product):
        has_ingredient = any(self.term in ingredient.lower() for ingredient in product.ingredients)
        if has_ingredient:
            print(f"Warning: Product contains ingredient '{self.term}'!")
        return has_ingredient

# Base class for filters with quantitative limits
class LimitFilter(Filter):
    def __init__(self, max_value):
        self.max_value = max_value

    @abstractmethod
    def apply(self, product):
        pass

# Specialized calorie filter
class CalorieFilter(LimitFilter):
    def apply(self, product):
        try:
            calories = int(product.nutrients.get("Energy", "0 kcal").split()[0])
            if calories > self.max_value:
                print(f"Warning: Product exceeds {self.max_value} kcal limit!")
                return True
        except ValueError:
            print("Calorie data is not available.")
        return False

# Specialized nutrient filter
class NutrientFilter(LimitFilter):
    def __init__(self, nutrient, max_value):
        super().__init__(max_value)
        self.nutrient = nutrient.lower()

    def apply(self, product):
        nutrient_value = product.nutrients.get(self.nutrient.title(), "0g").split()[0]
        try:
            nutrient_value = float(nutrient_value)
            if nutrient_value > self.max_value:
                print(f"Warning: {self.nutrient.title()} exceeds {self.max_value}g limit!")
                return True
        except ValueError:
            print(f"{self.nutrient.title()} data is not available.")
        return False

# Controller for managing products and filters
class ProductController:
    def __init__(self):
        self.fetcher = ProductFetcher()

    def search_and_translate_product(self, barcode, filters=[]):
        product = self.fetcher.fetch_product_details(barcode)
        
        if product is None:
            print("No product found for the given barcode.")
            return
        
        if isinstance(product, TranslatableProduct):
            product.translate_details()

        for f in filters:
            f.apply(product)
        
        product.display()

# Class where user enters barcode and any optional filters
# Filtering takes place in other classes
class ProductInterface:
    def __init__(self):
        self.controller = ProductController()

    def run(self):
        barcode = input("Enter the barcode of the product you want to search: ")
        filters = self.create_filters()
        self.controller.search_and_translate_product(barcode, filters)

    def create_filters(self):
        filters = []
        if self.confirm("Do you want to apply an allergen filter?"):
            allergen = input("Enter the allergen to check for: ")
            filters.append(AllergenFilter(allergen))
        
        if self.confirm("Do you want to apply an ingredient filter?"):
            ingredient = input("Enter the ingredient to check for: ")
            filters.append(IngredientFilter(ingredient))
        
        if self.confirm("Do you want to apply a calorie filter?"):
            max_calories = int(input("Enter the maximum calories: "))
            filters.append(CalorieFilter(max_calories))

        if self.confirm("Do you want to apply a nutrient filter?"):
            nutrient = input("Enter the nutrient to check for (e.g., 'Protein', 'Fat'): ")
            max_value = float(input(f"Enter the maximum {nutrient} amount in grams: "))
            filters.append(NutrientFilter(nutrient, max_value))

        return filters

    @staticmethod
    def confirm(prompt):
        return input(f"{prompt} (yes/no) ").strip().lower() == 'yes'

# Running the interface
# This is where the program starts running.
main()