# Prompt-dokumentation: AI Madplanlægger

Dette dokument indeholder de originale prompts anvendt i udviklingen af *Netto AI Madplanlægger* via **Google Antigravity**. Udviklingen fulgte en specifikationsdrevet prompting-tilgang opdelt i faser, som beskrevet i rapportens kapitel 3 (*Udviklingsprocessen med AI som værktøj*).

---

## 1. Fase 1: Den indledende kravspecifikation (Prototype & Arkitektur)

**Formål:** At etablere projektets overordnede arkitektur (Separation of Concerns), UI, database og kernefunktioner i et enkelt samlet specifikationskald.

```text
Lav en Python-applikation til madplanlægning.

Krav:
- Streamlit frontend
- SQLite database
- OpenAI API integration

Bruger kan angive:
- Budget
- Antal personer
- Allergier
- Kostpræferencer

AI skal:
- Generere en 7-dages madplan

Systemet skal:
- Samle ingredienser fra alle retter
- Fjerne dubletter
- Generere én samlet indkøbsliste
- Beregne samlet pris baseret på en lokal Netto-database
- Gemme madplaner og indkøbslister
```

---

## 2. Fase 2: Studie- og Analysekrav (Kvalitetssikring & Evaluering)

**Formål:** At transformere prototypen fra blot at være en fungerende applikation til en akademisk case for softwarekvalitet, arkitekturforklaring og systematisk testbarhed.

```text
Udvikl en Python-applikation, som skal bruges som case i et studieprojekt om AI-assisteret softwareudvikling.

Formålet er ikke kun at skabe en fungerende Meal Planner, men at skabe et system, som kan analyseres og evalueres.

Derfor skal du:
1. Udvikle applikationen.
2. Dokumentere dine designvalg.
3. Forklare arkitekturen.
4. Beskrive database-strukturen.
5. Begrunde valg af teknologier.
6. Generere unit tests.
7. Beskrive potentielle svagheder i løsningen.
8. Dokumentere hvilke antagelser der er foretaget under udviklingen.

Applikationen skal bruges til at evaluere AI som softwareudvikler med fokus på:
- Funktionalitet
- Kodekvalitet
- Vedligeholdelighed
- AI's styrker og svagheder som udvikler

Meal Planner-funktionen er kun casen og ikke projektets primære fokus.
```

---

## 3. Fase 3: Refaktorering, Pydantic-validering & Defensiv Programmering

**Formål:** Udbedring af prototypens observerede svagheder (*The Illusion of Correctness*, ustrukturerede dictionaries, float-afrundinger og manglende API-nøgle fallback).

```text
Opdater koden med følgende udbedringer:
1. Domænevalidering: Indfør Pydantic v2 (models.py) til at validere OpenAI JSON-outputtet, så negative tal og 0-mængder kastes som kontrollerede fejl (ValidationError).
2. Forretningsmatematik: Implementer loftsberegning (math.ceil) i aggregator.py til beregning af hele pakker mod Netto-katalogets pakkestørrelser, samt normalisering af enheder (kg -> g, dl -> ml).
3. Graceful Degradation: Tilføj en offline fallback generator (demo-tilstand), hvis OpenAI API-nøglen mangler, så systemet altid kan afvikles deterministisk.
4. Testsuite: Udvid til 12 systematiske unit tests i test_app.py til verifikation af dataintegritet, kaskadesletning og grænseværdier.
```

---

*Repository:* [https://github.com/PierreHulstrom/AI-madplan](https://github.com/PierreHulstrom/AI-madplan)  
*Forfattere:* Pierre & Andreas  
*Kursus:* Programmering og AI, Erhvervsakademi Sjælland (Zealand)
