"""
Omfattende Unit Test Suite til Madplanlægger AI.
Designet til analyse og evaluering i studieprojekter om AI-assisteret softwareudvikling.

Dækker:
- Datavalidering med Pydantic modeller
- Enhedskonvertering og matematiske kanttilfælde (edge cases)
- Ingrediens-aggregering og dublet-eliminering
- Netto-katalog matching algoritme
- SQLite CRUD-operationer og dataintegritet
- Fejlhåndtering ved ugyldige input
"""

import unittest
import json
from pydantic import ValidationError

from models import Ingredient, DayPlan, MealPlanSchema, ShoppingItem, NettoProduct
from db import (
    init_db,
    get_connection,
    get_all_netto_products,
    match_ingredient_to_netto,
    add_netto_product,
    update_netto_product,
    save_meal_plan,
    get_all_saved_meal_plans,
    get_meal_plan,
    delete_meal_plan,
    normalize_text
)
from meal_planner import generate_demo_plan
from aggregator import (
    aggregate_meal_plan_ingredients,
    calculate_total_shopping_price,
    parse_and_convert_unit
)


class TestDataModels(unittest.TestCase):
    """Tester Pydantic datamodeller og input-validering."""

    def test_valid_ingredient(self):
        ing = Ingredient(name="Løg", amount=2.0, unit="stk", category="Grønt & Frugt")
        self.assertEqual(ing.name, "Løg")
        self.assertEqual(ing.amount, 2.0)

    def test_invalid_ingredient_amount(self):
        """Mængde skal være strengt større end 0."""
        with self.assertRaises(ValidationError):
            Ingredient(name="Løg", amount=-1.0, unit="stk")
        with self.assertRaises(ValidationError):
            Ingredient(name="Løg", amount=0.0, unit="stk")

    def test_valid_meal_plan_schema(self):
        plan_dict = generate_demo_plan(600, 4, [], ["Børnevenlig mad"])
        # Valider med Pydantic
        schema = MealPlanSchema(**plan_dict)
        self.assertEqual(len(schema.days), 7)
        self.assertEqual(schema.days[0].day_name, "Mandag")


class TestUnitConversionAndMath(unittest.TestCase):
    """Tester konvertering af måleenheder og kanttilfælde i mængdeberegning."""

    def test_weight_conversions(self):
        self.assertEqual(parse_and_convert_unit(1.5, "kg"), (1500.0, "g"))
        self.assertEqual(parse_and_convert_unit(500, "g"), (500.0, "g"))

    def test_volume_conversions(self):
        self.assertEqual(parse_and_convert_unit(1, "L"), (1000.0, "ml"))
        self.assertEqual(parse_and_convert_unit(2.5, "dl"), (250.0, "ml"))
        self.assertEqual(parse_and_convert_unit(2, "spsk"), (30.0, "ml"))
        self.assertEqual(parse_and_convert_unit(3, "tsk"), (15.0, "ml"))

    def test_discrete_units(self):
        self.assertEqual(parse_and_convert_unit(4, "stk"), (4.0, "stk"))
        self.assertEqual(parse_and_convert_unit(2, "dåser"), (2.0, "dåse"))
        self.assertEqual(parse_and_convert_unit(3, "fed"), (3.0, "fed"))


