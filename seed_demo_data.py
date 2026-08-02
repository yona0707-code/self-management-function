"""Create a deterministic three-month demo dataset for the Streamlit app.

Run with ``python3 seed_demo_data.py``. Existing app data is preserved unless
``--force`` is supplied.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GOALS_FILE = ROOT / "smf_goals.json"
STATE_FILE = ROOT / "smf_state.json"
HISTORY_FILE = ROOT / "smf_history.csv"

HISTORY_FIELDS = [
    "date", "goal_id", "goal_name", "completion_status", "stress", "energy",
    "concentration", "mood", "readiness", "available_minutes",
    "normal_goal_minutes", "time_fit", "style_adjustment",
    "style_task_multiplier", "final_multiplier", "has_fun_plan", "fun_plan",
    "mode", "capacity", "burnout_risk", "goal_pressure", "task",
    "progress_update",
]

GOAL_TEMPLATES = [
    ("Achieve 1500+ on the SAT", 10, 120, "complete timed SAT questions", 35, "questions", 75),
    ("Earn A*s in A-Level Mathematics and Physics", 10, 210, "solve past-paper problems", 12, "problems", 90),
    ("Build and launch a university portfolio app", 9, 150, "work on the portfolio app", 75, "minutes", 75),
    ("Complete five university application essays", 9, 105, "draft or revise application essays", 500, "words", 60),
    ("Submit a competitive scholarship application", 8, 75, "research and prepare scholarship materials", 45, "minutes", 45),
]

FUN_PLANS = [
    "Dinner with family at 7pm", "Basketball with friends at 6pm",
    "Watch a movie at 8pm", "Coffee with a friend after class",
    "Gaming session at 9pm", "Evening walk at the park",
]

RANDOM_SEED = 20260802


def phase_probabilities(day_index: int) -> tuple[float, float, float]:
    """Return completed, partial, and skipped odds for a point in the demo."""
    if day_index < 28:  # An uneven start while the student finds a routine.
        return (0.43, 0.32, 0.25)
    if day_index < 55:  # Improvement is gradual rather than a sudden step.
        improvement = (day_index - 28) / 26
        return (
            0.50 + 0.20 * improvement,
            0.31 - 0.07 * improvement,
            0.19 - 0.13 * improvement,
        )
    if day_index < 62:  # A stressful week disrupts the developing routine.
        return (0.27, 0.41, 0.32)
    # The recovered routine is stronger, but still has believable off-days.
    return (0.76, 0.19, 0.05)


def choose_status(
    rng: random.Random,
    probabilities: tuple[float, float, float],
    ability_shift: float,
    weekend: bool,
    yesterday_status: str | None,
) -> str:
    completed, partial, skipped = probabilities
    completed += ability_shift
    skipped -= ability_shift * 0.65

    # Weekends and yesterday's outcome add small, non-periodic behavioral effects.
    if weekend:
        completed -= 0.05
        partial += 0.02
        skipped += 0.03
    if yesterday_status == "Skipped":
        completed -= 0.04
        partial += 0.03
        skipped += 0.01
    elif yesterday_status == "Completed":
        completed += 0.025
        skipped -= 0.015

    weights = [max(0.01, completed), max(0.01, partial), max(0.01, skipped)]
    return rng.choices(
        ["Completed", "Partly completed", "Skipped"],
        weights=weights,
        k=1,
    )[0]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def rounded(value: float) -> float:
    return round(value, 3)


def create_data(today: date) -> tuple[list[dict], dict, list[dict]]:
    rng = random.Random(RANDOM_SEED)
    start = today - timedelta(days=89)
    deadlines = [today + timedelta(days=template[2]) for template in GOAL_TEMPLATES]
    goals = []
    rows = []
    latest_by_goal = {}
    progress = [0.0] * len(GOAL_TEMPLATES)
    previous_status = [None] * len(GOAL_TEMPLATES)
    ability_shifts = [rng.uniform(-0.055, 0.055) for _ in GOAL_TEMPLATES]

    for goal_id, (name, importance, _, action, amount, unit, minutes) in enumerate(GOAL_TEMPLATES, 1):
        goals.append({
            "id": goal_id,
            "goal_name": name,
            "importance": importance,
            "deadline": deadlines[goal_id - 1].isoformat(),
            "start_date": start.isoformat(),
            "current_progress": 0.0,
            "estimated_progress": 0.0,
            "main_action": action,
            "normal_amount": amount,
            "unit": unit,
            "normal_goal_minutes": minutes,
        })

    # One observation per goal per day supports an honest seven-day trend.
    for day_index in range(90):
        check_date = start + timedelta(days=day_index)
        for goal_index, goal in enumerate(goals):
            weekend = check_date.weekday() >= 5
            status = choose_status(
                rng,
                phase_probabilities(day_index),
                ability_shifts[goal_index],
                weekend,
                previous_status[goal_index],
            )
            previous_status[goal_index] = status

            gain = {"Completed": 1.0, "Partly completed": 0.4, "Skipped": 0.0}[status]
            old_progress = progress[goal_index]
            progress[goal_index] = rounded(old_progress + gain)

            stressful_week = 55 <= day_index < 62
            stress = clamp(rng.gauss(0.47 + (0.22 if stressful_week else 0) + (0.08 if status == "Skipped" else 0), 0.09), 0.1, 0.95)
            energy = clamp(rng.gauss(0.66 - (0.15 if stressful_week else 0) - (0.07 if weekend else 0), 0.08), 0.1, 0.95)
            concentration = clamp(rng.gauss(0.69 - (0.17 if stressful_week else 0) - (0.12 if status == "Skipped" else 0), 0.08), 0.1, 0.95)
            mood = clamp(rng.gauss(0.67 - (0.13 if stressful_week else 0), 0.09), 0.1, 0.95)
            readiness = clamp((energy + concentration) / 2 - (0.1 if status == "Skipped" else 0), 0.1, 0.9)
            available = rng.choices([30, 45, 60, 90, 120], weights=[10, 15, 30, 28, 17], k=1)[0]
            time_fit = clamp(available / goal["normal_goal_minutes"], 0, 1.5)
            capacity = time_fit * energy * concentration * readiness * (1 - 0.6 * stress)
            burnout = 0.45 * stress**2 + 0.2 * (1 - mood) + 0.2 * (1 - energy) + 0.15 * (1 - readiness)
            days_left = max(1, (deadlines[goal_index] - check_date).days)
            pressure = clamp(((goal["importance"] / 10) * ((100 - old_progress) / days_left)) / 1.5, 0, 1)

            if status == "Skipped" and burnout < 0.65:
                mode, multiplier = "CATCH-UP", 1.2
            elif burnout > 0.62 and pressure < 0.72:
                mode, multiplier = "RECOVERY", 0.15
            elif capacity < 0.2:
                mode, multiplier = "MINIMUM", 0.35
            elif pressure > 0.7 and capacity > 0.35:
                mode, multiplier = "LOCK IN", 1.2
            else:
                mode, multiplier = "STEADY", 1.0

            planned_amount = round(goal["normal_amount"] * multiplier)
            has_plan = rng.random() < 0.42
            timestamp = datetime.combine(check_date, time(17 + goal_index, rng.choice([5, 15, 30, 45]))).strftime("%Y-%m-%d %H:%M:%S")
            task = f"{goal['main_action'].capitalize()}: {planned_amount} {goal['unit']}."
            update = ""
            if gain:
                update = json.dumps({
                    "goal_id": goal["id"], "goal_name": goal["goal_name"],
                    "old_progress": old_progress, "new_progress": progress[goal_index], "gain": gain,
                })

            row = {
                "date": timestamp, "goal_id": goal["id"], "goal_name": goal["goal_name"],
                "completion_status": status, "stress": rounded(stress), "energy": rounded(energy),
                "concentration": rounded(concentration), "mood": rounded(mood),
                "readiness": rounded(readiness), "available_minutes": available,
                "normal_goal_minutes": goal["normal_goal_minutes"], "time_fit": rounded(time_fit),
                "style_adjustment": 1.0, "style_task_multiplier": 1.0,
                "final_multiplier": multiplier, "has_fun_plan": has_plan,
                "fun_plan": rng.choice(FUN_PLANS) if has_plan else "",
                "mode": mode, "capacity": rounded(capacity), "burnout_risk": rounded(burnout),
                "goal_pressure": rounded(pressure), "task": task, "progress_update": update,
            }
            rows.append(row)
            latest_by_goal[str(goal["id"])] = {
                "task_sentence": task,
                "task_structured": {"goal_id": goal["id"], "goal_name": goal["goal_name"],
                                    "task_sentence": task, "amount": planned_amount,
                                    "unit": goal["unit"], "pressure": rounded(pressure)},
                "mode": mode, "date": timestamp, "plan_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, timestamp + goal["goal_name"])),
                "progress_applied_plan_id": "demo-data",
            }

    for index, goal in enumerate(goals):
        goal["current_progress"] = progress[index]
        goal["estimated_progress"] = progress[index]

    return goals, {"last_task_by_goal": latest_by_goal}, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace existing app data")
    args = parser.parse_args()
    existing = [path for path in (GOALS_FILE, STATE_FILE, HISTORY_FILE) if path.exists()]
    if existing and not args.force:
        names = ", ".join(path.name for path in existing)
        raise SystemExit(f"Refusing to replace {names}. Re-run with --force if intended.")

    goals, state, rows = create_data(date.today())
    GOALS_FILE.write_text(json.dumps(goals, indent=4) + "\n")
    STATE_FILE.write_text(json.dumps(state, indent=4) + "\n")
    with HISTORY_FILE.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HISTORY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Created {len(goals)} goals and {len(rows)} check-ins from {rows[0]['date'][:10]} to {rows[-1]['date'][:10]}.")


if __name__ == "__main__":
    main()
