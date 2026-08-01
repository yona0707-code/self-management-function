# Self-Management Function App
# Version 6: Multiple Academic Goal Tabs
#
# This app is for academic/application-related goals.
# Each goal works like a "tab":
#   - SAT goal
#   - A Level goal
#   - MIT project goal
#   - Essay goal
#
# Daily check-in is done once.
# Then the Self-Management Function chooses which goal tabs need attention today.


from datetime import datetime, date
import csv
import os
import json
import math


GOALS_FILE = "smf_goals.json"
STATE_FILE = "smf_state.json"
HISTORY_FILE = "smf_history.csv"


# ----------------------------
# Basic helpers
# ----------------------------

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def ask_number(question, minimum, maximum):
    while True:
        try:
            value = float(input(question))
            if minimum <= value <= maximum:
                return value
            print(f"Please enter a number from {minimum} to {maximum}.")
        except ValueError:
            print("Please enter a valid number.")


def ask_yes_no(question):
    while True:
        answer = input(question + " yes/no: ").lower().strip()
        if answer in ["yes", "y"]:
            return True
        if answer in ["no", "n"]:
            return False
        print("Please answer yes or no.")


def ask_date(question):
    while True:
        text = input(question + " YYYY-MM-DD: ").strip()
        try:
            return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
        except ValueError:
            print("Please enter the date in YYYY-MM-DD format.")


def normalize_1_to_10(value):
    return value / 10


def days_until(deadline_text):
    deadline = datetime.strptime(deadline_text, "%Y-%m-%d").date()
    today = date.today()
    return max(1, (deadline - today).days)


# ----------------------------
# File loading / saving
# ----------------------------

def load_goals():
    if not os.path.exists(GOALS_FILE):
        return []

    with open(GOALS_FILE, "r") as file:
        return json.load(file)


def save_goals(goals):
    with open(GOALS_FILE, "w") as file:
        json.dump(goals, file, indent=4)


def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "last_plan_tasks": [],
            "last_mode": "",
            "last_date": ""
        }

    with open(STATE_FILE, "r") as file:
        return json.load(file)


def save_state(state):
    with open(STATE_FILE, "w") as file:
        json.dump(state, file, indent=4)


def save_history(data):
    file_exists = os.path.exists(HISTORY_FILE)

    with open(HISTORY_FILE, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)


# ----------------------------
# Goal tab management
# ----------------------------

def get_next_goal_id(goals):
    if not goals:
        return 1
    return max(goal["id"] for goal in goals) + 1


def add_goal_tab(goals):
    print("\n===================================")
    print(" Add Academic Goal Tab")
    print("===================================")

    print("\nExamples:")
    print("- Get 1570 on SAT")
    print("- Get 4A*s on A Level")
    print("- Finish MIT project")
    print("- Write application essay")
    print("- Build GitHub portfolio")

    goal_name = input("\nGoal tab name: ")

    importance = ask_number(
        "Importance? 1 = low, 10 = extremely important: ",
        1,
        10
    )

    deadline = ask_date("Deadline")

    print("\nUse progress percentage for now.")
    print("Example: if you feel 60% done, enter 60.")

    current_progress = ask_number(
        "Current progress? 0-100: ",
        0,
        100
    )

    print("\nMain action setup")
    print("Example:")
    print("Main action: memorise vocabulary")
    print("Normal amount: 30")
    print("Unit: words")

    main_action = input("\nMain daily action for this goal: ")

    normal_amount = ask_number(
        "Normal daily amount: ",
        1,
        10000
    )

    unit = input("Unit: words/questions/minutes/pages/etc: ")

    goal = {
        "id": get_next_goal_id(goals),
        "goal_name": goal_name,
        "importance": importance,
        "deadline": deadline,
        "current_progress": current_progress,
        "main_action": main_action,
        "normal_amount": normal_amount,
        "unit": unit
    }

    goals.append(goal)
    save_goals(goals)

    print("\nGoal tab added.")


