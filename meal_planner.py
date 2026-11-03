"""
OpenAI API integration til generering af 7-dages madplaner.
Indeholder også intelligent demo-generator, hvis API-nøgle ikke er angivet.
"""

import json
import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from models import MealPlanSchema


SYSTEM_PROMPT = """Du er en erfaren dansk kok og husholdningsøkonom med ekspertise i prisbevidst madplanlægning i danske supermarkeder (særligt Netto).
Din opgave er at generere en velsmagende, varieret og budgetvenlig 7-dages madplan (aftensmad til ugens 7 dage: Mandag til Søndag).

Retningslinjer:
1. Respekter brugerens budget, antal personer, allergier og kostpræferencer nøje.
2. Minimer madspild ved at genbruge basis-ingredienser på tværs af ugens dage (f.eks. porrer, gulerødder, løg, ris, creme fraiche, krydderurter).
3. Ingrediensnavne skal skrives på naturligt dansk (f.eks. "Hakket oksekød", "Basmatiris", "Gule løg", "Hvidløg", "Gulerødder", "Hakkede tomater (dåse)").
4. Enheder skal være standardiserede: "g", "kg", "ml", "dl", "L", "stk", "dåse", "spsk", "tsk", "fed".
5. Angiv realistiske mængder tilpasset det angivne antal personer.
6. Svar UDELUKKENDE med valid JSON uden markdown formatering eller kodeblokke.

Output JSON format:
{
  "title": "F.eks. Børnevenlig og økonomisk madplan",
  "overview": "Kort beskrivelse af ugens tema og sparetricks",
  "tips_and_tricks": "Gode råd til at få råvarerne til at række længere",
  "days": [
    {
      "day_number": 1,
      "day_name": "Mandag",
      "meal_name": "Navn på ret",
      "description": "Kort appetitvækkende beskrivelse",
      "cook_time_minutes": 30,
      "servings": 4,
      "instructions": [
        "Trin 1...",
        "Trin 2..."
      ],
      "ingredients": [
        {"name": "Hakket oksekød", "amount": 500, "unit": "g", "category": "Kød & Fisk"},
        {"name": "Gule løg", "amount": 2, "unit": "stk", "category": "Grønt & Frugt"}
      ]
    }
  ]
}
"""


