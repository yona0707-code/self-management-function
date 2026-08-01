# Self-Management Function App
# Version 18: Study Style Adjusted SMF + About Study Style Test inside Profile
#
# Main screen:
#   1. Daily Check-In
#   2. Add New Goal
#
# Sidebar:
#   - What is SMF(x)?
#   - Study Style Profile
#   - View Goal Tabs
#   - Check Progress
#   - Delete Goal Tab
#   - History
#
# Core idea:
#   The user checks in for ONE academic goal at a time.
#   SMF decides today's mode and task amount.
#   Study Style Profile affects the function itself:
#       1. It adjusts capacity.
#       2. It adjusts the final task amount.
#       3. It gives advice on how to execute the task.
#
# Important:
#   The Study Style Test is NOT a diagnosis.
#   It is an app-specific profile inspired by educational psychology and cognitive science.


import streamlit as st
from pathlib import Path
from datetime import date, datetime
import json
import csv
import math
import uuid
import pandas as pd


GOALS_FILE = Path("smf_goals.json")
STATE_FILE = Path("smf_state.json")
HISTORY_FILE = Path("smf_history.csv")
STUDY_PROFILE_FILE = Path("study_profile.json")


MODE_LABELS = {
    "LOCK IN": "🔒 LOCK IN",
    "STEADY": "🌿 STEADY",
    "MINIMUM": "🟡 MINIMUM",
    "RECOVERY": "🛌 RECOVERY",
    "CATCH-UP": "🔁 CATCH-UP"
}


SOURCES = [
    {
        "title": "Motivated Strategies for Learning Questionnaire (MSLQ)",
        "url": "https://files.eric.ed.gov/fulltext/ED338122.pdf",
        "used_for": "Self-regulated learning, metacognitive self-regulation, effort regulation, time/study environment, and learning strategies."
    },
    {
        "title": "Zimmerman (2002), Becoming a Self-Regulated Learner: An Overview",
        "url": "https://www.tandfonline.com/doi/abs/10.1207/s15430421tip4102_2",
        "used_for": "The idea that learners plan, perform, monitor, and reflect on their learning."
    },
    {
        "title": "Cognitive Load Theory and instructional design",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12246501/",
        "used_for": "The idea that working memory is limited and tasks can become mentally overloaded."
    },
    {
        "title": "Sustained Attention overview",
        "url": "https://www.sciencedirect.com/topics/psychology/sustained-attention",
        "used_for": "The idea of maintaining focus and engagement toward a task over time."
    },
    {
        "title": "Cognitive Load Theory and individual differences",
        "url": "https://www.sciencedirect.com/science/article/pii/S1041608024000165",
        "used_for": "The idea that cognitive load and learning design interact with individual differences."
    }
]


def mode_label(mode):
    return MODE_LABELS.get(mode, mode)


def score_percent(value):
    return f"{round(value * 100)}%"


def score_level(value):
    if value < 0.35:
        return "Low"
    elif value < 0.65:
        return "Medium"
    else:
        return "High"


def score_display(value):
    return f"{score_percent(value)} — {score_level(value)}"


# ----------------------------
# Basic helpers
# ----------------------------

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def load_json(path, default):
    if not path.exists():
        return default

    with open(path, "r") as file:
        return json.load(file)


def save_json(path, data):
    with open(path, "w") as file:
        json.dump(data, file, indent=4)


def load_study_profile():
    return load_json(STUDY_PROFILE_FILE, None)


def save_study_profile(profile):
    save_json(STUDY_PROFILE_FILE, profile)


def estimate_normal_minutes_from_old_goal(goal):
    unit = goal.get("unit", "").lower()
    normal_amount = goal.get("normal_amount", 60)

    if "minute" in unit:
        return int(normal_amount)

    return 60


def load_goals():
    goals = load_json(GOALS_FILE, [])

    for goal in goals:
        if "estimated_progress" not in goal:
            goal["estimated_progress"] = goal.get("current_progress", 0)

        if "current_progress" not in goal:
            goal["current_progress"] = goal.get("estimated_progress", 0)

        if "normal_goal_minutes" not in goal:
            goal["normal_goal_minutes"] = estimate_normal_minutes_from_old_goal(goal)

    return goals


def save_goals(goals):
    save_json(GOALS_FILE, goals)


def load_state():
    state = load_json(
        STATE_FILE,
        {
            "last_task_by_goal": {}
        }
    )

    if "last_task_by_goal" not in state:
        state["last_task_by_goal"] = {}

    return state


def save_state(state):
    save_json(STATE_FILE, state)


def append_history(data):
    file_exists = HISTORY_FILE.exists()

    with open(HISTORY_FILE, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)


def read_history():
    if not HISTORY_FILE.exists():
        return []

    with open(HISTORY_FILE, "r") as file:
        return list(csv.DictReader(file))


def days_until(deadline_text):
    deadline = date.fromisoformat(deadline_text)
    today = date.today()
    return max(1, (deadline - today).days)


def get_next_goal_id(goals):
    if not goals:
        return 1
    return max(goal["id"] for goal in goals) + 1


def time_label_to_minutes(label):
    mapping = {
        "15 min": 15,
        "30 min": 30,
        "1 hour": 60,
        "2 hours": 120,
        "3+ hours": 180
    }
    return mapping[label]


def mbti_scale(title, options, key):
    labels = [item[0] for item in options]
    values = {item[0]: item[1] for item in options}

    choice = st.radio(
        title,
        labels,
        index=2,
        horizontal=True,
        key=key
    )

    return values[choice]


# ----------------------------
# Study Style Test
# ----------------------------

LIKERT_OPTIONS = [
    ("Strongly disagree", 1),
    ("Disagree", 2),
    ("Neutral", 3),
    ("Agree", 4),
    ("Strongly agree", 5)
]


