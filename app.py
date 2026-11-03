"""
Madplanlægger med AI og Netto Prisberegner
En komplet Streamlit-applikation til ugentlig madplanlægning med SQLite og OpenAI API.
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Importer lokale moduler
from db import (
    init_db,
    save_meal_plan,
    get_all_saved_meal_plans,
    get_meal_plan,
    delete_meal_plan,
    get_all_netto_products,
    add_netto_product,
    update_netto_product
)
from meal_planner import generate_meal_plan_openai, generate_demo_plan
from aggregator import aggregate_meal_plan_ingredients, calculate_total_shopping_price

# Sæt Streamlit sidekonfiguration
st.set_page_config(
    page_title="Netto Madplanlægger AI",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialiser databasen
init_db()

# Custom CSS for et flot, moderne og nordisk design
st.markdown("""
<style>
    /* Hoveddesign og farver */
    :root {
        --netto-yellow: #FEE100;
        --netto-black: #1E1E1E;
        --accent-green: #2E7D32;
    }
    
    .main-header {
        background: linear-gradient(135deg, #FFE600 0%, #FFD000 100%);
        padding: 24px;
        border-radius: 12px;
        color: #1E1E1E;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        margin: 0;
        font-weight: 800;
        font-size: 2.2rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .main-header p {
        margin: 6px 0 0 0;
        font-size: 1.05rem;
        color: #333333;
    }
    
    /* Dags-kort */
    .day-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #FFCC00;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 14px;
    }
    
    .badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 12px;
        background-color: #e2e8f0;
        color: #334155;
        margin-right: 6px;
    }
    .badge-success {
        background-color: #dcfce7;
        color: #166534;
    }
    .badge-warning {
        background-color: #fef3c7;
        color: #92400e;
    }
    .badge-category {
        background-color: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
    }
    
    /* Prisboks */
    .price-metric-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 16px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
</style>
""", unsafe_allow_html=True)

# Initialiser Session State
if "current_plan" not in st.session_state:
    st.session_state.current_plan = None
if "current_shopping_list" not in st.session_state:
    st.session_state.current_shopping_list = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "checked_items" not in st.session_state:
    st.session_state.checked_items = set()


# ==========================================
# SIDEBAR: API & Indstillinger
# ==========================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=600&q=80", use_container_width=True)
    st.title("⚙️ AI Indstillinger")
    
    env_api_key = os.environ.get("OPENAI_API_KEY", "")
    api_key_input = st.text_input(
        "OpenAI API Nøgle",
        value=env_api_key,
        type="password",
        help="Indtast din OpenAI API nøgle (starter med sk-...). Hvis tom, benyttes den smarte demo-generator."
    )
    
    use_openai = bool(api_key_input.strip())
    
    if use_openai:
        st.success("🟢 OpenAI API er klar")
        model_choice = st.selectbox(
            "OpenAI Model",
            ["gpt-4o-mini", "gpt-4o"],
            help="gpt-4o-mini er lynhurtig og billig. gpt-4o er endnu mere kreativ."
        )
    else:
        st.info("🟡 Demo-tilstand aktiv (ingen API-nøgle påkrævet for at teste appen)")
        model_choice = "demo"

    st.markdown("---")
    st.markdown("### 🛒 Om Netto Madplanlægger")
    st.markdown("""
    Denne app kombinerer:
    - **OpenAI GPT** til at sammensætte varierede madplaner
    - **Smart aggregering** af ingredienser for at minimere madspild
    - **Lokal Netto-database** med aktuelle priser og pakkestørrelser
    - **SQLite lagring** af dine favoritplaner og indkøbslister
    """)
    st.caption("Udviklet med Python & Streamlit • 100% lokal database")


# ==========================================
# HOVEDSIDE HEADER
# ==========================================
st.markdown("""
<div class="main-header">
    <h1>🛒 Netto AI Madplanlægger</h1>
    <p>Generér en skræddersyet 7-dages madplan, saml automatisk indkøbslisten og beregn den præcise pris i Netto!</p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# FANER (TABS)
# ==========================================
tab_create, tab_plan, tab_shopping, tab_history, tab_catalog = st.tabs([
    "📋 Opret Ny Madplan",
    "🍽️ Ugens Madplan",
    "🛒 Samlet Indkøbsliste & Pris",
    "💾 Gemte Madplaner",
    "🏪 Netto Varekatalog"
])


