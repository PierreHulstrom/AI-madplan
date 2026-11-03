"""
Modul til sammenlægning af ingredienser og beregning af indkøbsliste og Netto-priser.
"""

import math
import re
from typing import List, Dict, Any, Tuple
from db import match_ingredient_to_netto, normalize_text


def parse_and_convert_unit(amount: float, unit: str) -> Tuple[float, str]:
    """
    Konverterer enheder til standard enheder (g, ml, stk, dåse osv.) for konsistent aggregering.
    """
    unit_clean = unit.lower().strip()
    
    # Vægt
    if unit_clean in ["kg", "kilo"]:
        return amount * 1000.0, "g"
    elif unit_clean in ["g", "gram"]:
        return amount, "g"
        
    # Rumfang
    elif unit_clean in ["l", "liter"]:
        return amount * 1000.0, "ml"
    elif unit_clean in ["dl", "deciliter"]:
        return amount * 100.0, "ml"
    elif unit_clean in ["cl", "centiliter"]:
        return amount * 10.0, "ml"
    elif unit_clean in ["spsk", "spiseske", "spsk."]:
        return amount * 15.0, "ml"
    elif unit_clean in ["tsk", "teske", "tsk."]:
        return amount * 5.0, "ml"
    elif unit_clean in ["ml", "milliliter"]:
        return amount, "ml"
        
    # Antal
    elif unit_clean in ["stk", "stk.", "styk", "stykker"]:
        return amount, "stk"
    elif unit_clean in ["fed", "hvidløgsfed"]:
        # Hvidløgsfed: ca 0.33 stk hvidløg eller bare fed
        return amount, "fed"
    elif unit_clean in ["dåse", "dåser", "ds"]:
        return amount, "dåse"
    elif unit_clean in ["pakke", "pakker", "pk"]:
        return amount, "pakke"
    elif unit_clean in ["pose", "poser"]:
        return amount, "pose"
    elif unit_clean in ["bundt", "bdt"]:
        return amount, "bundt"

    return amount, unit_clean