STUDY_STYLE_QUESTIONS = [
    {
        "id": "q1",
        "text": "I can stay focused for a long time once I get into the task.",
        "dimension": "focus_endurance"
    },
    {
        "id": "q2",
        "text": "I work better when I study in short blocks with breaks.",
        "dimension": "sprint_preference"
    },
    {
        "id": "q3",
        "text": "Starting a task is usually harder than continuing it.",
        "dimension": "start_difficulty"
    },
    {
        "id": "q4",
        "text": "I often delay tasks even when I know they are important.",
        "dimension": "start_difficulty"
    },
    {
        "id": "q5",
        "text": "I usually know which study method works best for me.",
        "dimension": "metacognitive_regulation"
    },
    {
        "id": "q6",
        "text": "After studying, I think about what worked and what did not.",
        "dimension": "metacognitive_regulation"
    },
    {
        "id": "q7",
        "text": "I feel overwhelmed when a task has too many steps at once.",
        "dimension": "cognitive_load_sensitivity"
    },
    {
        "id": "q8",
        "text": "I focus better when a task is broken into small clear steps.",
        "dimension": "cognitive_load_sensitivity"
    },
    {
        "id": "q9",
        "text": "I often touch a pen, my face, hair, or objects while studying.",
        "dimension": "motor_sensory_regulation"
    },
    {
        "id": "q10",
        "text": "Having something harmless to hold, like a pen or stress ball, helps me focus.",
        "dimension": "motor_sensory_regulation"
    }
]


def normalize_likert_average(values):
    if not values:
        return 0.5

    average = sum(values) / len(values)

    # 1 to 5 becomes 0 to 1.
    return (average - 1) / 4


def profile_level(value):
    if value < 0.35:
        return "Low"
    elif value < 0.65:
        return "Medium"
    else:
        return "High"


def infer_focus_style(profile):
    sprint = profile["sprint_preference"]
    endurance = profile["focus_endurance"]

    if sprint > endurance + 0.15:
        return "Sprint Focus"
    elif endurance > sprint + 0.15:
        return "Deep Focus"
    else:
        return "Flexible Focus"