# ==========================================
# FANE 1: Opret Ny Madplan
# ==========================================
with tab_create:
    st.subheader("Angiv dine ønsker og rammer for ugen")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 🎯 Grundlæggende indstillinger")
        budget = st.number_input(
            "Ugentligt madbudget (DKK)",
            min_value=200,
            max_value=3500,
            value=650,
            step=50,
            help="Hvor meget må ugens aftensmåltider koste i alt?"
        )
        
        people_count = st.number_input(
            "Antal personer i husstanden",
            min_value=1,
            max_value=12,
            value=4,
            step=1,
            help="Hvor mange personer laves der mad til?"
        )
        
        st.markdown("#### 🚫 Allergier & Intolerancer")
        common_allergies = [
            "Glutenallergi",
            "Laktoseintolerance",
            "Nøddeallergi",
            "Skaldyrsallergi",
            "Ægallergi",
            "Sojaallergi"
        ]
        selected_allergies = st.multiselect(
            "Vælg kendte allergier",
            common_allergies,
            default=[]
        )
        custom_allergies = st.text_input(
            "Andre allergier eller ingredienser der skal undgås",
            placeholder="F.eks. svinekød, koriander, svampe..."
        )
        all_allergies = selected_allergies.copy()
        if custom_allergies.strip():
            all_allergies.append(custom_allergies.strip())

    with col2:
        st.markdown("#### 🥗 Kostpræferencer & Madstil")
        common_preferences = [
            "Børnevenlig mad",
            "Hurtig og nem (under 30 min)",
            "Vegetarisk",
            "Pescetarisk (fisk og grønt)",
            "Klassisk dansk hverdagsmad",
            "Kalorielet og sund",
            "Mexicansk / Italiensk inspireret",
            "Fokus på minimalt madspild"
        ]
        selected_preferences = st.multiselect(
            "Vælg præferencer for retterne",
            common_preferences,
            default=["Børnevenlig mad", "Fokus på minimalt madspild"]
        )
        
        custom_preferences = st.text_input(
            "Særlige ønsker til ugens menu (valgfrit)",
            placeholder="F.eks. gerne suppe om tirsdagen, burger om fredagen..."
        )
        all_preferences = selected_preferences.copy()
        if custom_preferences.strip():
            all_preferences.append(custom_preferences.strip())

        st.markdown("#### 💡 Beregnet rettesnit")
        per_person_day = budget / (people_count * 7) if (people_count and budget) else 0
        st.info(f"📊 Budgettet svarer til **{budget / 7:.1f} kr.** pr. aften (**{per_person_day:.1f} kr.** pr. person pr. dag).")

    st.markdown("---")
    
    # Knap til at generere madplan
    generate_btn = st.button("✨ Generér 7-dages Madplan & Netto Indkøbsliste", type="primary", use_container_width=True)
    
    if generate_btn:
        with st.spinner("Kokken planlægger ugens måltider og samler ingredienser..."):
            try:
                if use_openai:
                    plan_data = generate_meal_plan_openai(
                        api_key=api_key_input.strip(),
                        budget=float(budget),
                        people_count=int(people_count),
                        allergies=all_allergies,
                        preferences=all_preferences,
                        notes=custom_preferences,
                        model=model_choice
                    )
                else:
                    plan_data = generate_demo_plan(
                        budget=float(budget),
                        people_count=int(people_count),
                        allergies=all_allergies,
                        preferences=all_preferences,
                        notes=custom_preferences
                    )

                # Saml ingredienser og beregn Netto priser
                shopping_list = aggregate_meal_plan_ingredients(plan_data)
                total_estimated_price = calculate_total_shopping_price(shopping_list)

                # Gem i session state
                st.session_state.current_plan = {
                    "budget": float(budget),
                    "people_count": int(people_count),
                    "allergies": ", ".join(all_allergies),
                    "preferences": ", ".join(all_preferences),
                    "notes": custom_preferences,
                    "plan_data": plan_data,
                    "total_price": total_estimated_price
                }
                st.session_state.current_shopping_list = shopping_list
                st.session_state.checked_items = set()

                # Gem automatisk i SQLite
                plan_id = save_meal_plan(
                    title=plan_data.get("title", f"Madplan ({datetime.now().strftime('%d/%m/%Y')})"),
                    budget=float(budget),
                    people_count=int(people_count),
                    allergies=", ".join(all_allergies),
                    preferences=", ".join(all_preferences),
                    notes=custom_preferences,
                    plan_dict=plan_data,
                    total_estimated_price=total_estimated_price,
                    shopping_list_items=shopping_list
                )
                st.session_state.current_plan["id"] = plan_id

                st.success(f"🎉 Madplanen blev oprettet og gemt i SQLite databasen (ID #{plan_id})!")
                st.balloons()
                
            except Exception as e:
                st.error(f"Der opstod en fejl under genereringen: {str(e)}")
                st.info("Tip: Hvis du bruger OpenAI API, kontrollér at din API-nøgle er gyldig og har kreditter tilgængelig.")