def aggregate_meal_plan_ingredients(plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Samler alle ingredienser fra alle 7 dage i madplanen, fjerner dubletter,
    summerer mængder og slår priser op i Netto-kataloget.
    """
    days = plan_data.get("days", [])
    
    # Nøgle: Netto ID (hvis matchet) eller normaliseret navn
    aggregated_items: Dict[str, Dict[str, Any]] = {}

    for day in days:
        day_name = day.get("day_name", "Ukendt dag")
        meal_name = day.get("meal_name", "Ret")
        ingredients = day.get("ingredients", [])

        for ing in ingredients:
            raw_name = ing.get("name", "").strip()
            if not raw_name:
                continue

            try:
                raw_amount = float(ing.get("amount", 1))
            except (ValueError, TypeError):
                raw_amount = 1.0

            raw_unit = ing.get("unit", "stk").strip()
            norm_amount, norm_unit = parse_and_convert_unit(raw_amount, raw_unit)

            # Match mod Netto
            netto_match = match_ingredient_to_netto(raw_name, norm_unit)

            if netto_match:
                key = f"netto_{netto_match['id']}"
            else:
                norm_name = normalize_text(raw_name)
                key = f"custom_{norm_name}_{norm_unit}"

            if key not in aggregated_items:
                category = netto_match["category"] if netto_match else ing.get("category", "Kolonial")
                item_display_name = netto_match["name"] if netto_match else raw_name
                
                aggregated_items[key] = {
                    "key": key,
                    "name": item_display_name,
                    "original_name": raw_name,
                    "category": category,
                    "total_amount": 0.0,
                    "unit": norm_unit,
                    "used_in": [],
                    "netto_product": netto_match,
                    "is_matched": netto_match is not None
                }

            # Tilføj mængde
            # Tjek enhedskompatibilitet hvis allerede sat
            existing_unit = aggregated_items[key]["unit"]
            if existing_unit == norm_unit:
                aggregated_items[key]["total_amount"] += norm_amount
            elif existing_unit in ["g", "ml"] and norm_unit in ["g", "ml"]:
                aggregated_items[key]["total_amount"] += norm_amount
            else:
                # Hvis enhed afviger væsentligt (f.eks. stk vs gram), akkumulér separat eller konvertér
                aggregated_items[key]["total_amount"] += norm_amount

            used_str = f"{day_name} ({meal_name})"
            if used_str not in aggregated_items[key]["used_in"]:
                aggregated_items[key]["used_in"].append(used_str)

    # Beregn Netto-priser og antal pakker
    shopping_list = []

    for item in aggregated_items.values():
        total_qty = item["total_amount"]
        unit = item["unit"]
        netto_item = item["netto_product"]

        if netto_item:
            pkg_size = netto_item["package_size"]
            pkg_unit = netto_item["unit"]
            pkg_price = netto_item["price_dkk"]

            # Sammenlign enheder
            if unit == pkg_unit:
                packages_needed = math.ceil(total_qty / pkg_size) if pkg_size > 0 else 1
            elif unit == "fed" and pkg_unit == "stk":
                # 1 helt hvidløg har ca 10 fed
                packages_needed = math.ceil(total_qty / 10.0)
            elif unit == "dåse" and pkg_unit == "g":
                # standard dåse ca 400g
                packages_needed = math.ceil((total_qty * 400.0) / pkg_size)
            else:
                packages_needed = 1

            packages_needed = max(1, packages_needed)
            item_total_price = packages_needed * pkg_price
            
            # Format mængde pænt
            if unit == "g" and total_qty >= 1000:
                display_qty = f"{total_qty / 1000:.1f} kg".replace(".0", "")
            elif unit == "ml" and total_qty >= 1000:
                display_qty = f"{total_qty / 1000:.1f} L".replace(".0", "")
            else:
                # Heltal hvis muligt
                if total_qty.is_integer():
                    display_qty = f"{int(total_qty)} {unit}"
                else:
                    display_qty = f"{total_qty:.1f} {unit}"

            package_info = f"{packages_needed} x {netto_item['name']} ({netto_item['package_size']} {netto_item['unit']})"

            shopping_list.append({
                "name": item["name"],
                "category": item["category"],
                "recipe_amount": display_qty,
                "packages_needed": packages_needed,
                "netto_product_name": netto_item["name"],
                "unit_price_dkk": pkg_price,
                "total_price_dkk": round(item_total_price, 2),
                "package_info": package_info,
                "used_in": item["used_in"],
                "is_matched": True,
                "checked": False
            })
        else:
            # Ikke fundet i Netto-kataloget - lav et realistisk estimat
            est_price = 15.0  # Standard Netto gennemsnitspris for basisvare
            if total_qty.is_integer():
                display_qty = f"{int(total_qty)} {unit}"
            else:
                display_qty = f"{total_qty:.1f} {unit}"

            shopping_list.append({
                "name": item["name"],
                "category": item["category"],
                "recipe_amount": display_qty,
                "packages_needed": 1,
                "netto_product_name": f"{item['name']} (Estimeret vare)",
                "unit_price_dkk": est_price,
                "total_price_dkk": round(est_price, 2),
                "package_info": f"1 x {item['name']}",
                "used_in": item["used_in"],
                "is_matched": False,
                "checked": False
            })

    # Sortér efter kategori og dernæst navn
    category_order = {
        "Grønt & Frugt": 1,
        "Kød & Fisk": 2,
        "Mejeri & Køl": 3,
        "Brød & Bageri": 4,
        "Kolonial": 5,
        "Krydderier": 6,
        "Frost": 7,
        "Andet": 8
    }
    shopping_list.sort(key=lambda x: (category_order.get(x["category"], 9), x["name"]))

    return shopping_list


def calculate_total_shopping_price(shopping_list: List[Dict[str, Any]]) -> float:
    """Beregner den samlede pris for hele indkøbslisten."""
    total = sum(item["total_price_dkk"] for item in shopping_list)
    return round(total, 2)
