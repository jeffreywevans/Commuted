# **Commuted**

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=jeffreywevans_Commuted)

---

## **📚 Commuted Archive Primer**  

*“This is not the story. This is how to *build* the story.”*

---

## **🗨️ INTRODUCTION**

Welcome. You’ve found the vault.

This is the official documentation archive of **Commuted**, the band that never stopped surviving. This project blends **fiction and fact, real people and invented moments**, and is filtered through a style best described as **sacred realism with a taste for sweat and feedback**.

The world exists from **1989 to 2032**, with jumps, skips, collapses, and comebacks in between. Avril Lavigne is real. So is Lyme disease. So is the time Kathy threw a hi-hat at Jeremy Evans and called him a “studio fascist.” Most of the rest is yours to decide.

---

## 🎯 ARCHIVE PURPOSE

This vault serves four key functions:
1. **Preservation** – What happened, who played, what burned down.
2. **Interpretation** – Why it mattered.
3. **Creation** – Scripts, data, and systems to add more.
4. **Navigation** – A map through the noise.

---

## **🤯 COMMON MISTAKES AND HOW TO AVOID THEM**

- There are two Jeremys.  There is Jeremy Evans and Jeremy Gilley, the band's **Mephistopheles**.  They are best friends.  Jeremy Gilley is nearly ubiquitously called Gilley.  
- There are two Evans brother characters.  There is Jeff Evans, the bassist, and Jeremy Evans, the lead guitar player.  Jeff's 18 months older.
- There are two Jeffs.  One is Jeff Evans, the bassist.  There is Jeff Cremeans, the band manager.  Jeff Cremeans is nearly ubiquitously called Cremeans.
- Yes, this was done on purpose.  

---

## **🧨 FINAL NOTE**

This project is alive. It is not just an archive. It is a breathing, snarling, fucked-up rock myth.

Treat it accordingly.

---

## ⚙️ Story brief generator configuration

The story brief generator (`commuted_calligraphy/story_brief/generate_story_brief.py`) supports one environment override:

- `COMMUTED_STORY_BRIEF_DATA_DIR`  
  Optional path to a directory containing `titles.json`, `entities.json`, `prompts.json`, and `config.json`.

### Data file resolution order

When generating a brief, data files are resolved in this order:

1. `COMMUTED_STORY_BRIEF_DATA_DIR` (best for custom/system deployments and mounted volumes).
2. Installed package resources under `commuted_calligraphy.story_brief.data` (best for packaged installs).
3. Repository-relative `commuted_calligraphy/story_brief/data` path (best for local development/source checkouts).

### Strict validation mode

For deeper dataset-health checks, run the generator with:

- `--validate-strict`

This performs per-date preflight checks across the configured date range to ensure each date has:
- at least one available setting, and
- at least two distinct available characters.

If strict validation fails, the generator exits early with a targeted error message.

### Linting with Ruff

Install development dependencies:

- `pip install -r requirements-dev.txt`

Run lint checks:

- `ruff check .`
