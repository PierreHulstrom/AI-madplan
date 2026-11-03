"""
Database modul til madplanlægning med SQLite.
Håndterer lokal Netto varekatalog, gemte madplaner og indkøbslister.
"""

import sqlite3
import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "madplan.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialiserer tabeller til madplan, indkøbslister og Netto-katalog."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Netto varekatalog
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS netto_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                package_size REAL NOT NULL,
                unit TEXT NOT NULL,
                price_dkk REAL NOT NULL,
                keywords TEXT NOT NULL
            )
        """)

        # Madplaner
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT NOT NULL,
                budget REAL NOT NULL,
                people_count INTEGER NOT NULL,
                allergies TEXT,
                preferences TEXT,
                notes TEXT,
                plan_json TEXT NOT NULL,
                total_estimated_price REAL DEFAULT 0.0
            )
        """)

        # Indkøbslister
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_plan_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT,
                items_json TEXT NOT NULL,
                total_price REAL NOT NULL,
                FOREIGN KEY (meal_plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE
            )
        """)

        conn.commit()

    seed_netto_catalog_if_empty()


def seed_netto_catalog_if_empty():
    """Seeder Netto varekataloget med realistiske danske dagligvarer og Netto-priser."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM netto_catalog")
        count = cursor.fetchone()["count"]

        if count > 0:
            return

        items = [
            # --- KØD & FISK ---
            ("Hakket oksekød 8-12%", "Kød & Fisk", 500, "g", 39.95, "hakket oksekød, oksekød, hakkekød, oksefars"),
            ("Hakket oksekød 4-7%", "Kød & Fisk", 400, "g", 38.50, "hakket oksekød magert, oksekød"),
            ("Hakket svinekød 8-12%", "Kød & Fisk", 500, "g", 27.95, "hakket svinekød, svinefars, flæskefars, svinekød"),
            ("Hakket kalv og flæsk", "Kød & Fisk", 500, "g", 32.95, "hakket kalv og flæsk, frikadellefars, kalv og flæsk"),
            ("Kyllingebrystfilet", "Kød & Fisk", 450, "g", 36.95, "kyllingebryst, kyllingebrystfilet, kylling, kyllingefilet"),
            ("Kyllingeinderfilet", "Kød & Fisk", 400, "g", 34.95, "kyllingeinderfilet, kyllingestrimler, kylling"),
            ("Hel kylling", "Kød & Fisk", 1300, "g", 49.95, "hel kylling, kylling"),
            ("Bacon i tern", "Kød & Fisk", 200, "g", 14.95, "bacon, bacontern, røget bacon"),
            ("Bacon i skiver", "Kød & Fisk", 150, "g", 15.95, "baconskiver, bacon"),
            ("Lakseportioner (2 stk)", "Kød & Fisk", 250, "g", 42.95, "laks, laksefilet, laksebøffer, fersk laks"),
            ("Torskefilet", "Kød & Fisk", 300, "g", 45.00, "torsk, torskefilet, hvid fisk"),
            ("Kogepølser / Wienerpølser", "Kød & Fisk", 400, "g", 24.95, "pølser, wienerpølser, brunchpølser"),
            ("Medisterpølse", "Kød & Fisk", 500, "g", 29.95, "medister, medisterpølse"),
            ("Dåsetun i vand", "Kød & Fisk", 160, "g", 10.95, "tun, dåsetun, tun i vand, tunfisk"),
            ("Kødboller / Melboller (frost)", "Kød & Fisk", 400, "g", 23.95, "kødboller, suppeboller"),

            # --- GRØNT & FRUGT ---
            ("Kartofler (danske)", "Grønt & Frugt", 1500, "g", 16.95, "kartofler, kartoffel, bagekartofler"),
            ("Søde kartofler", "Grønt & Frugt", 800, "g", 18.95, "sød kartoffel, søde kartofler"),
            ("Gulerødder", "Grønt & Frugt", 1000, "g", 12.95, "gulerødder, gulerod"),
            ("Gule løg i net", "Grønt & Frugt", 1000, "g", 12.50, "løg, gule løg, madløg, zittauerløg"),
            ("Rødløg", "Grønt & Frugt", 500, "g", 11.95, "rødløg, røde løg"),
            ("Hvidløg (3 stk)", "Grønt & Frugt", 3, "stk", 10.95, "hvidløg, hvidløgsfed"),
            ("Tomater i bakke", "Grønt & Frugt", 500, "g", 14.95, "tomater, tomat, modne tomater"),
            ("Cherrytomater", "Grønt & Frugt", 250, "g", 12.95, "cherrytomater, små tomater"),
            ("Agurk", "Grønt & Frugt", 1, "stk", 8.95, "agurk, frisk agurk"),
            ("Rød peberfrugt", "Grønt & Frugt", 2, "stk", 14.95, "peberfrugt, rød peber, snackpeber"),
            ("Peberfrugt mix (3 stk)", "Grønt & Frugt", 3, "stk", 18.95, "peberfrugt, peberfrugter"),
            ("Iceberg salat", "Grønt & Frugt", 1, "stk", 11.95, "iceberg, salathoved, salat"),
            ("Frisk spinat", "Grønt & Frugt", 200, "g", 14.95, "spinat, babyspinat, frisk spinat"),
            ("Broccoli", "Grønt & Frugt", 400, "g", 13.95, "broccoli, frisk broccoli"),
            ("Blomkål", "Grønt & Frugt", 1, "stk", 17.95, "blomkål"),
            ("Porrer (3 stk)", "Grønt & Frugt", 3, "stk", 15.95, "porrer, porre"),
            ("Champignon / Marksvampe", "Grønt & Frugt", 250, "g", 12.95, "champignon, svampe, brune champignon"),
            ("Squash / Zucchini", "Grønt & Frugt", 1, "stk", 9.95, "squash, zucchini, courgette"),
            ("Spidskål", "Grønt & Frugt", 1, "stk", 16.95, "spidskål, sommerkål"),
            ("Hvidkål", "Grønt & Frugt", 1, "stk", 15.00, "hvidkål"),
            ("Citroner (3 stk)", "Grønt & Frugt", 3, "stk", 12.95, "citron, citronsaft, citroner"),
            ("Lime (3 stk)", "Grønt & Frugt", 3, "stk", 11.95, "lime, limesaft"),
            ("Avocado (2 stk)", "Grønt & Frugt", 2, "stk", 19.95, "avocado, avokado"),
            ("Ingefær (frisk)", "Grønt & Frugt", 150, "g", 9.95, "ingefær, frisk ingefær"),
            ("Frisk chili", "Grønt & Frugt", 50, "g", 8.95, "chili, frisk chili, rød chili"),
            ("Bananer", "Grønt & Frugt", 5, "stk", 15.00, "banan, bananer"),
            ("Æbler (pose)", "Grønt & Frugt", 1000, "g", 17.95, "æbler, æble"),
            ("Frisk basilikum i potte", "Grønt & Frugt", 1, "stk", 14.95, "basilikum, frisk basilikum, krydderurte"),
            ("Frisk persille i potte", "Grønt & Frugt", 1, "stk", 14.95, "persille, bredbladet persille, kruspersille"),

            # --- MEJERI & KØL ---
            ("Letmælk", "Mejeri & Køl", 1000, "ml", 13.50, "letmælk, mælk"),
            ("Sødmælk", "Mejeri & Køl", 1000, "ml", 14.25, "sødmælk, mælk"),
            ("Minimælk", "Mejeri & Køl", 1000, "ml", 13.25, "minimælk, mælk"),
            ("Madlavningsfløde 18%", "Mejeri & Køl", 250, "ml", 10.95, "madlavningsfløde, fløde 18%, madfløde"),
            ("Piskefløde 38%", "Mejeri & Køl", 250, "ml", 14.95, "piskefløde, fløde"),
            ("Creme Fraiche 18%", "Mejeri & Køl", 250, "g", 11.95, "creme fraiche, cremefraiche"),
            ("Smørbar (Lurpak/Kærgården)", "Mejeri & Køl", 200, "g", 21.95, "smør, smørbar, kærgården, stegesmør"),
            ("Rigtigt Smør", "Mejeri & Køl", 200, "g", 23.95, "smør, lurpak smør, bagesmør"),
            ("Revet Mozzarella", "Mejeri & Køl", 200, "g", 16.95, "revet mozzarella, mozzarella, pizzaost, revet ost"),
            ("Revet Gouda / Gratineringsost", "Mejeri & Køl", 200, "g", 16.95, "revet ost, gratineringsost, gouda"),
            ("Parmesan (stykke)", "Mejeri & Køl", 150, "g", 27.95, "parmesan, parmigiano, revet parmesan"),
            ("Feta / Salattern", "Mejeri & Køl", 150, "g", 12.95, "feta, salattern, hvid ost"),
            ("Friske Æg (10 stk M/L)", "Mejeri & Køl", 10, "stk", 24.95, "æg, hønseæg, friske æg"),
            ("Yoghurt Naturel", "Mejeri & Køl", 1000, "ml", 16.95, "yoghurt, yoghurt naturel, græsk yoghurt"),
            ("Flødeost Naturel", "Mejeri & Køl", 200, "g", 13.95, "flødeost, philadelphia, naturel ost"),
            ("Plantemælk (Havredrik)", "Mejeri & Køl", 1000, "ml", 16.95, "havremælk, havredrik, plantemælk"),

            # --- KOLONIAL & TØRVARER ---
            ("Hakkede tomater (dåse)", "Kolonial", 400, "g", 7.95, "hakkede tomater, dåsetomater, flåede tomater"),
            ("Passata / Tomatpassata", "Kolonial", 500, "g", 9.95, "passata, purerede tomater, tomatsauce"),
            ("Tomatpuré", "Kolonial", 140, "g", 6.50, "tomatpuré, tomatpure"),
            ("Spaghetti", "Kolonial", 500, "g", 10.95, "spaghetti, pasta"),
            ("Penne / Skruer pasta", "Kolonial", 500, "g", 10.95, "pasta, penne, pastaskruer, fusilli"),
            ("Fuldkornspasta", "Kolonial", 500, "g", 12.95, "fuldkornspasta, fuldkornsspaghetti"),
            ("Lasagneplader", "Kolonial", 500, "g", 14.95, "lasagneplader, pasta til lasagne"),
            ("Basmatiris", "Kolonial", 1000, "g", 19.95, "ris, basmatiris, hvide ris"),
            ("Jasminris", "Kolonial", 1000, "g", 18.95, "ris, jasminris"),
            ("Grødris", "Kolonial", 500, "g", 11.95, "grødris, risgrød"),
            ("Kokosmælk (dåse)", "Kolonial", 400, "ml", 11.95, "kokosmælk, coconut milk"),
            ("Kidneybønner (dåse)", "Kolonial", 400, "g", 8.95, "kidneybønner, røde bønner, bønner"),
            ("Kikærter (dåse)", "Kolonial", 400, "g", 8.95, "kikærter, dåsekikærter"),
            ("Sorte bønner (dåse)", "Kolonial", 400, "g", 8.95, "sorte bønner"),
            ("Hvedemel", "Kolonial", 1000, "g", 10.95, "hvedemel, mel"),
            ("Havregryn (finvalsede)", "Kolonial", 1000, "g", 11.95, "havregryn, gryn"),
            ("Rapsolie", "Kolonial", 1000, "ml", 18.95, "rapsolie, stegeolie, madolie"),
            ("Olivenolie (ekstra jomfru)", "Kolonial", 500, "ml", 44.95, "olivenolie, jomfruolivenolie"),
            ("Sojasauce", "Kolonial", 150, "ml", 14.95, "sojasauce, soya, soja"),
            ("Fiskesauce", "Kolonial", 200, "ml", 16.95, "fiskesauce, fish sauce"),
            ("Rød karrypasta", "Kolonial", 110, "g", 15.95, "karrypasta, rød karrypasta, thai curry"),
            ("Kyllingebouillon terninger", "Kolonial", 10, "stk", 11.95, "bouillon, hønsebouillon, kyllingebouillon"),
            ("Grøntsagsbouillon terninger", "Kolonial", 10, "stk", 11.95, "grøntsagsbouillon, grøntsagsterning, bouillon"),
            ("Oksebouillon terninger", "Kolonial", 10, "stk", 11.95, "oksebouillon, okseterning, bouillon"),
            ("Sukker", "Kolonial", 1000, "g", 14.95, "sukker, hvidt sukker, støvsukker"),
            ("Brun farin", "Kolonial", 500, "g", 13.95, "brun farin, farin"),
            ("Eddike (lagereddike)", "Kolonial", 1000, "ml", 9.95, "eddike, hvid eddike, lagereddike"),
            ("Balsamico eddike", "Kolonial", 500, "ml", 19.95, "balsamico, balsamicoeddike"),
            ("Sennep (dijon eller sød)", "Kolonial", 250, "g", 12.95, "sennep, dijonsennep"),
            ("Ketchup", "Kolonial", 500, "g", 14.95, "ketchup, tomatketchup"),
            ("Mayonnaise", "Kolonial", 400, "g", 15.95, "mayo, mayonnaise"),
            ("Majsstivelse / Maizena", "Kolonial", 400, "g", 17.95, "maizena, majsstivelse, jævner"),

            # --- KRYDDERIER ---
            ("Fint salt", "Krydderier", 1000, "g", 7.95, "salt, bordsalt, køkkensalt"),
            ("Sort peber (stødt)", "Krydderier", 50, "g", 11.95, "sort peber, peber, stødt peber"),
            ("Karry (stødt)", "Krydderier", 40, "g", 10.95, "karry, madras karry"),
            ("Paprika (sød)", "Krydderier", 40, "g", 10.95, "paprika, sød paprika"),
            ("Spidskommen (stødt)", "Krydderier", 40, "g", 12.95, "spidskommen, kommen"),
            ("Oregano (tørret)", "Krydderier", 20, "g", 9.95, "oregano, tørret oregano"),
            ("Timian (tørret)", "Krydderier", 25, "g", 9.95, "timian, tørret timian"),
            ("Chilipulver / Chiliflager", "Krydderier", 40, "g", 11.95, "chilipulver, chiliflager, cayennepeber"),
            ("Hvidløgspulver", "Krydderier", 45, "g", 10.95, "hvidløgspulver"),
            ("Kanel (stødt)", "Krydderier", 40, "g", 10.95, "kanel"),

            # --- BRØD & BAGERI ---
            ("Rugbrød (solsikke/kerne)", "Brød & Bageri", 950, "g", 16.95, "rugbrød, mørkt brød, kernerugbrød"),
            ("Hvedebrød / Toastbrød", "Brød & Bageri", 600, "g", 14.95, "toastbrød, sandwichbrød, franskbrød"),
            ("Tortilla pandekager / Wraps", "Brød & Bageri", 8, "stk", 14.95, "tortilla, wraps, pandekager, madpandekager"),
            ("Burgerboller (4 stk)", "Brød & Bageri", 4, "stk", 15.95, "burgerboller, brioche boller"),
            ("Pitabrød (6 stk)", "Brød & Bageri", 6, "stk", 12.95, "pitabrød, pita"),
            ("Tærtebund (fersk rulle)", "Brød & Bageri", 250, "g", 14.95, "tærtebund, butterdej"),

            # --- FROST ---
            ("Frosne ærter", "Frost", 500, "g", 11.95, "frosne ærter, ærter, grønne ærter"),
            ("Frosne majs", "Frost", 450, "g", 11.95, "frosne majs, majs"),
            ("Frosne grønne bønner", "Frost", 500, "g", 12.95, "haricots verts, grønne bønner, bønner frost"),
            ("Frossen spinat (hakket)", "Frost", 450, "g", 11.95, "frossen spinat, spinat frost"),
            ("Frossen wokblanding / grønt", "Frost", 500, "g", 14.95, "wokgrønt, wokblanding, frosne grøntsager"),
            ("Pommes frites (frost)", "Frost", 750, "g", 15.95, "pommes frites, ovnfritter"),
        ]

        cursor.executemany("""
            INSERT INTO netto_catalog (name, category, package_size, unit, price_dkk, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
        """, items)
        conn.commit()