# ==========================================
# FANE 2: Ugens Madplan
# ==========================================
with tab_plan:
    if not st.session_state.current_plan:
        st.info("👋 Du har ikke genereret en madplan endnu. Gå til fanen **'📋 Opret Ny Madplan'** for at starte.")
    else:
        plan = st.session_state.current_plan
        plan_data = plan["plan_data"]
        
        st.markdown(f"## 🍽️ {plan_data.get('title', 'Ugens Madplan')}")
        if plan_data.get("overview"):
            st.markdown(f"*{plan_data.get('overview')}*")
            
        if plan_data.get("tips_and_tricks"):
            st.markdown(f"> **💡 Kokkens sparetip:** {plan_data.get('tips_and_tricks')}")

        st.markdown("---")
        
        days = plan_data.get("days", [])
        for day in days:
            day_num = day.get("day_number", "")
            day_name = day.get("day_name", f"Dag {day_num}")
            meal_name = day.get("meal_name", "Ret")
            cook_time = day.get("cook_time_minutes", 30)
            servings = day.get("servings", plan.get("people_count", 4))
            description = day.get("description", "")
            ingredients = day.get("ingredients", [])
            instructions = day.get("instructions", [])

            with st.expander(f"📅 **{day_name}**: {meal_name}  ⏱️ {cook_time} min  👥 {servings} pers.", expanded=(day_num in [1, 2])):
                if description:
                    st.markdown(f"**Beskrivelse:** {description}")
                
                col_ing, col_inst = st.columns([1, 1])
                
                with col_ing:
                    st.markdown("#### 🥕 Ingredienser")
                    for ing in ingredients:
                        name = ing.get("name", "")
                        amount = ing.get("amount", "")
                        unit = ing.get("unit", "")
                        cat = ing.get("category", "")
                        st.markdown(f"- **{name}**: {amount} {unit} <span class='badge badge-category'>{cat}</span>", unsafe_allow_html=True)
                
                with col_inst:
                    st.markdown("#### 👩‍🍳 Fremgangsmåde")
                    if isinstance(instructions, list):
                        for i, step in enumerate(instructions, 1):
                            st.markdown(f"**{i}.** {step}")
                    else:
                        st.markdown(str(instructions))