class TestAggregationAndDeduplication(unittest.TestCase):
    """Tester forretningslogikken for dubletfjernelse og pakkeberegning."""

    def test_aggregation_sums_quantities_across_days(self):
        """Tester at samme ingrediens brugt på dag 1 og dag 3 lægges korrekt sammen."""
        mock_plan = {
            "title": "Test Plan",
            "overview": "Test",
            "days": [
                {
                    "day_number": 1,
                    "day_name": "Mandag",
                    "meal_name": "Kødsovs",
                    "ingredients": [
                        {"name": "Hakket oksekød 8-12%", "amount": 400, "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Gule løg", "amount": 2, "unit": "stk", "category": "Grønt & Frugt"}
                    ]
                },
                {
                    "day_number": 2,
                    "day_name": "Tirsdag",
                    "meal_name": "Gullasch",
                    "ingredients": [
                        {"name": "Hakket oksekød 8-12%", "amount": 350, "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Gule løg", "amount": 1, "unit": "stk", "category": "Grønt & Frugt"}
                    ]
                }
            ]
        }
        shopping_list = aggregate_meal_plan_ingredients(mock_plan)
        
        # Der bør kun være 2 varelinjer i alt (oksekød og løg)
        self.assertEqual(len(shopping_list), 2)
        
        meat_item = next(it for it in shopping_list if "oksekød" in it["name"].lower())
        onion_item = next(it for it in shopping_list if "løg" in it["name"].lower())

        # Oksekød: 400g + 350g = 750g. Netto pakke er 500g. Bør kræve 2 pakker.
        self.assertEqual(meat_item["packages_needed"], 2)
        self.assertEqual(len(meat_item["used_in"]), 2)
        self.assertIn("Mandag", meat_item["used_in"][0])
        self.assertIn("Tirsdag", meat_item["used_in"][1])

        # Løg: 2 stk + 1 stk = 3 stk.
        self.assertIn("3 stk", onion_item["recipe_amount"])

    def test_unmatched_ingredient_fallback(self):
        """Tester at ukendte ingredienser håndteres yndefuldt med et estimat."""
        mock_plan = {
            "title": "Eksotisk Plan",
            "days": [
                {
                    "day_number": 1,
                    "day_name": "Mandag",
                    "meal_name": "Dragonfruit Salat",
                    "ingredients": [
                        {"name": "Eksotisk Dragefrugt Superfood", "amount": 2, "unit": "stk", "category": "Eksotisk"}
                    ]
                }
            ]
        }
        shopping_list = aggregate_meal_plan_ingredients(mock_plan)
        self.assertEqual(len(shopping_list), 1)
        item = shopping_list[0]
        self.assertFalse(item["is_matched"])
        self.assertGreater(item["total_price_dkk"], 0.0)


class TestDatabaseAndCatalog(unittest.TestCase):
    """Tester SQLite databasetilstand, forespørgsler og CRUD."""

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_netto_catalog_seeded(self):
        products = get_all_netto_products()
        self.assertGreaterEqual(len(products), 70, "Netto-kataloget bør have mindst 70 varer.")

    def test_text_normalization(self):
        self.assertEqual(normalize_text("  Hakket Oksekød 8-12%!  "), "hakket oksekød 8 12")
        self.assertEqual(normalize_text("LØG"), "løg")

    def test_add_and_update_catalog_item(self):
        new_id = add_netto_product(
            name="Test Kaffe",
            category="Kolonial",
            package_size=500,
            unit="g",
            price_dkk=45.50,
            keywords="kaffe, bønner, filterkaffe"
        )
        self.assertIsNotNone(new_id)

        # Match på nyt nøgleord
        match = match_ingredient_to_netto("filterkaffe", "g")
        self.assertIsNotNone(match)
        self.assertEqual(match["name"], "Test Kaffe")

        # Opdater
        update_netto_product(new_id, "Test Kaffe Mørkristet", "Kolonial", 500, "g", 49.95, "kaffe, mørkristet")
        match_updated = match_ingredient_to_netto("mørkristet", "g")
        self.assertIsNotNone(match_updated)
        self.assertEqual(match_updated["price_dkk"], 49.95)

    def test_meal_plan_lifecycle_and_cascade(self):
        """Tester Oprettelse, Læsning, Tilknytning til indkøbsliste og Sletning."""
        demo = generate_demo_plan(650, 4, [], ["Hurtig og nem (under 30 min)"])
        shopping_list = aggregate_meal_plan_ingredients(demo)
        total_price = calculate_total_shopping_price(shopping_list)

        plan_id = save_meal_plan(
            title="Studieprojekt Testplan",
            budget=650.0,
            people_count=4,
            allergies="Ingen",
            preferences="Hurtig mad",
            notes="Test",
            plan_dict=demo,
            total_estimated_price=total_price,
            shopping_list_items=shopping_list
        )
        self.assertIsNotNone(plan_id)

        # Hent og verificer
        fetched = get_meal_plan(plan_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "Studieprojekt Testplan")
        self.assertIsNotNone(fetched["shopping_list"])
        self.assertEqual(len(fetched["shopping_list"]["items"]), len(shopping_list))

        # Slet
        delete_meal_plan(plan_id)
        self.assertIsNone(get_meal_plan(plan_id))


if __name__ == "__main__":
    unittest.main()