def view_goal_tabs(goals):
    print("\n===================================")
    print(" Academic Goal Tabs")
    print("===================================")

    if not goals:
        print("\nNo goal tabs yet.")
        return

    for index, goal in enumerate(goals, start=1):
        days_left = days_until(goal["deadline"])

        print("-----------------------------------")
        print(f"Tab {index}")
        print(f"Name: {goal['goal_name']}")
        print(f"Importance: {goal['importance']}/10")
        print(f"Deadline: {goal['deadline']} ({days_left} days left)")
        print(f"Progress: {goal['current_progress']}%")
        print(
            f"Main action: {goal['main_action']} "
            f"({goal['normal_amount']} {goal['unit']} normally)"
        )


def choose_goal_index(goals, question):
    if not goals:
        print("\nNo goal tabs available.")
        return None

    view_goal_tabs(goals)

    choice = int(
        ask_number(
            f"\n{question} Enter tab number: ",
            1,
            len(goals)
        )
    )

    return choice - 1


def delete_goal_tab(goals):
    index = choose_goal_index(goals, "Which goal tab do you want to delete?")
    if index is None:
        return

    deleted_goal = goals.pop(index)
    save_goals(goals)

    print(f"\nDeleted goal tab: {deleted_goal['goal_name']}")


def update_goal_progress(goals):
    index = choose_goal_index(goals, "Which goal tab do you want to update?")
    if index is None:
        return

    goal = goals[index]

    print(f"\nUpdating progress for: {goal['goal_name']}")
    new_progress = ask_number("New progress? 0-100: ", 0, 100)

    goal["current_progress"] = new_progress
    save_goals(goals)

    print("\nProgress updated.")


# ----------------------------
# Self-Management Function
# ----------------------------

def calculate_goal_pressure(goal):
    """
    Goal Pressure measures how much this goal needs attention.

    Formula:
    G = (importance / 10) × ((100 - progress) / days_left) ÷ 1.5

    Higher when:
    - goal is important
    - progress is low
    - deadline is close
    """

    importance = goal["importance"] / 10
    progress = goal["current_progress"]
    days_left = days_until(goal["deadline"])

    remaining_progress = 100 - progress
    daily_progress_needed = remaining_progress / days_left

    goal_pressure = importance * daily_progress_needed / 1.5
    goal_pressure = clamp(goal_pressure, 0, 1)

    return goal_pressure, remaining_progress, daily_progress_needed, days_left


def calculate_capacity(available_minutes, energy, concentration, stress):
    """
    User Capacity estimates how much useful work the user can realistically do today.

    Formula:
    C = (available_minutes / 180) × energy × concentration × (1 - 0.6 × stress)
    """

    time_factor = clamp(available_minutes / 180, 0, 1)

    stress_adjustment = 1 - (0.6 * stress)
    stress_adjustment = clamp(stress_adjustment, 0.2, 1)

    capacity = time_factor * energy * concentration * stress_adjustment
    capacity = clamp(capacity, 0, 1)

    return capacity


def calculate_burnout_risk(stress, happiness, energy):
    """
    Burnout Risk estimates how dangerous it is to push hard today.

    Formula:
    B = 0.5 × stress² + 0.25 × (1 - happiness) + 0.25 × (1 - energy)
    """

    burnout_risk = (
        0.50 * (stress ** 2)
        + 0.25 * (1 - happiness)
        + 0.25 * (1 - energy)
    )

    return clamp(burnout_risk, 0, 1)


def decide_overall_mode(max_goal_pressure, capacity, burnout_risk, skipped_yesterday):
    """
    Decides the user's overall self-management mode for today.
    """

    if skipped_yesterday and burnout_risk < 0.65:
        return "CATCH-UP"

    if max_goal_pressure >= 0.65 and burnout_risk < 0.60 and capacity >= 0.35:
        return "LOCK IN"

    if max_goal_pressure >= 0.65 and burnout_risk >= 0.60:
        return "MINIMUM"

    if max_goal_pressure < 0.45 and burnout_risk >= 0.65:
        return "RECOVERY"

    if capacity < 0.30 and burnout_risk >= 0.55:
        return "MINIMUM"

    return "STEADY"


def get_mode_multiplier(mode, rank, capacity):
    """
    Converts mode into task size.

    rank = 0 means highest-pressure goal.
    rank = 1 means second-highest-pressure goal.
    """

    if rank == 0:
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

    if rank == 1:
        if mode == "LOCK IN" and capacity >= 0.55:
            return 0.50
        if mode == "STEADY" and capacity >= 0.55:
            return 0.50
        if mode == "CATCH-UP" and capacity >= 0.70:
            return 0.35

    return 0