def build_study_profile(answers):
    grouped = {}

    for question in STUDY_STYLE_QUESTIONS:
        dimension = question["dimension"]
        answer_value = answers[question["id"]]
        grouped.setdefault(dimension, []).append(answer_value)

    profile = {}

    for dimension, values in grouped.items():
        profile[dimension] = normalize_likert_average(values)

    profile["focus_style"] = infer_focus_style(profile)
    profile["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return profile


def get_study_style_recommendations(profile):
    recommendations = []

    focus_style = profile.get("focus_style", "Flexible Focus")

    if focus_style == "Sprint Focus":
        recommendations.append("Use short focus blocks, such as 15–30 minutes, with short breaks.")
    elif focus_style == "Deep Focus":
        recommendations.append("Use longer focus blocks when possible, such as 45–90 minutes.")
    else:
        recommendations.append("Use flexible blocks. Start with 25–30 minutes and adjust based on the task.")

    if profile.get("start_difficulty", 0.5) >= 0.65:
        recommendations.append("Start with a very small first step, such as a 5-minute warm-up task.")

    if profile.get("cognitive_load_sensitivity", 0.5) >= 0.65:
        recommendations.append("Break large tasks into small visible steps before starting.")

    if profile.get("motor_sensory_regulation", 0.5) >= 0.65:
        recommendations.append("Use a pen, stress ball, or harmless object while studying. Avoid using your phone as a fidget object.")

    if profile.get("metacognitive_regulation", 0.5) < 0.40:
        recommendations.append("After studying, write one sentence about what worked and what did not.")

    return recommendations


def calculate_style_adjustment(profile, time_fit, concentration, readiness):
    """
    Adjusts capacity using the user's Study Style Profile.

    Study style should influence the function, but not completely control it.
    Therefore, this adjustment is limited between 70% and 110%.
    """

    if not profile:
        return 1.0

    start_difficulty = profile.get("start_difficulty", 0.5)
    cognitive_load = profile.get("cognitive_load_sensitivity", 0.5)
    focus_endurance = profile.get("focus_endurance", 0.5)

    style_adjustment = (
        1
        - 0.15 * start_difficulty * (1 - readiness)
        - 0.05 * cognitive_load * (1 - concentration)
        + 0.05 * focus_endurance * time_fit
    )

    return clamp(style_adjustment, 0.70, 1.10)


def calculate_style_task_multiplier(profile, mode, capacity, readiness, concentration):
    """
    Fine-tunes the task amount using the Study Style Profile.

    The mode multiplier decides the main task size.
    The study style multiplier only fine-tunes it.
    """

    if not profile:
        return 1.0

    start_difficulty = profile.get("start_difficulty", 0.5)
    focus_endurance = profile.get("focus_endurance", 0.5)

    multiplier = 1.0

    if start_difficulty >= 0.65 and readiness <= 0.4:
        multiplier *= 0.85

    if focus_endurance >= 0.65 and mode == "LOCK IN" and capacity >= 0.65:
        multiplier *= 1.10

    return clamp(multiplier, 0.80, 1.15)


def generate_execution_advice(profile, mode, task, goal):
    if not profile:
        return ["Start with the task as written. Adjust the method if it feels too hard."]

    advice = []

    focus_style = profile.get("focus_style", "Flexible Focus")
    metacognition = profile.get("metacognitive_regulation", 0.5)
    cognitive_load = profile.get("cognitive_load_sensitivity", 0.5)
    sensory = profile.get("motor_sensory_regulation", 0.5)
    amount = task["amount"]
    unit = task["unit"].lower()

    if focus_style == "Sprint Focus":
        if "minute" in unit:
            advice.append("Split the task into short work blocks with short breaks.")
        else:
            if amount >= 10:
                rounds = 3
                per_round = max(1, math.ceil(amount / rounds))
                advice.append(f"Split the task into about {rounds} rounds of {per_round} {task['unit']} each.")
            else:
                advice.append("Do the task in one small round, then take a short break.")
    elif focus_style == "Deep Focus":
        advice.append("Try to do the task in one focused block before switching activities.")
    else:
        advice.append("Start with one focused block. If focus drops, split the task into smaller rounds.")

    if profile.get("start_difficulty", 0.5) >= 0.65:
        advice.append("Before the full task, do a 5-minute starter step just to begin.")

    if metacognition >= 0.65:
        advice.append("Use your own preferred study method. At the end, briefly check whether it worked.")
    elif metacognition < 0.40:
        advice.append("Use a simple structure: start with the easiest part, work for one block, then write one sentence about what to improve next time.")
    else:
        advice.append("Use your own method first. If you feel stuck, break the task into smaller steps.")

    if cognitive_load >= 0.65:
        advice.append("Keep the instructions visually simple. Write only the next 2–3 steps, not the whole plan.")

    if sensory >= 0.65:
        advice.append("Use a pen or stress ball while studying. Avoid touching your phone.")

    if mode in ["MINIMUM", "RECOVERY"]:
        advice.append("Keep the task small on purpose. The goal is to stay connected, not to force maximum effort.")

    return advice


# ----------------------------
# Estimated progress logic
# ----------------------------

def progress_gain_from_completion(completion_status):
    if completion_status == "Completed":
        return 1.0

    if completion_status == "Partly completed":
        return 0.4

    return 0.0


def completion_score(completion_status):
    if completion_status == "Completed":
        return 100

    if completion_status == "Partly completed":
        return 40

    return 0


def find_goal_by_id(goals, goal_id):
    for goal in goals:
        if goal["id"] == goal_id:
            return goal
    return None


def apply_estimated_progress_for_goal(goals, state, selected_goal_id, completion_status):
    goal_key = str(selected_goal_id)
    last_task_by_goal = state.get("last_task_by_goal", {})
    last_goal_state = last_task_by_goal.get(goal_key)

    if not last_goal_state:
        return goals, None, state

    last_plan_id = last_goal_state.get("plan_id", "")
    applied_plan_id = last_goal_state.get("progress_applied_plan_id", "")

    if not last_plan_id:
        return goals, None, state

    if last_plan_id == applied_plan_id:
        return goals, None, state

    gain = progress_gain_from_completion(completion_status)
    goal = find_goal_by_id(goals, selected_goal_id)

    if goal is None:
        return goals, None, state

    update = None

    if gain > 0:
        old_progress = goal.get("estimated_progress", 0)
        new_progress = clamp(old_progress + gain, 0, 100)

        goal["estimated_progress"] = new_progress
        goal["current_progress"] = new_progress

        update = {
            "goal_id": selected_goal_id,
            "goal_name": goal["goal_name"],
            "old_progress": old_progress,
            "new_progress": new_progress,
            "gain": gain
        }

    last_goal_state["progress_applied_plan_id"] = last_plan_id
    last_task_by_goal[goal_key] = last_goal_state
    state["last_task_by_goal"] = last_task_by_goal

    return goals, update, state


# ----------------------------
# Self-Management Function
# ----------------------------

def calculate_goal_pressure(goal):
    importance = goal["importance"] / 10
    progress = goal.get("estimated_progress", 0)
    days_left = days_until(goal["deadline"])

    remaining_progress = 100 - progress
    daily_progress_needed = remaining_progress / days_left

    high_pressure_rate = 1.5
    goal_pressure = importance * daily_progress_needed / high_pressure_rate
    goal_pressure = clamp(goal_pressure, 0, 1)

    return goal_pressure, remaining_progress, daily_progress_needed, days_left


def calculate_capacity(available_minutes, normal_goal_minutes, energy, concentration, stress, readiness, profile=None):
    """
    Capacity:
    C = time_fit × energy × concentration × readiness × stress_adjustment × style_adjustment
    """

    normal_goal_minutes = max(1, normal_goal_minutes)

    time_fit = clamp(available_minutes / normal_goal_minutes, 0, 1)

    stress_penalty_weight = 0.6
    stress_adjustment = 1 - (stress_penalty_weight * stress)
    stress_adjustment = clamp(stress_adjustment, 0.2, 1)

    style_adjustment = calculate_style_adjustment(
        profile,
        time_fit,
        concentration,
        readiness
    )

    capacity = (
        time_fit
        * energy
        * concentration
        * readiness
        * stress_adjustment
        * style_adjustment
    )

    capacity = clamp(capacity, 0, 1)

    return capacity, time_fit, style_adjustment


def calculate_burnout_risk(stress, mood, energy, readiness):
    low_mood = 1 - mood
    low_energy = 1 - energy
    low_readiness = 1 - readiness

    burnout_risk = (
        0.45 * (stress ** 2)
        + 0.20 * low_mood
        + 0.20 * low_energy
        + 0.15 * low_readiness
    )

    return clamp(burnout_risk, 0, 1)


def decide_mode(goal_pressure, capacity, burnout_risk, completion_status):
    if completion_status == "Skipped" and burnout_risk < 0.65:
        return "CATCH-UP"

    if goal_pressure >= 0.65 and burnout_risk < 0.60 and capacity >= 0.35:
        return "LOCK IN"

    if goal_pressure >= 0.65 and burnout_risk >= 0.60:
        return "MINIMUM"

    if goal_pressure < 0.45 and burnout_risk >= 0.65:
        return "RECOVERY"

    if capacity < 0.30 and burnout_risk >= 0.55:
        return "MINIMUM"

    return "STEADY"


def get_mode_multiplier(mode):
    if mode == "LOCK IN":
        return 1.20

    if mode == "STEADY":
        return 1.00

    if mode == "MINIMUM":
        return 0.35

    if mode == "RECOVERY":
        return 0.15

    if mode == "CATCH-UP":
        return 1.20

    return 1.00


def calculate_task_amount(normal_amount, unit, multiplier):
    amount = math.ceil(normal_amount * multiplier)
    amount = max(1, amount)

    if "minute" in unit.lower() and amount >= 5:
        amount = int(math.ceil(amount / 5) * 5)

    return amount


def create_task_sentence(goal, amount):
    return f"{goal['goal_name']}: {goal['main_action']} — {amount} {goal['unit']}"


def get_mode_explanation(mode):
    if mode == "LOCK IN":
        return (
            "Goal pressure is high and your condition is good enough to push. "
            "Today should be a focused progress day."
        )

    if mode == "STEADY":
        return (
            "Your situation is stable. Today should be a normal progress day "
            "without overloading yourself."
        )

    if mode == "MINIMUM":
        return (
            "This goal still matters, but stress, readiness, or low capacity makes a large task risky. "
            "Today should protect progress with a smaller task."
        )

    if mode == "RECOVERY":
        return (
            "Burnout risk is high and goal pressure is not extreme. "
            "Recovery is allowed, but you should still keep a tiny connection to this goal."
        )

    if mode == "CATCH-UP":
        return (
            "You skipped this goal recently, but burnout risk is not too high. "
            "Today should include a small catch-up, not a punishment."
        )

    return "No explanation available."


def get_relaxation_advice(mode, has_fun_plan, fun_plan):
    if not has_fun_plan:
        if mode == "RECOVERY":
            return (
                "Plan a clean recovery activity today, such as a walk, movie, or relaxing meal. "
                "Avoid addictive activities that make tomorrow worse."
            )
        return "No special relaxation plan entered."

    plan_text = f"Your plan: {fun_plan}."

    if mode == "LOCK IN":
        return (
            f"{plan_text} You can still relax, but complete this goal's main task first. "
            "Avoid relaxing too early if it usually makes you lose momentum."
        )

    if mode == "STEADY":
        return (
            f"{plan_text} This is okay. Complete this goal's planned task first so you can relax without guilt."
        )

    if mode == "MINIMUM":
        return (
            f"{plan_text} This is okay, but complete the minimum task first. "
            "The point is to protect your connection with this goal."
        )

    if mode == "RECOVERY":
        return (
            f"{plan_text} This may help recovery. Choose relaxation that restores you, "
            "not something that makes tomorrow worse."
        )

    if mode == "CATCH-UP":
        return (
            f"{plan_text} Do the catch-up task before going out. "
            "Do not cancel all relaxation, but protect this goal first."
        )

    return "No relaxation advice available."


def generate_single_goal_plan(goal, check_in, profile=None):
    pressure, remaining, daily_needed, days_left = calculate_goal_pressure(goal)

    capacity, time_fit, style_adjustment = calculate_capacity(
        check_in["available_minutes"],
        goal["normal_goal_minutes"],
        check_in["energy"],
        check_in["concentration"],
        check_in["stress"],
        check_in["readiness"],
        profile
    )

    burnout_risk = calculate_burnout_risk(
        check_in["stress"],
        check_in["mood"],
        check_in["energy"],
        check_in["readiness"]
    )

    mode = decide_mode(
        pressure,
        capacity,
        burnout_risk,
        check_in["completion_status"]
    )

    mode_multiplier = get_mode_multiplier(mode)

    style_task_multiplier = calculate_style_task_multiplier(
        profile,
        mode,
        capacity,
        check_in["readiness"],
        check_in["concentration"]
    )

    final_multiplier = mode_multiplier * style_task_multiplier

    amount = calculate_task_amount(
        goal["normal_amount"],
        goal["unit"],
        final_multiplier
    )

    task = {
        "goal_id": goal["id"],
        "goal_name": goal["goal_name"],
        "task_sentence": create_task_sentence(goal, amount),
        "amount": amount,
        "unit": goal["unit"],
        "pressure": pressure
    }

    return {
        "mode": mode,
        "task": task,
        "goal_pressure": pressure,
        "remaining": remaining,
        "daily_needed": daily_needed,
        "days_left": days_left,
        "capacity": capacity,
        "time_fit": time_fit,
        "style_adjustment": style_adjustment,
        "style_task_multiplier": style_task_multiplier,
        "final_multiplier": final_multiplier,
        "burnout_risk": burnout_risk,
        "explanation": get_mode_explanation(mode),
        "relaxation_advice": get_relaxation_advice(
            mode,
            check_in["has_fun_plan"],
            check_in["fun_plan"]
        )
    }


# ----------------------------
# Progress evidence and consistency
# ----------------------------

def get_recent_progress_evidence(goal_name, limit=5):
    history = read_history()
    evidence = []

    for item in history:
        updates_text = item.get("progress_update", "")

        if not updates_text:
            continue

        try:
            update = json.loads(updates_text)
        except json.JSONDecodeError:
            continue

        if update and update.get("goal_name") == goal_name:
            evidence.append({
                "date": item.get("date", ""),
                "old_progress": update.get("old_progress", 0),
                "new_progress": update.get("new_progress", 0),
                "gain": update.get("gain", 0)
            })

    return list(reversed(evidence[-limit:]))


def get_consistency_data(goal_name, limit=14):
    history = read_history()
    rows = []

    for item in history:
        if item.get("goal_name", "") != goal_name:
            continue

        completion_status = item.get("completion_status", "")

        if not completion_status:
            continue

        date_text = item.get("date", "")

        try:
            date_label = datetime.strptime(
                date_text,
                "%Y-%m-%d %H:%M:%S"
            ).strftime("%b %d")
        except ValueError:
            date_label = date_text

        rows.append({
            "Day": date_label,
            "Completion": completion_score(completion_status)
        })

    return rows[-limit:]


# ----------------------------
# UI screens
# ----------------------------

def render_study_style_test():
    st.title("Study Style Test")

    st.write(
        "This short test helps the app understand how you tend to study. "
        "It is not a diagnosis. It is used only to personalize study methods."
    )

    st.info(
        "The questions are inspired by concepts from educational psychology and cognitive science, "
        "such as sustained attention, self-regulated learning, metacognition, cognitive load, and effort regulation."
    )

    st.markdown("---")

    answers = {}

    with st.form("study_style_test_form"):
        for index, question in enumerate(STUDY_STYLE_QUESTIONS, start=1):
            st.markdown(f"**{index}. {question['text']}**")

            value = mbti_scale(
                "",
                LIKERT_OPTIONS,
                key=f"study_test_{question['id']}"
            )

            answers[question["id"]] = value

        submitted = st.form_submit_button("Create Study Style Profile")

        if submitted:
            profile = build_study_profile(answers)
            save_study_profile(profile)

            st.success("Study Style Profile created.")

            goals = load_goals()
            if not goals:
                st.session_state["screen"] = "add_goal"
            else:
                st.session_state["screen"] = "profile"

            st.rerun()


def render_about_study_style_test():
    st.subheader("About the Study Style Test")

    st.write(
        "This test is not a clinical or diagnostic test. "
        "It is a lightweight study-style profile inspired by cognitive science "
        "and educational psychology."
    )

    st.write(
        "The purpose is not to label the user. "
        "The purpose is to help the app decide how much structure, guidance, "
        "and task breakdown the user may need when studying."
    )

    st.markdown("### What the factors are based on")

    st.markdown(
        """
        | App factor | Professional basis | How the app uses it |
        |---|---|---|
        | **Focus endurance** | Sustained attention | Helps decide whether longer focus blocks are realistic. |
        | **Sprint preference** | Self-regulated learning / time management | Helps decide whether tasks should be split into short blocks. |
        | **Start difficulty** | Effort regulation / academic procrastination | Helps decide whether the app should suggest a small starter step. |
        | **Metacognitive regulation** | Metacognition / self-regulated learning | Helps decide how much guidance the app should give. |
        | **Cognitive load sensitivity** | Cognitive Load Theory | Helps decide whether tasks should be presented as small visible steps. |
        | **Motor/sensory regulation** | Study-behavior observation | Helps decide whether to suggest a harmless object like a pen or stress ball. |
        """
    )

    st.markdown("### Sources")

    for source in SOURCES:
        st.markdown(f"**{source['title']}**")
        st.write(source["used_for"])
        st.markdown(f"[Open source]({source['url']})")
        st.write("")


def render_profile():
    st.title("Study Style Profile")

    profile = load_study_profile()

    if not profile:
        st.warning("No Study Style Profile found.")
        if st.button("Take Study Style Test"):
            st.session_state["screen"] = "study_test"
            st.rerun()
        return

    st.subheader("Main Focus Style")
    st.success(profile.get("focus_style", "Flexible Focus"))

    st.markdown("---")

    st.subheader("Profile Scores")

    st.write(f"Focus endurance: **{profile_level(profile.get('focus_endurance', 0.5))}**")
    st.progress(profile.get("focus_endurance", 0.5))

    st.write(f"Sprint preference: **{profile_level(profile.get('sprint_preference', 0.5))}**")
    st.progress(profile.get("sprint_preference", 0.5))

    st.write(f"Start difficulty: **{profile_level(profile.get('start_difficulty', 0.5))}**")
    st.progress(profile.get("start_difficulty", 0.5))

    st.write(f"Metacognitive regulation: **{profile_level(profile.get('metacognitive_regulation', 0.5))}**")
    st.progress(profile.get("metacognitive_regulation", 0.5))

    st.write(f"Cognitive load sensitivity: **{profile_level(profile.get('cognitive_load_sensitivity', 0.5))}**")
    st.progress(profile.get("cognitive_load_sensitivity", 0.5))

    st.write(f"Motor/sensory regulation: **{profile_level(profile.get('motor_sensory_regulation', 0.5))}**")
    st.progress(profile.get("motor_sensory_regulation", 0.5))

    st.markdown("---")

    st.subheader("Recommended Study Method")

    recommendations = get_study_style_recommendations(profile)

    for recommendation in recommendations:
        st.write(f"- {recommendation}")

    st.markdown("---")

    with st.expander("About the Study Style Test"):
        render_about_study_style_test()

    st.markdown("---")

    if st.button("Retake Study Style Test"):
        st.session_state["screen"] = "study_test"
        st.rerun()


def render_home():
    st.title("Self-Management Function")

    st.write(
        "This app helps you check in with one academic goal at a time, "
        "then decides whether today should be a **Lock In**, **Steady**, "
        "**Minimum**, **Recovery**, or **Catch-Up** day."
    )

    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Daily Check-In", use_container_width=True):
            st.session_state["screen"] = "daily_check_in"
            st.rerun()

    with col2:
        if st.button("Add New Goal", use_container_width=True):
            st.session_state["screen"] = "add_goal"
            st.rerun()

    goals = load_goals()

    st.subheader("Current Goal Tabs")

    if not goals:
        st.info("No goal tabs yet. Add your first academic goal.")
    else:
        for goal in goals:
            st.markdown(f"### {goal['goal_name']}")
            st.markdown(
                f"""
                Importance: **{goal['importance']}/10**  
                Deadline: **{goal['deadline']}**  
                Main action: **{goal['main_action']} — {goal['normal_amount']} {goal['unit']} normally**  
                Average time needed: **{goal['normal_goal_minutes']} minutes**
                """
            )


def render_add_goal():
    st.title("Add New Academic Goal Tab")

    st.write("Examples: SAT 1570, A Level 4A*, MIT project, application essay, GitHub portfolio.")

    goals = load_goals()

    with st.form("add_goal_form"):
        goal_name = st.text_input("Goal tab name", placeholder="Get 1570 on SAT")

        importance = st.slider(
            "Importance",
            min_value=1,
            max_value=10,
            value=8
        )

        deadline = st.date_input(
            "Deadline",
            value=date.today()
        )

        st.subheader("Main Daily Action")

        main_action = st.text_input(
            "Main action",
            placeholder="memorise vocabulary"
        )

        normal_amount = st.number_input(
            "Normal daily amount",
            min_value=1,
            max_value=10000,
            value=30
        )

        unit = st.text_input(
            "Unit",
            placeholder="words / questions / minutes / pages",
            value="words"
        )

        normal_goal_minutes = st.number_input(
            "Average time needed for this daily action (minutes)",
            min_value=1,
            max_value=1440,
            value=30
        )

        st.caption(
            "Example: SAT vocabulary may be 30 minutes. "
            "A Level past paper practice may be 180 minutes."
        )

        submitted = st.form_submit_button("Add Goal Tab")

        if submitted:
            if not goal_name or not main_action or not unit:
                st.error("Please fill in goal name, main action, and unit.")
            else:
                new_goal = {
                    "id": get_next_goal_id(goals),
                    "goal_name": goal_name,
                    "importance": importance,
                    "deadline": deadline.isoformat(),
                    "estimated_progress": 0,
                    "current_progress": 0,
                    "main_action": main_action,
                    "normal_amount": normal_amount,
                    "unit": unit,
                    "normal_goal_minutes": normal_goal_minutes
                }

                goals.append(new_goal)
                save_goals(goals)

                st.success("Goal tab added.")

                st.session_state["screen"] = "home"
                st.rerun()


def render_daily_check_in():
    st.title("Daily Check-In")

    goals = load_goals()

    if not goals:
        st.warning("You need to add at least one academic goal first.")
        if st.button("Add New Goal"):
            st.session_state["screen"] = "add_goal"
            st.rerun()
        return

    active_goals = [
        goal for goal in goals
        if goal.get("estimated_progress", 0) < 100
    ]

    if not active_goals:
        st.warning("All goals are at 100%. Add a new goal or delete/restart a goal tab.")
        return

    goal_names = [goal["goal_name"] for goal in active_goals]

    selected_goal_name = st.selectbox(
        "Which goal do you want to check in today?",
        goal_names
    )

    selected_goal = next(goal for goal in active_goals if goal["goal_name"] == selected_goal_name)

    state = load_state()
    goal_key = str(selected_goal["id"])
    goal_state = state.get("last_task_by_goal", {}).get(goal_key)

    st.subheader(f"Goal: {selected_goal['goal_name']}")

    if goal_state and goal_state.get("task_sentence"):
        st.subheader("Previous Task for This Goal")
        st.write(f"- {goal_state['task_sentence']}")

        completion_status = st.radio(
            "Did you complete this task?",
            ["Completed", "Partly completed", "Skipped"],
            horizontal=True
        )
    else:
        st.info("No previous task found for this goal. This looks like your first check-in for this tab.")
        completion_status = "Completed"

    st.subheader("How do you feel today?")

    stress = mbti_scale(
        "Stress",
        [
            ("Very calm", 0.1),
            ("Calm", 0.3),
            ("Neutral", 0.5),
            ("Stressed", 0.7),
            ("Very stressed", 0.9),
        ],
        key=f"stress_scale_{goal_key}"
    )

    energy = mbti_scale(
        "Energy",
        [
            ("Very tired", 0.1),
            ("Tired", 0.3),
            ("Neutral", 0.5),
            ("Energetic", 0.7),
            ("Very energetic", 0.9),
        ],
        key=f"energy_scale_{goal_key}"
    )

    concentration = mbti_scale(
        "Concentration",
        [
            ("Very scattered", 0.1),
            ("Scattered", 0.3),
            ("Neutral", 0.5),
            ("Focused", 0.7),
            ("Very focused", 0.9),
        ],
        key=f"concentration_scale_{goal_key}"
    )

    mood = mbti_scale(
        "Mood",
        [
            ("Very low", 0.1),
            ("Low", 0.3),
            ("Neutral", 0.5),
            ("Good", 0.7),
            ("Very good", 0.9),
        ],
        key=f"mood_scale_{goal_key}"
    )

    readiness = mbti_scale(
        "Readiness to start",
        [
            ("Avoiding", 0.1),
            ("Not ready", 0.3),
            ("Neutral", 0.5),
            ("Ready", 0.7),
            ("Very ready", 0.9),
        ],
        key=f"readiness_scale_{goal_key}"
    )

    available_time_label = st.select_slider(
        "Available time for this goal today",
        options=["15 min", "30 min", "1 hour", "2 hours", "3+ hours"],
        value="1 hour"
    )

    has_fun_plan = st.radio(
        "Do you have a fun/social plan today?",
        ["No", "Yes"],
        horizontal=True
    )

    fun_plan = ""

    if has_fun_plan == "Yes":
        fun_plan = st.text_input(
            "What is the plan?",
            placeholder="movie at 8pm"
        )

    if st.button("Generate Today's Plan for This Goal", use_container_width=True):
        state = load_state()
        goals = load_goals()

        goals, progress_update, state = apply_estimated_progress_for_goal(
            goals,
            state,
            selected_goal["id"],
            completion_status
        )

        save_goals(goals)
        save_state(state)

        selected_goal = find_goal_by_id(goals, selected_goal["id"])

        if progress_update:
            st.subheader("Progress Estimate Updated")
            st.write(
                f"{progress_update['goal_name']}: "
                f"{round(progress_update['old_progress'], 1)}% → "
                f"{round(progress_update['new_progress'], 1)}% "
                f"(+{progress_update['gain']}%)"
            )
            st.caption("This update is based on your daily check-in evidence.")

        elif goal_state:
            if completion_status == "Skipped":
                st.info("No estimated progress was added because the previous task was skipped.")
            else:
                st.caption("Progress was already applied for the previous task, or no structured task data was found.")

        check_in = {
            "completion_status": completion_status,
            "stress": stress,
            "energy": energy,
            "concentration": concentration,
            "mood": mood,
            "readiness": readiness,
            "available_minutes": time_label_to_minutes(available_time_label),
            "has_fun_plan": has_fun_plan == "Yes",
            "fun_plan": fun_plan
        }

        profile = load_study_profile()
        plan = generate_single_goal_plan(selected_goal, check_in, profile)

        execution_advice = generate_execution_advice(
            profile,
            plan["mode"],
            plan["task"],
            selected_goal
        )

        st.success(f"Today's mode: {mode_label(plan['mode'])}")

        st.subheader("Today's Task")
        st.write(f"- {plan['task']['task_sentence']}")

        st.subheader("How to Do It")
        for advice in execution_advice:
            st.write(f"- {advice}")

        st.subheader("Why")
        st.write(plan["explanation"])

        st.subheader("Relaxation Advice")
        st.write(plan["relaxation_advice"])

        st.subheader("Function Values")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Goal Pressure", score_percent(plan["goal_pressure"]))
            st.caption(score_level(plan["goal_pressure"]))

        with col2:
            st.metric("Time Fit", score_percent(plan["time_fit"]))
            st.caption(score_level(plan["time_fit"]))

        with col3:
            st.metric("Capacity", score_percent(plan["capacity"]))
            st.caption(score_level(plan["capacity"]))

        col4, col5, col6 = st.columns(3)

        with col4:
            st.metric("Burnout Risk", score_percent(plan["burnout_risk"]))
            st.caption(score_level(plan["burnout_risk"]))

        with col5:
            st.metric("Style Adjustment", f"{round(plan['style_adjustment'] * 100)}%")
            st.caption("Study style effect on capacity")

        with col6:
            st.metric("Task Multiplier", f"{round(plan['final_multiplier'] * 100)}%")
            st.caption("Mode × study style")

        st.subheader("Goal Details")

        st.markdown(
            f"""
            Days left: **{plan['days_left']}**  
            Remaining estimated progress: **{round(plan['remaining'], 1)}%**  
            Daily estimated progress needed: **{round(plan['daily_needed'], 2)}% per day**  
            Average time needed for this goal: **{selected_goal['normal_goal_minutes']} minutes**
            """
        )

        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_plan_id = str(uuid.uuid4())

        state = load_state()
        last_task_by_goal = state.get("last_task_by_goal", {})

        last_task_by_goal[goal_key] = {
            "task_sentence": plan["task"]["task_sentence"],
            "task_structured": plan["task"],
            "mode": plan["mode"],
            "date": today,
            "plan_id": new_plan_id,
            "progress_applied_plan_id": state.get("last_task_by_goal", {}).get(goal_key, {}).get("progress_applied_plan_id", "")
        }

        state["last_task_by_goal"] = last_task_by_goal

        save_state(state)

        history_data = {
            "date": today,
            "goal_id": selected_goal["id"],
            "goal_name": selected_goal["goal_name"],
            "completion_status": completion_status,
            "stress": check_in["stress"],
            "energy": check_in["energy"],
            "concentration": check_in["concentration"],
            "mood": check_in["mood"],
            "readiness": check_in["readiness"],
            "available_minutes": check_in["available_minutes"],
            "normal_goal_minutes": selected_goal["normal_goal_minutes"],
            "time_fit": plan["time_fit"],
            "style_adjustment": plan["style_adjustment"],
            "style_task_multiplier": plan["style_task_multiplier"],
            "final_multiplier": plan["final_multiplier"],
            "has_fun_plan": check_in["has_fun_plan"],
            "fun_plan": check_in["fun_plan"],
            "mode": plan["mode"],
            "capacity": plan["capacity"],
            "burnout_risk": plan["burnout_risk"],
            "goal_pressure": plan["goal_pressure"],
            "task": plan["task"]["task_sentence"],
            "progress_update": json.dumps(progress_update) if progress_update else ""
        }

        append_history(history_data)

        st.info("Today's plan for this goal was saved.")

        if st.button("Back to Home"):
            st.session_state["screen"] = "home"
            st.rerun()


def render_view_goals():
    st.title("Goal Tabs")

    goals = load_goals()

    if not goals:
        st.info("No goal tabs yet.")
        return

    for goal in goals:
        days_left = days_until(goal["deadline"])

        with st.expander(goal["goal_name"], expanded=True):
            st.write(f"Importance: {goal['importance']}/10")
            st.write(f"Deadline: {goal['deadline']} ({days_left} days left)")
            st.write(
                f"Main action: {goal['main_action']} — "
                f"{goal['normal_amount']} {goal['unit']} normally"
            )
            st.write(f"Average time needed: {goal['normal_goal_minutes']} minutes")


def render_check_progress():
    st.title("Check Progress")

    st.write(
        "Progress is estimated from daily check-ins for each goal. "
        "Each goal tab has its own progress estimate and consistency graph."
    )

    goals = load_goals()

    if not goals:
        st.info("No goal tabs yet.")
        return

    for goal in goals:
        progress_value = goal.get("estimated_progress", 0)
        recent_evidence = get_recent_progress_evidence(goal["goal_name"])
        consistency_data = get_consistency_data(goal["goal_name"])

        with st.expander(goal["goal_name"], expanded=True):
            st.subheader("Estimated Progress")
            st.progress(progress_value / 100)

            st.markdown(
                f"""
                Estimated progress: **{round(progress_value, 1)}%**

                How the app estimates progress:
                - Completed task → +1.0%
                - Partly completed → +0.4%
                - Skipped → +0%
                """
            )

            st.subheader("Consistency Graph")

            if consistency_data:
                df = pd.DataFrame(consistency_data)

                st.line_chart(
                    df,
                    x="Day",
                    y="Completion"
                )

                st.caption(
                    "Completed = 100%, partly completed = 40%, skipped = 0%."
                )
            else:
                st.caption("No consistency data has been recorded yet for this goal.")

            if recent_evidence:
                st.subheader("Recent Daily Check-In Evidence")

                for item in recent_evidence:
                    st.write(
                        f"- {item['date']}: "
                        f"{round(item['old_progress'], 1)}% → "
                        f"{round(item['new_progress'], 1)}% "
                        f"(+{item['gain']}%)"
                    )
            else:
                st.caption("No progress evidence has been recorded yet for this goal.")


def render_delete_goal():
    st.title("Delete Goal Tab")

    goals = load_goals()

    if not goals:
        st.info("No goal tabs yet.")
        return

    goal_names = [goal["goal_name"] for goal in goals]

    selected_name = st.selectbox("Choose goal tab to delete", goal_names)

    st.warning("Deleting a tab is like closing/restarting a goal. This cannot be undone.")

    if st.button("Delete Goal Tab"):
        deleted_goal = next(goal for goal in goals if goal["goal_name"] == selected_name)
        goals = [goal for goal in goals if goal["goal_name"] != selected_name]
        save_goals(goals)

        state = load_state()
        goal_key = str(deleted_goal["id"])
        if goal_key in state.get("last_task_by_goal", {}):
            del state["last_task_by_goal"][goal_key]
            save_state(state)

        st.success(f"Deleted: {selected_name}")


def render_history():
    st.title("History")

    history = read_history()

    if not history:
        st.info("No daily check-in history yet.")
        return

    st.write("Most recent check-ins:")

    for item in reversed(history[-15:]):
        with st.expander(f"{item.get('date', '')} — {item.get('goal_name', '')}"):
            st.write(f"Goal: {item.get('goal_name', '')}")
            st.write(f"Mode: {mode_label(item.get('mode', ''))}")
            st.write(f"Task: {item.get('task', '')}")
            st.write(f"Completion: {item.get('completion_status', '')}")
            st.write(f"Stress: {item.get('stress', '')}")
            st.write(f"Energy: {item.get('energy', '')}")
            st.write(f"Mood: {item.get('mood', '')}")
            st.write(f"Readiness: {item.get('readiness', '')}")
            st.write(f"Time fit: {item.get('time_fit', '')}")
            st.write(f"Style adjustment: {item.get('style_adjustment', '')}")
            st.write(f"Final multiplier: {item.get('final_multiplier', '')}")

            update = item.get("progress_update", "")
            if update:
                st.write(f"Progress update: {update}")


def render_function_explanation():
    st.title("What is SMF(x)?")

    st.write(
        "SMF(x) means **Self-Management Function**. "
        "It is the mathematical function used by this app to decide what the user should do today."
    )

    st.markdown("---")

    st.subheader("1. Basic idea")

    st.markdown(
        """
        The function takes the user's current situation as input:

        **x = goal state + daily condition + completion history + study style profile**

        Then it outputs:

        **SMF(x) → today's mode + today's task**
        """
    )

    st.info("Example: **SMF(x) = 🟡 MINIMUM + memorise 10 words**")

    st.markdown("---")

    st.subheader("2. Main variables")

    st.markdown(
        """
        The function mainly uses these values:

        **G = Goal Pressure**  
        How urgently this goal needs attention.

        **C = Capacity**  
        How much useful work the user can realistically do today.

        **B = Burnout Risk**  
        How dangerous it is to push too hard today.

        **P = Study Style Profile**  
        How the user tends to focus, start, and handle cognitive load.
        """
    )

    st.markdown("---")

    st.subheader("3. Goal Pressure")

    st.latex(
        r"G = \frac{\frac{importance}{10} \times \frac{100 - progress}{days\_left}}{1.5}"
    )

    st.write(
        "Goal Pressure becomes high when the goal is important, the deadline is close, "
        "and estimated progress is still low."
    )

    st.write(
        "The value 1.5 is a high-pressure benchmark. "
        "It means that needing about 1.5% estimated progress per day is treated as high pressure."
    )

    st.markdown("---")

    st.subheader("4. Capacity")

    st.latex(
        r"C = time\_fit \times energy \times concentration \times readiness \times stress\_adjustment \times style\_adjustment"
    )

    st.markdown(
        """
        Where:

        **time_fit = available_minutes / normal_goal_minutes**

        **stress_adjustment = 1 - 0.6 × stress**
        """
    )

    st.write(
        "Capacity estimates how much useful work the user can realistically do today."
    )

    st.write(
        "**style_adjustment** is part of Capacity. "
        "For example, if the user has high start difficulty and low readiness today, "
        "the app lowers realistic capacity slightly."
    )

    st.markdown("---")

    st.subheader("5. Study Style Adjustment")

    st.latex(
        r"style\_adjustment = 1 - 0.15 \times start\_difficulty \times (1 - readiness) - 0.05 \times cognitive\_load \times (1 - concentration) + 0.05 \times focus\_endurance \times time\_fit"
    )

    st.write(
        "This adjustment lets the Study Style Profile affect the function, "
        "but only within a limited range so it does not dominate everything."
    )

    st.markdown("---")

    st.subheader("6. Burnout Risk")

    st.latex(
        r"B = 0.45 \times stress^2 + 0.20 \times low\_mood + 0.20 \times low\_energy + 0.15 \times low\_readiness"
    )

    st.markdown(
        """
        Where:

        - **low_mood = 1 - mood**
        - **low_energy = 1 - energy**
        - **low_readiness = 1 - readiness**
        """
    )

    st.write(
        "Burnout Risk increases when stress is high, mood is low, energy is low, "
        "or the user feels resistant to starting."
    )

    st.markdown("---")

    st.subheader("7. How mode becomes today's task")

    st.latex(
        r"task\_amount = normal\_amount \times mode\_multiplier \times style\_task\_multiplier"
    )

    st.markdown(
        """
        **mode_multiplier** depends on the daily mode:

        - 🔒 LOCK IN → 120%  
        - 🌿 STEADY → 100%  
        - 🟡 MINIMUM → 35%  
        - 🛌 RECOVERY → 15%  
        - 🔁 CATCH-UP → 120%

        **style_task_multiplier** makes a small adjustment based on study style.
        """
    )

    st.markdown("---")

    st.subheader("8. How progress is estimated")

    st.write(
        "The app does not ask the user to manually enter progress every day. "
        "Instead, progress is estimated from daily check-in evidence."
    )

    st.markdown(
        """
        - Completed → +1.0% estimated progress  
        - Partly completed → +0.4% estimated progress  
        - Skipped → +0% estimated progress  
        """
    )

    st.warning(
        "This is estimated progress, not guaranteed mastery. "
        "The app uses completion evidence as a reasonable signal that the user is moving forward."
    )

    st.markdown("---")

    st.subheader("9. Consistency graph")

    st.write(
        "The Check Progress page shows a consistency graph for each goal."
    )

    st.markdown(
        """
        - Completed → 100%
        - Partly completed → 40%
        - Skipped → 0%
        """
    )

    st.write(
        "This helps the user see whether they are consistently showing up."
    )

    st.markdown("---")

    st.subheader("10. Summary")

    st.markdown(
        """
        **SMF(x)** is designed to avoid two common problems:

        1. Forcing the user to work too hard and burn out.  
        2. Letting the user relax so much that they forget the big goal.

        The function tries to find the best daily balance between **progress**, **sustainability**, and **personal study style**.
        """
    )


# ----------------------------
# Main app
# ----------------------------

def main():
    st.set_page_config(
        page_title="Self-Management Function",
        page_icon="🎯",
        layout="centered",
        initial_sidebar_state="expanded"
    )

    profile = load_study_profile()

    if "screen" not in st.session_state:
        # Show the study-style test on the first visit, but do not keep forcing
        # it on every rerun. Otherwise every sidebar click is immediately
        # redirected back to the test until a profile has been created.
        st.session_state["screen"] = (
            "study_test" if profile is None else "home"
        )

    if profile is None and st.session_state["screen"] not in {
        "study_test",
        "function_explanation",
    }:
        st.session_state["screen"] = "study_test"

    st.sidebar.title("☰ Menu")

    if profile is None:
        if st.sidebar.button("Study Style Test", use_container_width=True):
            st.session_state["screen"] = "study_test"
            st.rerun()

        if st.sidebar.button("What is SMF(x)?", use_container_width=True):
            st.session_state["screen"] = "function_explanation"
            st.rerun()

        st.sidebar.info("Complete the Study Style Test to unlock the other tabs.")
    else:
        if st.sidebar.button("Home", use_container_width=True):
            st.session_state["screen"] = "home"
            st.rerun()

        st.sidebar.markdown("---")

        if st.sidebar.button("What is SMF(x)?", use_container_width=True):
            st.session_state["screen"] = "function_explanation"
            st.rerun()

        if st.sidebar.button("Study Style Profile", use_container_width=True):
            st.session_state["screen"] = "profile"
            st.rerun()

        st.sidebar.markdown("---")
        st.sidebar.subheader("Goal Management")

        if st.sidebar.button("View Goal Tabs", use_container_width=True):
            st.session_state["screen"] = "view_goals"
            st.rerun()

        if st.sidebar.button("Check Progress", use_container_width=True):
            st.session_state["screen"] = "check_progress"
            st.rerun()

        if st.sidebar.button("Delete Goal Tab", use_container_width=True):
            st.session_state["screen"] = "delete_goal"
            st.rerun()

        if st.sidebar.button("History", use_container_width=True):
            st.session_state["screen"] = "history"
            st.rerun()

    screen = st.session_state["screen"]

    if screen == "study_test":
        render_study_style_test()

    elif screen == "profile":
        render_profile()

    elif screen == "home":
        render_home()

    elif screen == "add_goal":
        render_add_goal()

    elif screen == "daily_check_in":
        render_daily_check_in()

    elif screen == "view_goals":
        render_view_goals()

    elif screen == "check_progress":
        render_check_progress()

    elif screen == "delete_goal":
        render_delete_goal()

    elif screen == "history":
        render_history()

    elif screen == "function_explanation":
        render_function_explanation()


if __name__ == "__main__":
    main()
