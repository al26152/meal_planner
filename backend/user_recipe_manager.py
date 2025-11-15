"""
User Recipe Manager
Handles CRUD operations for user-curated recipes
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class UserRecipeManager:
    """Manages user-curated recipes storage and retrieval."""

    def __init__(self, data_dir: str = "data"):
        """Initialize the recipe manager.

        Args:
            data_dir: Directory where user_recipes.json is stored
        """
        self.data_file = Path(data_dir) / "user_recipes.json"
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create user_recipes.json if it doesn't exist."""
        if not self.data_file.exists():
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            self._save({
                "recipes": [],
                "version": "1.0"
            })

    def _load(self) -> Dict:
        """Load recipes from file."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"recipes": [], "version": "1.0"}

    def _save(self, data: Dict):
        """Save recipes to file."""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_recipe(self,
                   name: str,
                   ingredients: List[Dict],
                   instructions: str,
                   source: str = "manual",
                   source_url: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   notes: Optional[str] = None) -> Dict:
        """Add a new recipe to the library.

        Args:
            name: Recipe name
            ingredients: List of ingredient dicts with keys: name, quantity, unit
            instructions: Cooking instructions
            source: Where recipe came from (manual, youtube, website, etc.)
            source_url: URL to original recipe (if applicable)
            tags: List of tags (cuisine, diet, difficulty, etc.)
            notes: User notes about the recipe

        Returns:
            Created recipe dict with ID
        """
        data = self._load()

        recipe = {
            "id": str(uuid.uuid4()),
            "name": name,
            "ingredients": ingredients,
            "instructions": instructions,
            "source": source,
            "source_url": source_url,
            "tags": tags or [],
            "notes": notes or "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        data["recipes"].append(recipe)
        self._save(data)
        return recipe

    def get_recipe(self, recipe_id: str) -> Optional[Dict]:
        """Get a recipe by ID.

        Args:
            recipe_id: Recipe UUID

        Returns:
            Recipe dict or None if not found
        """
        data = self._load()
        for recipe in data["recipes"]:
            if recipe["id"] == recipe_id:
                return recipe
        return None

    def get_all_recipes(self) -> List[Dict]:
        """Get all recipes.

        Returns:
            List of recipe dicts
        """
        data = self._load()
        return data.get("recipes", [])

    def search_recipes(self,
                      query: Optional[str] = None,
                      tags: Optional[List[str]] = None,
                      ingredients: Optional[List[str]] = None) -> List[Dict]:
        """Search recipes by name, tags, or required ingredients.

        Args:
            query: Search string to match in recipe name
            tags: List of tags to match (AND logic - recipe must have all)
            ingredients: List of ingredients to match (recipe must contain at least one)

        Returns:
            List of matching recipes
        """
        data = self._load()
        recipes = data.get("recipes", [])

        # Filter by name query
        if query:
            query_lower = query.lower()
            recipes = [r for r in recipes if query_lower in r["name"].lower()]

        # Filter by tags (recipe must have all specified tags)
        if tags:
            tags_lower = [t.lower() for t in tags]
            recipes = [r for r in recipes
                      if all(any(t.lower() == rt.lower() for rt in r.get("tags", []))
                            for t in tags_lower)]

        # Filter by ingredients (recipe must contain at least one)
        if ingredients:
            ingredient_names = [ing.lower() for ing in ingredients]
            filtered = []
            for recipe in recipes:
                recipe_ing_names = [ing["name"].lower() for ing in recipe.get("ingredients", [])]
                if any(ing in recipe_ing_names for ing in ingredient_names):
                    filtered.append(recipe)
            recipes = filtered

        return recipes

    def update_recipe(self, recipe_id: str, **kwargs) -> Optional[Dict]:
        """Update a recipe.

        Args:
            recipe_id: Recipe UUID
            **kwargs: Fields to update (name, ingredients, instructions, tags, notes, etc.)

        Returns:
            Updated recipe dict or None if not found
        """
        data = self._load()

        for i, recipe in enumerate(data["recipes"]):
            if recipe["id"] == recipe_id:
                # Update allowed fields
                allowed_fields = {"name", "ingredients", "instructions", "tags", "notes", "source", "source_url"}
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        recipe[key] = value

                recipe["updated_at"] = datetime.now().isoformat()
                data["recipes"][i] = recipe
                self._save(data)
                return recipe

        return None

    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe.

        Args:
            recipe_id: Recipe UUID

        Returns:
            True if deleted, False if not found
        """
        data = self._load()

        for i, recipe in enumerate(data["recipes"]):
            if recipe["id"] == recipe_id:
                data["recipes"].pop(i)
                self._save(data)
                return True

        return False

    def get_recipes_by_tag(self, tag: str) -> List[Dict]:
        """Get all recipes with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of recipes with this tag
        """
        tag_lower = tag.lower()
        recipes = self.get_all_recipes()
        return [r for r in recipes
               if any(t.lower() == tag_lower for t in r.get("tags", []))]

    def get_recipes_with_ingredients(self, ingredients: List[str]) -> List[Dict]:
        """Get recipes that use specified ingredients.

        Args:
            ingredients: List of ingredient names

        Returns:
            List of recipes containing these ingredients
        """
        ingredient_names = [ing.lower() for ing in ingredients]
        recipes = self.get_all_recipes()

        matching = []
        for recipe in recipes:
            recipe_ing_names = [ing["name"].lower() for ing in recipe.get("ingredients", [])]
            # Count how many ingredients match
            matches = sum(1 for ing in ingredient_names if ing in recipe_ing_names)
            if matches > 0:
                # Add recipe with match count for sorting
                recipe_copy = recipe.copy()
                recipe_copy["_match_count"] = matches
                matching.append(recipe_copy)

        # Sort by number of matches (descending)
        matching.sort(key=lambda r: r["_match_count"], reverse=True)
        return matching
