# 🛒 Netto AI Madplanlægger

En fuldautomatisk og intelligent Python-applikation til ugentlig madplanlægning med Streamlit frontend, SQLite database og OpenAI API integration.

Appen hjælper dig med at planlægge aftensmad til 7 dage ud fra dit budget, antal personer i husstanden, allergier og kostpræferencer. Den samler automatisk alle ingredienser på tværs af ugens retter, fjerner dubletter, genererer én samlet indkøbsliste og beregner den præcise pris baseret på et lokalt Netto varekatalog.

---

## 🌟 Funktioner

- **🤖 OpenAI API integration**: Genererer varierede, velsmagende 7-dages madplaner med opskrifter, ingredienser og tilberedningstid tilpasset dine præferencer.
- **🧪 Indbygget Demo-tilstand**: Kan afprøves med det samme uden en OpenAI API-nøgle.
- **🥦 Smart ingrediens-aggregering**:
  - Samler alle ingredienser fra mandag til søndag.
  - Fjerner dubletter (hvis flere retter bruger f.eks. løg, oksekød eller mælk, lægges mængderne sammen).
  - Viser hvilke retter hver ingrediens indgår i.
- **🏷️ Lokal Netto-database (SQLite)**:
  - Indeholder over 70 typiske Netto-dagligvarer med realistiske priser og pakkestørrelser.
  - Beregner antal nødvendige pakker og totalpris for hele indkøbskurven.
  - Sammenligner automatisk den samlede pris med dit ugentlige budget.
- **📝 Interaktiv indkøbsliste**:
  - Organiseret efter Netto-kategori (Grønt & Frugt, Kød & Fisk, Mejeri, Kolonial, Frost osv.).
  - Afkrydsningsfelter, så du kan vinge varerne af mens du handler.
  - Download som tekstfil (`.txt`).
- **💾 Historik & Lagring**:
  - Gemmer automatisk genererede madplaner og indkøbslister i SQLite.
  - Genindlæs tidligere succesfulde madplaner med ét klik.
- **🏪 Netto Varekatalog-editor**:
  - Søg og filtrér i Netto-varer.
  - Tilføj nye varer eller tilpas priser til aktuelle tilbudsaviser.

---

## 🚀 Sådan starter du applikationen

### Hurtig start (Windows):
Dobbeltklik på filen:
```bat
run.bat
```

Eller kør via terminalen:
```powershell
cd C:\Users\Pierre\.gemini\antigravity\scratch\madplan_app
.\venv\Scripts\streamlit run app.py
```

Appen åbner automatisk i din browser på `http://localhost:8501`.

---

## ⚙️ Opsætning af OpenAI API

Du kan angive din OpenAI API-nøgle på to måder:
1. **Direkte i appens venstre sidepanel** (anbefalet ved hurtig brug).
2. **Som en miljøvariabel**:
   ```powershell
   $env:OPENAI_API_KEY = "sk-..."
   ```

Hvis der ikke er angivet en API-nøgle, slår appen automatisk over i **Demo-tilstand**, hvor den genererer en fuld, skræddersyet madplan baseret på dine valgte præferencer (antal personer, vegetar, budget osv.).

---

## 📁 Projektstruktur

```
madplan_app/
│
├── app.py                 # Streamlit frontend & UI
├── db.py                  # SQLite database, modeller & Netto varekatalog
├── meal_planner.py        # OpenAI API integration & prompt engineering
├── aggregator.py          # Sammenlægning af ingredienser & prisberegner
├── test_app.py            # Enhedstest (unittest)
├── requirements.txt       # Python afhængigheder
├── run.bat                # Start-script til Windows
└── README.md              # Dokumentation
```

---

## 🧪 Kørsel af tests

For at køre unittest-suiten:
```powershell
.\venv\Scripts\python test_app.py
```
Alle tests validerer database-seed, ingrediensmatching, samling af dubletter og prisberegning.