def generate_meal_plan_openai(
    api_key: str,
    budget: float,
    people_count: int,
    allergies: List[str],
    preferences: List[str],
    notes: str = "",
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Kalder OpenAI API for at generere en 7-dages madplan som JSON.
    """
    client = OpenAI(api_key=api_key)

    allergies_str = ", ".join(allergies) if allergies else "Ingen oplyst"
    preferences_str = ", ".join(preferences) if preferences else "Almindelig hverdagsmad"

    user_prompt = f"""Generer en komplet 7-dages madplan (Mandag til Søndag) med følgende rammer:
- Budget: {budget:.0f} DKK for hele ugen
- Antal personer i husstanden: {people_count}
- Allergier / Fødevareintolerancer: {allergies_str}
- Kostpræferencer og stil: {preferences_str}
- Eventuelle ekstra noter eller ønsker: {notes if notes else 'Ingen'}

Sørg for, at madplanen indeholder præcis 7 dage og opfylder alle krav til ingrediensmængder til {people_count} personer."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    content = response.choices[0].message.content
    plan_dict = json.loads(content)
    # Valider mod Pydantic schema for at sikre streng datastruktur
    validated_schema = MealPlanSchema(**plan_dict)
    return validated_schema.model_dump()


def generate_demo_plan(
    budget: float,
    people_count: int,
    allergies: List[str],
    preferences: List[str],
    notes: str = ""
) -> Dict[str, Any]:
    """
    Intelligent demo-generator der returnerer en realistisk 7-dages madplan,
    tilpasset antal personer og vegetar-ønsker uden at kræve OpenAI API-nøgle.
    """
    is_vegetarian = any("vegetar" in p.lower() for p in preferences)
    multiplier = max(1, people_count) / 4.0

    if is_vegetarian:
        plan = {
            "title": f"Grøn og budgetvenlig ugemadplan ({people_count} pers.)",
            "overview": f"En nærende og farverig vegetarisk madplan skræddersyet til {people_count} personer med fokus på bælgfrugter, friske grøntsager og lave Netto-priser.",
            "tips_and_tricks": "Kog en stor portion ris og tørrede/dåsebønner, som kan indgå i flere retter i løbet af ugen.",
            "days": [
                {
                    "day_number": 1,
                    "day_name": "Mandag",
                    "meal_name": "Klassisk Grøntsagslasagne med Spinat og Ost",
                    "description": "Lækker, cremet lasagne fyldt med revet squash, gulerødder, spinat og rigelig ost.",
                    "cook_time_minutes": 45,
                    "servings": people_count,
                    "instructions": [
                        "Svits finthakket løg, hvidløg, revet gulerod og squash i en gryde.",
                        "Tilsæt hakkede tomater, tomatpuré og tørret oregano. Lad simre 15 min.",
                        "Læg skiftevis grøntsagssauce, optøet spinat, mornaysauce/bechamel og lasagneplader i et ovnfast fad.",
                        "Top med revet mozzarella og bag ved 200°C i ca. 30 minutter."
                    ],
                    "ingredients": [
                        {"name": "Lasagneplader", "amount": round(300 * multiplier), "unit": "g", "category": "Kolonial"},
                        {"name": "Hakkede tomater (dåse)", "amount": max(1, round(2 * multiplier)), "unit": "dåse", "category": "Kolonial"},
                        {"name": "Frisk spinat", "amount": round(200 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Gule løg", "amount": max(1, round(2 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Hvidløg", "amount": max(2, round(3 * multiplier)), "unit": "fed", "category": "Grønt & Frugt"},
                        {"name": "Gulerødder", "amount": round(300 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Squash / Zucchini", "amount": max(1, round(1 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Revet Mozzarella", "amount": round(200 * multiplier), "unit": "g", "category": "Mejeri & Køl"}
                    ]
                },
                {
                    "day_number": 2,
                    "day_name": "Tirsdag",
                    "meal_name": "Kremet Rød Dahl med Kokosmælk og Basmatiris",
                    "description": "Indisk linsesuppe/gryde med røde linser, ingefær, kokosmælk og varme krydderier.",
                    "cook_time_minutes": 30,
                    "servings": people_count,
                    "instructions": [
                        "Svits hakket løg, hvidløg, ingefær og spidskommen i lidt olie.",
                        "Tilsæt hakkede tomater, kokosmælk og skyllede røde linser / kikærter.",
                        "Lad retten simre i 20 minutter til linserne er møre og cremede.",
                        "Kog basmatiris og server dahlen toppet med friskpresset citronsaft."
                    ],
                    "ingredients": [
                        {"name": "Kikærter (dåse)", "amount": max(1, round(2 * multiplier)), "unit": "dåse", "category": "Kolonial"},
                        {"name": "Kokosmælk (dåse)", "amount": max(1, round(1 * multiplier)), "unit": "dåse", "category": "Kolonial"},
                        {"name": "Basmatiris", "amount": round(350 * multiplier), "unit": "g", "category": "Kolonial"},
                        {"name": "Hakkede tomater (dåse)", "amount": max(1, round(1 * multiplier)), "unit": "dåse", "category": "Kolonial"},
                        {"name": "Gule løg", "amount": max(1, round(1 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Hvidløg", "amount": 2, "unit": "fed", "category": "Grønt & Frugt"},
                        {"name": "Citroner (3 stk)", "amount": 1, "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Spidskommen (stødt)", "amount": 1, "unit": "spsk", "category": "Krydderier"}
                    ]
                },
                {
                    "day_number": 3,
                    "day_name": "Onsdag",
                    "meal_name": "Grøntsagstærte med Porrer, Feta og Salat",
                    "description": "Sprød madtærte fyldt med dampede porrer, cremet æggemasse og saltet feta.",
                    "cook_time_minutes": 40,
                    "servings": people_count,
                    "instructions": [
                        "Rul tærtedejen ud i en tærteform og prik bunden med en gaffel.",
                        "Skær porrer i ringe og svits dem bløde på en pande med lidt smør.",
                        "Pisk æg, mælk, salt og peber sammen.",
                        "Fordel porrer og smuldret feta i tærten, hæld æggemassen over og bag 35 min ved 200°C.",
                        "Server med frisk agurk og tomater."
                    ],
                    "ingredients": [
                        {"name": "Tærtebund (fersk rulle)", "amount": max(1, round(1 * multiplier)), "unit": "pakke", "category": "Brød & Bageri"},
                        {"name": "Porrer (3 stk)", "amount": max(2, round(2 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Friske Æg (10 stk M/L)", "amount": max(3, round(4 * multiplier)), "unit": "stk", "category": "Mejeri & Køl"},
                        {"name": "Letmælk", "amount": round(150 * multiplier), "unit": "ml", "category": "Mejeri & Køl"},
                        {"name": "Feta / Salattern", "amount": round(150 * multiplier), "unit": "g", "category": "Mejeri & Køl"},
                        {"name": "Tomater i bakke", "amount": round(250 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Agurk", "amount": 1, "unit": "stk", "category": "Grønt & Frugt"}
                    ]
                },
                {
                    "day_number": 4,
                    "day_name": "Torsdag",
                    "meal_name": "Kikærte-curry i Wok med Grøntsager og Jasminris",
                    "description": "Mild og fyldig grøntsagscurry med sprøde grøntsager og mættende kikærter.",
                    "cook_time_minutes": 25,
                    "servings": people_count,
                    "instructions": [
                        "Varm lidt olie i en wok eller dyb pande og svits rød karrypasta.",
                        "Tilsæt gulerødder, broccoli i små buketter og peberfrugt.",
                        "Tilsæt kokosmælk og drænede kikærter og lad simre i 10 minutter.",
                        "Smag til med lidt sojasauce og server med dampende jasminris."
                    ],
                    "ingredients": [
                        {"name": "Kikærter (dåse)", "amount": max(1, round(2 * multiplier)), "unit": "dåse", "category": "Kolonial"},
                        {"name": "Kokosmælk (dåse)", "amount": max(1, round(1 * multiplier)), "unit": "dåse", "category": "Kolonial"},
                        {"name": "Rød karrypasta", "amount": 2, "unit": "spsk", "category": "Kolonial"},
                        {"name": "Broccoli", "amount": round(300 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Rød peberfrugt", "amount": max(1, round(1 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Jasminris", "amount": round(350 * multiplier), "unit": "g", "category": "Kolonial"}
                    ]
                },
                {
                    "day_number": 5,
                    "day_name": "Fredag",
                    "meal_name": "Vegetariske Burger med Hjemmelavede Fritter",
                    "description": "Saftige bønnebøffer i sprøde burgerboller med cheddarost, salat og sprøde ovnfritter.",
                    "cook_time_minutes": 35,
                    "servings": people_count,
                    "instructions": [
                        "Skær kartofler i stave, vend i lidt olie, salt og peber, og bag ved 220°C i 30 min.",
                        "Mos kidneybønner med et æg, lidt mel, hakket løg og spidskommen. Form til bøffer og steg sprøde.",
                        "Rist burgerbollerne.",
                        "Saml burgerne med mayo, salat, agurk, tomater og de lune bøffer."
                    ],
                    "ingredients": [
                        {"name": "Burgerboller (4 stk)", "amount": max(2, round(people_count)), "unit": "stk", "category": "Brød & Bageri"},
                        {"name": "Kidneybønner (dåse)", "amount": max(1, round(2 * multiplier)), "unit": "dåse", "category": "Kolonial"},
                        {"name": "Kartofler (danske)", "amount": round(800 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Iceberg salat", "amount": 1, "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Tomater i bakke", "amount": round(200 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Mayonnaise", "amount": round(80 * multiplier), "unit": "g", "category": "Kolonial"},
                        {"name": "Friske Æg (10 stk M/L)", "amount": 1, "unit": "stk", "category": "Mejeri & Køl"}
                    ]
                },
                {
                    "day_number": 6,
                    "day_name": "Lørdag",
                    "meal_name": "Hjemmelavet Kartoffel-Porre Suppe med Ristede Kerner og Brød",
                    "description": "Varmende og fløjlsblød klassisk vintersuppe serveret med lunt flute.",
                    "cook_time_minutes": 30,
                    "servings": people_count,
                    "instructions": [
                        "Svits porrer og hakket løg i lidt smør i en gryde.",
                        "Skræl kartofler, skær i tern og kom i gryden sammen med grøntsagsbouillon.",
                        "Kog til kartoflerne er møre (ca. 18 minutter).",
                        "Blend suppen helt glat med en stavblender og rør madlavningsfløde i.",
                        "Smag til med salt, peber og server med ristet hvedebrød."
                    ],
                    "ingredients": [
                        {"name": "Kartofler (danske)", "amount": round(700 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Porrer (3 stk)", "amount": max(2, round(2 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Madlavningsfløde 18%", "amount": round(200 * multiplier), "unit": "ml", "category": "Mejeri & Køl"},
                        {"name": "Grøntsagsbouillon terninger", "amount": 2, "unit": "stk", "category": "Kolonial"},
                        {"name": "Hvedebrød / Toastbrød", "amount": round(300 * multiplier), "unit": "g", "category": "Brød & Bageri"}
                    ]
                },
                {
                    "day_number": 7,
                    "day_name": "Søndag",
                    "meal_name": "Pasta med Cremet Tomatsauce, Spinat og Parmesan",
                    "description": "Hurtig søndagspasta der bruger ugens rester af grønt og ost.",
                    "cook_time_minutes": 20,
                    "servings": people_count,
                    "instructions": [
                        "Kog pastaen al dente i rigeligt saltet vand.",
                        "Svits hvidløg og tomatpuré i olivenolie på en pande.",
                        "Tilsæt passata/hakkede tomater og lad simre i 8 min.",
                        "Vend frisk spinat og kogt pasta i saucen så spinaten falder sammen.",
                        "Server med friskrevet parmesan på toppen."
                    ],
                    "ingredients": [
                        {"name": "Penne / Skruer pasta", "amount": round(400 * multiplier), "unit": "g", "category": "Kolonial"},
                        {"name": "Passata / Tomatpassata", "amount": max(1, round(1 * multiplier)), "unit": "pakke", "category": "Kolonial"},
                        {"name": "Frisk spinat", "amount": round(150 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Hvidløg", "amount": 2, "unit": "fed", "category": "Grønt & Frugt"},
                        {"name": "Parmesan (stykke)", "amount": round(60 * multiplier), "unit": "g", "category": "Mejeri & Køl"}
                    ]
                }
            ]
        }
    else:
        # Standard populær dansk hverdagsmadplan
        plan = {
            "title": f"Dansk Hverdagsfavorit Madplan ({people_count} pers.)",
            "overview": f"En familievenlig og velsmagende madplan for {people_count} personer med kendte klassikere, lavet af gode råvarer til Netto-priser.",
            "tips_and_tricks": "Kartofler og løg købes i store poser og udnyttes optimalt over flere dage.",
            "days": [
                {
                    "day_number": 1,
                    "day_name": "Mandag",
                    "meal_name": "Klassisk Spaghetti Bolognese",
                    "description": "Fyldig og børnevenlig kødsovs med oksekød, masser af grøntsager og spaghetti.",
                    "cook_time_minutes": 30,
                    "servings": people_count,
                    "instructions": [
                        "Brun hakket oksekød i en stor gryde.",
                        "Tilsæt finthakket løg, hvidløg og revet gulerod.",
                        "Tilsæt hakkede tomater, tomatpuré, oregano, salt og peber. Lad simre 20 min.",
                        "Kog spaghetti i letsaltet vand og server med friskhakket persille eller ost."
                    ],
                    "ingredients": [
                        {"name": "Hakket oksekød 8-12%", "amount": round(500 * multiplier), "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Spaghetti", "amount": round(400 * multiplier), "unit": "g", "category": "Kolonial"},
                        {"name": "Hakkede tomater (dåse)", "amount": max(1, round(2 * multiplier)), "unit": "dåse", "category": "Kolonial"},
                        {"name": "Tomatpuré", "amount": 1, "unit": "dåse", "category": "Kolonial"},
                        {"name": "Gule løg", "amount": max(1, round(2 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Gulerødder", "amount": round(250 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Hvidløg", "amount": 2, "unit": "fed", "category": "Grønt & Frugt"},
                        {"name": "Oregano (tørret)", "amount": 1, "unit": "spsk", "category": "Krydderier"}
                    ]
                },
                {
                    "day_number": 2,
                    "day_name": "Tirsdag",
                    "meal_name": "Kylling i Karry med Grønt og Ris",
                    "description": "Mør kylling i en mild og cremet karrysauce med æbler og ærter, serveret med ris.",
                    "cook_time_minutes": 30,
                    "servings": people_count,
                    "instructions": [
                        "Skær kyllingebryst i mundrette tern og brun i en gryde med karry og løg.",
                        "Tilsæt terninger af æbler og gulerødder.",
                        "Hæld hønsebouillon og madlavningsfløde ved og lad simre i 12 minutter.",
                        "Tilsæt frosne ærter de sidste 2 minutter og smag til med salt.",
                        "Server med kogte ris."
                    ],
                    "ingredients": [
                        {"name": "Kyllingebrystfilet", "amount": round(450 * multiplier), "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Basmatiris", "amount": round(350 * multiplier), "unit": "g", "category": "Kolonial"},
                        {"name": "Gule løg", "amount": max(1, round(1 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Æbler (pose)", "amount": max(1, round(2 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Karry (stødt)", "amount": 2, "unit": "spsk", "category": "Krydderier"},
                        {"name": "Madlavningsfløde 18%", "amount": round(200 * multiplier), "unit": "ml", "category": "Mejeri & Køl"},
                        {"name": "Frosne ærter", "amount": round(200 * multiplier), "unit": "g", "category": "Frost"}
                    ]
                },
                {
                    "day_number": 3,
                    "day_name": "Onsdag",
                    "meal_name": "Danske Frikadeller med Kartofler og Brun Sauce",
                    "description": "Klassiske saftige frikadeller af hakket svin/kalv med kogte kartofler og lun sauce.",
                    "cook_time_minutes": 35,
                    "servings": people_count,
                    "instructions": [
                        "Rør hakket kød med revet løg, æg, mel, mælk, salt og peber til en fast fars.",
                        "Form frikadeller med en ske og steg gyldne i smør/olie på en pande.",
                        "Kog kartoflerne møre i saltet vand.",
                        "Lav pandesovs af stegefedtet spædet med kartoffelvand/bouillon og lidt fløde.",
                        "Server med kartofler og eventuelt syltede agurker."
                    ],
                    "ingredients": [
                        {"name": "Hakket svinekød 8-12%", "amount": round(500 * multiplier), "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Kartofler (danske)", "amount": round(900 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Gule løg", "amount": max(1, round(1 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Friske Æg (10 stk M/L)", "amount": 1, "unit": "stk", "category": "Mejeri & Køl"},
                        {"name": "Hvedemel", "amount": round(40 * multiplier), "unit": "g", "category": "Kolonial"},
                        {"name": "Letmælk", "amount": round(100 * multiplier), "unit": "ml", "category": "Mejeri & Køl"},
                        {"name": "Smørbar (Lurpak/Kærgården)", "amount": round(40 * multiplier), "unit": "g", "category": "Mejeri & Køl"}
                    ]
                },
                {
                    "day_number": 4,
                    "day_name": "Torsdag",
                    "meal_name": "Ovnbagt Laks med Citron, Dampet Broccoli og Ris",
                    "description": "Sund og hurtig hverdagsfisk tilberedt i ovn med citron og sprød broccoli.",
                    "cook_time_minutes": 25,
                    "servings": people_count,
                    "instructions": [
                        "Læg laksen i et ovnfast fad, drys med salt, peber og læg citronskiver på toppen.",
                        "Bag ved 180°C i ca. 15-18 minutter.",
                        "Kog risene.",
                        "Skær broccoli i buketter og damp i letsaltet vand i 4 minutter.",
                        "Rør creme fraiche med lidt hvidløg og citronsaft til en kold dressing."
                    ],
                    "ingredients": [
                        {"name": "Lakseportioner (2 stk)", "amount": round(300 * multiplier), "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Broccoli", "amount": round(400 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Citroner (3 stk)", "amount": 1, "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Basmatiris", "amount": round(300 * multiplier), "unit": "g", "category": "Kolonial"},
                        {"name": "Creme Fraiche 18%", "amount": round(150 * multiplier), "unit": "g", "category": "Mejeri & Køl"}
                    ]
                },
                {
                    "day_number": 5,
                    "day_name": "Fredag",
                    "meal_name": "Mexicanske Tortilla Wraps med Oksekød og Frisk Grønt",
                    "description": "Festlig fredagsmad hvor familien selv bygger lune tortillas med kød, majs, salat og ost.",
                    "cook_time_minutes": 20,
                    "servings": people_count,
                    "instructions": [
                        "Steg hakket oksekød på en pande med spidskommen, paprika, salt og hvidløg.",
                        "Snit icebergsalat, tomater og agurk.",
                        "Lun tortillapandekagerne i ovnen eller på en tør pande.",
                        "Server kød, lune wraps, majs, revet mozzarella og creme fraiche i små skåle."
                    ],
                    "ingredients": [
                        {"name": "Hakket oksekød 8-12%", "amount": round(500 * multiplier), "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Tortilla pandekager / Wraps", "amount": max(4, round(8 * multiplier)), "unit": "stk", "category": "Brød & Bageri"},
                        {"name": "Revet Mozzarella", "amount": round(150 * multiplier), "unit": "g", "category": "Mejeri & Køl"},
                        {"name": "Frosne majs", "amount": round(200 * multiplier), "unit": "g", "category": "Frost"},
                        {"name": "Iceberg salat", "amount": 1, "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Tomater i bakke", "amount": round(250 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Creme Fraiche 18%", "amount": round(150 * multiplier), "unit": "g", "category": "Mejeri & Køl"},
                        {"name": "Spidskommen (stødt)", "amount": 1, "unit": "spsk", "category": "Krydderier"}
                    ]
                },
                {
                    "day_number": 6,
                    "day_name": "Lørdag",
                    "meal_name": "Hjemmelavede Smashburgere med Sprøde Bådkartofler",
                    "description": "Lækre burgere med saftigt oksekød, smeltet ost, sprøde kartoffelbåde og burgerdressing.",
                    "cook_time_minutes": 35,
                    "servings": people_count,
                    "instructions": [
                        "Vask kartofler og skær dem i både. Vend i rapsolie, salt og paprika. Bag i ovn ved 210°C i 30 min.",
                        "Form faste kugler af oksekød og pres fladt på en rygende varm pande (smash).",
                        "Læg ost på bøfferne lige inden de tages af panden så det smelter.",
                        "Rist burgerbollerne let.",
                        "Saml burgerne med mayo, salat, bøf, tomat og løgringe."
                    ],
                    "ingredients": [
                        {"name": "Burgerboller (4 stk)", "amount": max(2, round(people_count)), "unit": "stk", "category": "Brød & Bageri"},
                        {"name": "Hakket oksekød 8-12%", "amount": round(500 * multiplier), "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Kartofler (danske)", "amount": round(800 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Iceberg salat", "amount": 1, "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Rødløg", "amount": max(1, round(1 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Tomater i bakke", "amount": round(200 * multiplier), "unit": "g", "category": "Grønt & Frugt"},
                        {"name": "Mayonnaise", "amount": round(80 * multiplier), "unit": "g", "category": "Kolonial"}
                    ]
                },
                {
                    "day_number": 7,
                    "day_name": "Søndag",
                    "meal_name": "Porre-Bacon Tærte med Grøn Salat",
                    "description": "Dejlig søndagstærte med sprød bacon, møre porrer og en let grøn salat til.",
                    "cook_time_minutes": 40,
                    "servings": people_count,
                    "instructions": [
                        "Rul tærtedejen ud i en tærteform.",
                        "Rist bacontern sprøde på en tør pande og svits porreringe let i baconfedtet.",
                        "Pisk æg sammen med mælk, salt og friskkværnet peber.",
                        "Læg bacon og porrer i tærtebunden og hæld æggemassen over.",
                        "Bag ved 200°C i 30-35 minutter til den er fast og gylden.",
                        "Server med resten af ugens salat og agurk."
                    ],
                    "ingredients": [
                        {"name": "Tærtebund (fersk rulle)", "amount": max(1, round(1 * multiplier)), "unit": "pakke", "category": "Brød & Bageri"},
                        {"name": "Bacon i tern", "amount": round(150 * multiplier), "unit": "g", "category": "Kød & Fisk"},
                        {"name": "Porrer (3 stk)", "amount": max(2, round(2 * multiplier)), "unit": "stk", "category": "Grønt & Frugt"},
                        {"name": "Friske Æg (10 stk M/L)", "amount": max(3, round(4 * multiplier)), "unit": "stk", "category": "Mejeri & Køl"},
                        {"name": "Letmælk", "amount": round(150 * multiplier), "unit": "ml", "category": "Mejeri & Køl"},
                        {"name": "Agurk", "amount": 1, "unit": "stk", "category": "Grønt & Frugt"}
                    ]
                }
            ]
        }

    return plan