# ==========================================
# FANE 3: Samlet Indkøbsliste & Netto Priser
# ==========================================
with tab_shopping:
    if not st.session_state.current_shopping_list:
        st.info("🛒 Indkøbslisten er tom. Generér en madplan for at få en samlet Netto indkøbsliste.")
    else:
        shopping_list = st.session_state.current_shopping_list
        plan = st.session_state.current_plan
        budget = plan.get("budget", 650.0)
        total_price = calculate_total_shopping_price(shopping_list)
        diff = budget - total_price

        # Pris-overblik kasser
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Netto Indkøbspris", f"{total_price:.2f} kr.")
        with m2:
            st.metric("Dit Budget", f"{budget:.2f} kr.")
        with m3:
            diff_label = "Under budget 🎉" if diff >= 0 else "Over budget ⚠️"
            st.metric(diff_label, f"{abs(diff):.2f} kr.", delta=f"{diff:.2f} kr.")
        with m4:
            st.metric("Antal Varelinjer", len(shopping_list))

        # Progress bar mod budget
        pct = min(1.0, total_price / budget) if budget > 0 else 1.0
        st.progress(pct, text=f"Forbrug af budget: {pct * 100:.1f}%")

        if diff >= 0:
            st.success(f"👏 Flot! Din samlede indkøbsliste i Netto holder sig **{diff:.2f} kr.** under dit budget på {budget:.0f} kr.")
        else:
            st.warning(f"⚠️ Bemærk: Indkøbslisten overstiger budgettet med **{abs(diff):.2f} kr.** Overvej at udskifte f.eks. kødretter med bønner eller pasta.")

        st.markdown("---")
        
        # Mulighed for at afkrydse varer
        st.markdown("### 📝 Afkrydsningsliste sorteret efter Netto-kategori")
        st.caption("Varer fra alle ugens 7 retter er lagt sammen og dubletter er fjernet. Klik af efterhånden som du handler i Netto!")

        # Gruppér efter kategori
        categories = sorted(list(set(item["category"] for item in shopping_list)))
        
        for cat in categories:
            cat_items = [it for it in shopping_list if it["category"] == cat]
            st.markdown(f"#### 🏷️ {cat} ({len(cat_items)} varer)")
            
            for item in cat_items:
                item_id = item["name"]
                is_checked = item_id in st.session_state.checked_items
                
                c_check, c_name, c_qty, c_netto, c_price = st.columns([0.6, 2.5, 1.8, 3.2, 1.5])
                
                with c_check:
                    checked = st.checkbox("", value=is_checked, key=f"chk_{item_id}")
                    if checked:
                        st.session_state.checked_items.add(item_id)
                    else:
                        st.session_state.checked_items.discard(item_id)
                
                with c_name:
                    name_style = f"~~{item['name']}~~" if checked else f"**{item['name']}**"
                    st.markdown(name_style)
                    st.caption(f"Bruges i: {', '.join(item['used_in'][:2])}")
                
                with c_qty:
                    st.markdown(f"Opskrift: `{item['recipe_amount']}`")
                
                with c_netto:
                    if item.get("is_matched"):
                        st.markdown(f"Netto: {item['package_info']}")
                    else:
                        st.markdown(f"Netto: *{item['package_info']}*")
                
                with c_price:
                    st.markdown(f"**{item['total_price_dkk']:.2f} kr.**")

            st.markdown("<hr style='margin: 8px 0; border: none; border-bottom: 1px dashed #cbd5e1;'>", unsafe_allow_html=True)

        # Eksport og download
        st.markdown("### 📤 Eksportér Indkøbsliste")
        export_text_lines = [
            f"🛒 INDKØBSLISTE - NETTO ({datetime.now().strftime('%d/%m/%Y')})",
            f"Estimeret total: {total_price:.2f} DKK | Budget: {budget:.2f} DKK",
            "=" * 50,
            ""
        ]
        for cat in categories:
            export_text_lines.append(f"[{cat.upper()}]")
            for it in [x for x in shopping_list if x["category"] == cat]:
                export_text_lines.append(f" [ ] {it['name']}: {it['recipe_amount']} -> Køb: {it['package_info']} ({it['total_price_dkk']:.2f} kr.)")
            export_text_lines.append("")

        export_content = "\n".join(export_text_lines)
        
        st.download_button(
            label="📥 Download Indkøbsliste som Tekstfil (.txt)",
            data=export_content,
            file_name=f"netto_indkoebsliste_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )


# ==========================================
# FANE 4: Gemte Madplaner (Historik i SQLite)
# ==========================================
with tab_history:
    st.subheader("💾 Gemte Madplaner i SQLite")
    saved_plans = get_all_saved_meal_plans()

    if not saved_plans:
        st.info("Ingen gemte madplaner endnu. Når du genererer en ny madplan, gemmes den automatisk her.")
    else:
        st.write(f"Du har **{len(saved_plans)}** gemte madplaner i databasen.")
        
        for sp in saved_plans:
            plan_id = sp["id"]
            title = sp["title"]
            created_at = sp["created_at"]
            budget_val = sp["budget"]
            price_val = sp["total_estimated_price"]
            people = sp["people_count"]
            prefs = sp["preferences"] or "Standard"
            
            with st.container():
                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0;">#{plan_id}: {title}</h4>
                        <span style="font-size: 0.85rem; color: #64748b;">📅 {created_at}</span>
                    </div>
                    <p style="margin: 6px 0; color: #475569; font-size: 0.95rem;">
                        👥 <b>{people} personer</b> | 💰 Budget: <b>{budget_val:.0f} kr.</b> | 🛒 Netto Pris: <b>{price_val:.2f} kr.</b> | 🏷️ <i>{prefs}</i>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                btn_col1, btn_col2, _ = st.columns([1.5, 1, 4])
                
                with btn_col1:
                    if st.button(f"🔄 Indlæs Madplan #{plan_id}", key=f"load_{plan_id}"):
                        full_plan = get_meal_plan(plan_id)
                        if full_plan:
                            st.session_state.current_plan = {
                                "id": full_plan["id"],
                                "budget": full_plan["budget"],
                                "people_count": full_plan["people_count"],
                                "allergies": full_plan["allergies"],
                                "preferences": full_plan["preferences"],
                                "notes": full_plan["notes"],
                                "plan_data": full_plan["plan_data"],
                                "total_price": full_plan["total_estimated_price"]
                            }
                            if full_plan.get("shopping_list"):
                                st.session_state.current_shopping_list = full_plan["shopping_list"]["items"]
                            else:
                                st.session_state.current_shopping_list = aggregate_meal_plan_ingredients(full_plan["plan_data"])
                            st.session_state.checked_items = set()
                            st.success(f"Madplan #{plan_id} er indlæst! Skift til fanen '🍽️ Ugens Madplan' for at se den.")
                            st.rerun()

                with btn_col2:
                    if st.button(f"🗑️ Slet", key=f"del_{plan_id}"):
                        delete_meal_plan(plan_id)
                        st.warning(f"Madplan #{plan_id} blev slettet.")
                        st.rerun()


# ==========================================
# FANE 5: Netto Varekatalog
# ==========================================
with tab_catalog:
    st.subheader("🏪 Netto Varekatalog & Priser")
    st.markdown("Dette er det lokale Netto-katalog gemt i SQLite. Systemet slår ingredienser op heri for at beregne priser og pakkestørrelser.")
    
    catalog_items = get_all_netto_products()
    
    search_query = st.text_input("🔍 Søg i Netto varer...", placeholder="F.eks. mælk, hakket oksekød, pasta...")
    
    cat_filter = st.selectbox("Filtrér efter varekategori", ["Alle"] + sorted(list(set(i["category"] for i in catalog_items))))
    
    filtered = catalog_items
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = [x for x in filtered if q in x["name"].lower() or q in x["keywords"].lower()]
    if cat_filter != "Alle":
        filtered = [x for x in filtered if x["category"] == cat_filter]

    st.write(f"Viser **{len(filtered)}** af i alt {len(catalog_items)} Netto-produkter:")
    
    df = pd.DataFrame(filtered)[["id", "name", "category", "package_size", "unit", "price_dkk", "keywords"]]
    df.columns = ["ID", "Varenavn", "Kategori", "Pakkestørrelse", "Enhed", "Pris (DKK)", "Nøgleord"]
    
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Tilføj ny vare til Netto kataloget
    with st.expander("➕ Tilføj ny vare til Netto-kataloget"):
        with st.form("add_netto_item_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_name = st.text_input("Varenavn (f.eks. Økologiske Æbler)")
                new_cat = st.selectbox("Kategori", [
                    "Grønt & Frugt", "Kød & Fisk", "Mejeri & Køl", "Brød & Bageri",
                    "Kolonial", "Krydderier", "Frost", "Andet"
                ])
            with c2:
                new_size = st.number_input("Pakkestørrelse (mængde)", min_value=1.0, value=500.0, step=10.0)
                new_unit = st.selectbox("Enhed", ["g", "ml", "stk", "dåse", "pakke"])
            with c3:
                new_price = st.number_input("Pris i Netto (DKK)", min_value=0.5, value=19.95, step=0.5)
                new_keywords = st.text_input("Søgenøgleord (adskilt af komma)", placeholder="æbler, frugt, æble")
            
            submit_item = st.form_submit_button("Gem vare i Netto-katalog")
            if submit_item:
                if not new_name.strip():
                    st.error("Varenavn må ikke være tomt.")
                else:
                    add_netto_product(new_name.strip(), new_cat, new_size, new_unit, new_price, new_keywords.strip() or new_name.strip())
                    st.success(f"Varen '{new_name}' er tilføjet til Netto-databasen!")
                    st.rerun()