def get_all_netto_products() -> List[Dict[str, Any]]:
    """Henter alle varer i Netto-kataloget."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM netto_catalog ORDER BY category, name")
        return [dict(row) for row in cursor.fetchall()]


def add_netto_product(name: str, category: str, package_size: float, unit: str, price_dkk: float, keywords: str) -> int:
    """Tilføjer en ny vare til Netto-kataloget."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO netto_catalog (name, category, package_size, unit, price_dkk, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, category, package_size, unit, price_dkk, keywords))
        conn.commit()
        return cursor.lastrowid


def update_netto_product(prod_id: int, name: str, category: str, package_size: float, unit: str, price_dkk: float, keywords: str):
    """Opdaterer en eksisterende vare i Netto-kataloget."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE netto_catalog
            SET name = ?, category = ?, package_size = ?, unit = ?, price_dkk = ?, keywords = ?
            WHERE id = ?
        """, (name, category, package_size, unit, price_dkk, keywords, prod_id))
        conn.commit()


def normalize_text(text: str) -> str:
    """Renser tekst til søgning (små bogstaver, fjerner specialtegn)."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\sæøå]", " ", text)
    return " ".join(text.split())


def match_ingredient_to_netto(ingredient_name: str, requested_unit: str = "") -> Optional[Dict[str, Any]]:
    """
    Matcher en ingrediens mod Netto-kataloget ved hjælp af nøgleord og tekstanalyse.
    Returnerer den bedst matchende vare eller et fornuftigt standard-estimat.
    """
    normalized_input = normalize_text(ingredient_name)
    tokens = [t for t in normalized_input.split() if len(t) > 2]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM netto_catalog")
        catalog = [dict(row) for row in cursor.fetchall()]

    # 1. Præcis match på navn eller nøgleord
    for item in catalog:
        item_name = normalize_text(item["name"])
        keywords = [normalize_text(k) for k in item["keywords"].split(",")]
        
        if normalized_input == item_name or normalized_input in keywords:
            return item

    # 2. Match hvis nøgleord er indeholdt i ingrediensnavnet (f.eks. "økologisk hakket oksekød" -> "hakket oksekød")
    best_match = None
    best_score = 0

    for item in catalog:
        keywords = [normalize_text(k) for k in item["keywords"].split(",")]
        keywords.append(normalize_text(item["name"]))
        
        for kw in keywords:
            kw_tokens = kw.split()
            # Beregn token overlap
            matched_tokens = sum(1 for t in kw_tokens if t in tokens)
            score = 0
            
            if kw in normalized_input:
                score = len(kw) * 3
            elif matched_tokens > 0:
                score = matched_tokens * 10
            
            # Bonus hvis enheden matcher (f.eks. "g" eller "stk")
            if requested_unit and requested_unit.lower() == item["unit"].lower():
                score += 5
                
            if score > best_score:
                best_score = score
                best_match = item

    if best_match and best_score >= 10:
        return best_match

    return None


def save_meal_plan(
    title: str,
    budget: float,
    people_count: int,
    allergies: str,
    preferences: str,
    notes: str,
    plan_dict: Dict[str, Any],
    total_estimated_price: float,
    shopping_list_items: Optional[List[Dict[str, Any]]] = None
) -> int:
    """Gemmer en genereret madplan og tilhørende indkøbsliste i SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO meal_plans (
                title, budget, people_count, allergies, preferences, notes, plan_json, total_estimated_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, budget, people_count, allergies, preferences, notes,
            json.dumps(plan_dict, ensure_ascii=False), total_estimated_price
        ))
        plan_id = cursor.lastrowid

        if shopping_list_items:
            cursor.execute("""
                INSERT INTO shopping_lists (meal_plan_id, title, items_json, total_price)
                VALUES (?, ?, ?, ?)
            """, (
                plan_id, f"Indkøbsliste til: {title}",
                json.dumps(shopping_list_items, ensure_ascii=False),
                total_estimated_price
            ))

        conn.commit()
        return plan_id


def get_all_saved_meal_plans() -> List[Dict[str, Any]]:
    """Henter alle gemte madplaner sorteret nyeste først."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, created_at, title, budget, people_count, allergies, preferences, notes,
                   total_estimated_price, plan_json
            FROM meal_plans
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["plan_data"] = json.loads(d["plan_json"])
            except Exception:
                d["plan_data"] = {}
            results.append(d)
        return results


def get_meal_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    """Henter en specifik madplan baseret på ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM meal_plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["plan_data"] = json.loads(d["plan_json"])
        
        # Hent tilhørende indkøbsliste hvis findes
        cursor.execute("SELECT * FROM shopping_lists WHERE meal_plan_id = ?", (plan_id,))
        s_row = cursor.fetchone()
        if s_row:
            d["shopping_list"] = dict(s_row)
            d["shopping_list"]["items"] = json.loads(s_row["items_json"])
        else:
            d["shopping_list"] = None
        return d


def delete_meal_plan(plan_id: int):
    """Sletter en madplan og tilknyttede indkøbslister."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM shopping_lists WHERE meal_plan_id = ?", (plan_id,))
        cursor.execute("DELETE FROM meal_plans WHERE id = ?", (plan_id,))
        conn.commit()