def calculate_task_amount(normal_amount, unit, multiplier):
    amount = math.ceil(normal_amount * multiplier)
    amount = max(1, amount)

    # Make minutes look cleaner.
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
            "Your goals still matter, but stress or low capacity makes a large task risky. "
            "Today should protect progress with a smaller task."
        )

    if mode == "RECOVERY":
        return (
            "Burnout risk is high and goal pressure is not extreme. "
            "Recovery is allowed, but you should still keep a tiny connection to your goal."
        )

    if mode == "CATCH-UP":
        return (
            "You skipped recently, but burnout risk is not too high. "
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
            f"{plan_text} You can still relax, but complete the main task first. "
            "Avoid relaxing too early if it usually makes you lose momentum."
        )

    if mode == "STEADY":
        return (
            f"{plan_text} This is okay. Complete your planned task first so you can relax without guilt."
        )

    if mode == "MINIMUM":
        return (
            f"{plan_text} This is okay, but complete the minimum task first. "
            "The point is to protect your connection with the big goal."
        )

    if mode == "RECOVERY":
        return (
            f"{plan_text} This may help recovery. Choose relaxation that restores you, "
            "not something that makes tomorrow worse."
        )

    if mode == "CATCH-UP":
        return (
            f"{plan_text} Do the catch-up task before going out. "
            "Do not cancel all relaxation, but protect the goal first."
        )

    return "No relaxation advice available."


# ----------------------------
# Daily check-in
# ----------------------------

