"""
Domænemodeller og Pydantic-skemaer for Madplanlæggeren.
Sikrer streng typetestning, datavalidering og serialisering mellem AI, Database og Frontend.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    """Enkelt ingrediens i en opskrift."""
    name: str = Field(..., description="Ingrediensens navn på dansk (f.eks. Hakket oksekød)")
    amount: float = Field(..., gt=0, description="Mængde af ingrediensen")
    unit: str = Field(..., description="Enhed (g, kg, ml, dl, L, stk, dåse, fed, spsk, tsk)")
    category: Optional[str] = Field("Kolonial", description="Varekategori (f.eks. Grønt & Frugt, Kød & Fisk)")


class DayPlan(BaseModel):
    """Dagsmenu i madplanen."""
    day_number: int = Field(..., ge=1, le=7, description="Dag 1 til 7")
    day_name: str = Field(..., description="Ugedag (f.eks. Mandag)")
    meal_name: str = Field(..., description="Rettens titel")
    description: str = Field("", description="Beskrivelse af retten")
    cook_time_minutes: int = Field(30, ge=5, description="Forventet tilberedningstid")
    servings: int = Field(4, ge=1, description="Antal kuverter/portioner")
    instructions: List[str] = Field(default_factory=list, description="Trin-for-trin guide")
    ingredients: List[Ingredient] = Field(default_factory=list, description="Ingredienser til retten")


class MealPlanSchema(BaseModel):
    """Komplet 7-dages madplan struktureret til JSON-schema validering med OpenAI."""
    title: str = Field(..., description="Madplanens overordnede tema/titel")
    overview: str = Field("", description="Kort introduktion og overblik over ugen")
    tips_and_tricks: Optional[str] = Field("", description="Gode råd til madspild og tilberedning")
    days: List[DayPlan] = Field(..., description="Præcis 7 dages madplan (Mandag til Søndag)")


class ShoppingItem(BaseModel):
    """Aggregeret varelinje til indkøbslisten med Netto-katalog matching."""
    name: str
    category: str
    recipe_amount: str
    packages_needed: int
    netto_product_name: str
    unit_price_dkk: float
    total_price_dkk: float
    package_info: str
    used_in: List[str]
    is_matched: bool
    checked: bool = False


class NettoProduct(BaseModel):
    """Vare i det lokale Netto varekatalog."""
    id: Optional[int] = None
    name: str
    category: str
    package_size: float
    unit: str
    price_dkk: float
    keywords: str
