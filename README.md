# Self-Management Function (SMF)

SMF is a local study-planning app that turns a daily check-in into a realistic task plan. It considers goal importance, deadline pressure, current progress, available time, energy, concentration, stress, and study style to recommend how much work to do today.

For the product scope, decision model, formulas, research basis, and development priorities, see the [project planning document](planning.md).

The project includes two interfaces:

- `smf_visual_app.py` — the recommended Streamlit web interface
- `smf_app.py` — a simpler command-line interface

## Features

- Create and manage multiple academic goals
- Set deadlines, progress, normal daily workload, and task units
- Complete a daily wellbeing and availability check-in
- Receive an adaptive work mode such as **Lock In**, **Steady**, **Minimum**, **Recovery**, or **Catch-Up**
- Build a study-style profile and receive execution advice
- Track estimated progress and review check-in history
- Store all information locally in JSON and CSV files

The study-style profile is an app-specific planning aid inspired by educational psychology and cognitive science. It is not a diagnosis.

## Requirements

- Python 3.9 or newer
- `streamlit` and `pandas` for the visual app

## Installation

Clone or download the project, open a terminal in its directory, and optionally create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install streamlit pandas
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

## Run the visual app

```bash
streamlit run smf_visual_app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`. On first launch, complete the study-style test, add a goal, and use **Daily Check-In** to generate a plan.

## Run the command-line app

The terminal version uses only the Python standard library:

```bash
python3 smf_app.py
```

Choose an option from the menu to add goals, update progress, or perform a daily check-in.

## Local data

The apps create their data files in the directory from which they are run:

| File | Contents |
| --- | --- |
| `smf_goals.json` | Goal definitions and progress |
| `smf_state.json` | Most recent plan state |
| `smf_history.csv` | Daily check-in and plan history |
| `study_profile.json` | Study-style profile (visual app only) |

These files may contain personal check-in information. Keep them private and back them up if you want to preserve your history. To start fresh, close the app and remove the generated data files you no longer want.

## Project structure

```text
.
├── README.md
├── planning.md         # Product plan and SMF decision model
├── smf_app.py          # Command-line application
└── smf_visual_app.py   # Streamlit application
```

## How planning works

At a high level, SMF combines:

1. **Goal pressure** — importance, remaining progress, and time until the deadline
2. **Capacity** — available time, energy, concentration, stress, and readiness
3. **Burnout risk** — signals that the plan should be reduced or shifted toward recovery
4. **Study style** — adjustments to workload and advice for completing the task

The result is a suggested mode and task amount for the selected goal. Treat the recommendation as a planning prompt and adjust it when your circumstances require it.