def daily_check_in(goals):
    print("\n===================================")
    print(" Daily Check-In")
    print("===================================")

    if not goals:
        print("\nYou need to add at least one academic goal tab first.")
        return

    state = load_state()
    last_plan_tasks = state.get("last_plan_tasks", [])

    if last_plan_tasks:
        print("\nYesterday's plan was:")
        for task in last_plan_tasks:
            print(f"- {task}")

        completed_yesterday = ask_yes_no("\nDid you complete yesterday's plan?")
        skipped_yesterday = not completed_yesterday
    else:
        completed_yesterday = None
        skipped_yesterday = False
        print("\nNo previous plan found. This looks like your first daily check-in.")

    print("\nHow are you today?")
    print("Use 1 to 10 scale.")

    stress = normalize_1_to_10(
        ask_number("Stress today? 1 = low, 10 = high: ", 1, 10)
    )

    happiness = normalize_1_to_10(
        ask_number("Happiness today? 1 = low, 10 = high: ", 1, 10)
    )

    energy = normalize_1_to_10(
        ask_number("Energy today? 1 = low, 10 = high: ", 1, 10)
    )

    concentration = normalize_1_to_10(
        ask_number("Concentration today? 1 = low, 10 = high: ", 1, 10)
    )

    available_minutes = ask_number(
        "Available minutes today? ",
        0,
        1440
    )

    has_fun_plan = ask_yes_no("Do you have a fun/social plan today?")

    fun_plan = ""
    if has_fun_plan:
        fun_plan = input("What is your fun/social plan? Example: movie at 8pm: ")

    active_goals = [
        goal for goal in goals
        if goal["current_progress"] < 100
    ]

    if not active_goals:
        print("\nAll goal tabs are at 100% progress. Add a new goal tab or update progress.")
        return

    goal_results = []

    for goal in active_goals:
        pressure, remaining, daily_needed, days_left = calculate_goal_pressure(goal)

        goal_results.append({
            "goal": goal,
            "pressure": pressure,
            "remaining": remaining,
            "daily_needed": daily_needed,
            "days_left": days_left
        })

    goal_results.sort(key=lambda item: item["pressure"], reverse=True)

    max_goal_pressure = goal_results[0]["pressure"]

    capacity = calculate_capacity(
        available_minutes,
        energy,
        concentration,
        stress
    )

    burnout_risk = calculate_burnout_risk(
        stress,
        happiness,
        energy
    )

    mode = decide_overall_mode(
        max_goal_pressure,
        capacity,
        burnout_risk,
        skipped_yesterday
    )

    today_tasks = []

    for rank, result in enumerate(goal_results):
        multiplier = get_mode_multiplier(mode, rank, capacity)

        if multiplier <= 0:
            continue

        goal = result["goal"]

        amount = calculate_task_amount(
            goal["normal_amount"],
            goal["unit"],
            multiplier
        )

        task_sentence = create_task_sentence(goal, amount)

        today_tasks.append({
            "goal_name": goal["goal_name"],
            "task_sentence": task_sentence,
            "amount": amount,
            "unit": goal["unit"],
            "pressure": result["pressure"],
            "rank": rank + 1
        })

    if not today_tasks:
        top_goal = goal_results[0]["goal"]
        amount = calculate_task_amount(
            top_goal["normal_amount"],
            top_goal["unit"],
            0.15
        )
        task_sentence = create_task_sentence(top_goal, amount)

        today_tasks.append({
            "goal_name": top_goal["goal_name"],
            "task_sentence": task_sentence,
            "amount": amount,
            "unit": top_goal["unit"],
            "pressure": goal_results[0]["pressure"],
            "rank": 1
        })

    explanation = get_mode_explanation(mode)
    relaxation_advice = get_relaxation_advice(mode, has_fun_plan, fun_plan)

    print("\n===================================")
    print(" Today's Self-Management Plan")
    print("===================================")

    print("\nToday's mode:")
    print(mode)

    print("\nToday's tasks:")
    for task in today_tasks:
        print(f"- {task['task_sentence']}")

    print("\nWhy:")
    print(explanation)

    print("\nRelaxation advice:")
    print(relaxation_advice)

    print("\n===================================")
    print(" Function Values")
    print("===================================")

    print(f"User capacity: {round(capacity, 3)}")
    print(f"Burnout risk: {round(burnout_risk, 3)}")
    print(f"Highest goal pressure: {round(max_goal_pressure, 3)}")

    print("\nGoal pressure ranking:")
    for result in goal_results:
        goal = result["goal"]
        print("-----------------------------------")
        print(f"Goal: {goal['goal_name']}")
        print(f"Pressure: {round(result['pressure'], 3)}")
        print(f"Days left: {result['days_left']}")
        print(f"Remaining progress: {round(result['remaining'], 1)}%")
        print(f"Daily progress needed: {round(result['daily_needed'], 2)}% per day")

    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plan_task_sentences = [task["task_sentence"] for task in today_tasks]

    history_data = {
        "date": today,
        "completed_yesterday": completed_yesterday,
        "stress": stress,
        "happiness": happiness,
        "energy": energy,
        "concentration": concentration,
        "available_minutes": available_minutes,
        "has_fun_plan": has_fun_plan,
        "fun_plan": fun_plan,
        "mode": mode,
        "capacity": capacity,
        "burnout_risk": burnout_risk,
        "max_goal_pressure": max_goal_pressure,
        "tasks": " | ".join(plan_task_sentences)
    }

    save_history(history_data)

    new_state = {
        "last_plan_tasks": plan_task_sentences,
        "last_mode": mode,
        "last_date": today
    }

    save_state(new_state)

    print("\nSaved:")
    print(f"- Goals: {GOALS_FILE}")
    print(f"- State: {STATE_FILE}")
    print(f"- History: {HISTORY_FILE}")


# ----------------------------
# Main menu
# ----------------------------

def main():
    while True:
        goals = load_goals()

        print("\n===================================")
        print(" Self-Management Function App")
        print(" Version 6: Academic Goal Tabs")
        print("===================================")

        print("\nMenu:")
        print("1. Add academic goal tab")
        print("2. View goal tabs")
        print("3. Delete goal tab")
        print("4. Update goal progress")
        print("5. Daily check-in")
        print("6. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            add_goal_tab(goals)

        elif choice == "2":
            view_goal_tabs(goals)

        elif choice == "3":
            delete_goal_tab(goals)

        elif choice == "4":
            update_goal_progress(goals)

        elif choice == "5":
            daily_check_in(goals)

        elif choice == "6":
            print("\nGoodbye.")
            break

        else:
            print("\nPlease choose a valid option.")


if __name__ == "__main__":
    main()