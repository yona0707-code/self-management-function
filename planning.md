# Yona's Management Function — Planning

## 1. Project overview

**Yona's Management Function (YMF)** is a personal Streamlit app that helps Yona make realistic daily decisions for academic goals.

Instead of assigning a fixed schedule or simply encouraging the user to work harder, the app evaluates the selected goal, the user's condition, recent completion history, and study-style profile. It then recommends a mode and a concrete task for today.

```text
YMF(x) → today's mode + today's task

x = goal state + daily condition + completion history + study style profile
```

The central principle is:

> The app should not maximize effort. It should maximize realistic and sustainable progress.

## 2. Scope

### In scope

The app focuses on academic and application-related goals that have comparable planning factors, such as:

- SAT preparation
- A-Level study
- Application essays
- GitHub projects
- University preparation

Academic goals work well for the model because they typically have a deadline, an importance level, a repeated daily action, an estimated workload, and progress that can be approximated from completion evidence.

### Out of scope

The app is not intended to manage every area of life. Health, money, sleep, and general habits require different measurements and would make the function too broad and unclear.

The Study Style Test is an app-specific planning aid. It is not a clinical or diagnostic assessment.

## 3. Product goals

- Turn a short daily check-in into an achievable task for one selected goal.
- Adapt the plan when time, energy, concentration, readiness, or stress changes.
- Balance deadline pressure with burnout risk.
- Support multiple independent academic goals without mixing their progress states.
- Estimate progress from daily completion evidence rather than subjective manual input.
- Explain why a mode and task were recommended.
- Adjust task presentation and guidance to the user's study style.

## 4. Core decision model

The function uses four main components:

- **G — Goal Pressure:** how urgent and important the goal is today.
- **C — Capacity:** how much useful work the user can realistically do today.
- **B — Burnout Risk:** how risky it would be to push too hard today.
- **P — Study Style Profile:** how task amount, structure, and advice should be adjusted.

### 4.1 Goal Pressure

Goal Pressure increases when the goal is important, the deadline is close, and estimated progress is low.

```text
G = ((importance / 10) × ((100 - progress) / days_left)) / 1.5
```

The value `1.5` is the high-pressure benchmark: needing about 1.5% estimated progress per day is treated as high pressure.

### 4.2 Capacity

Capacity estimates the amount of useful work that is realistic today.

```text
C = time_fit × energy × concentration × readiness
    × stress_adjustment × style_adjustment

time_fit = available_minutes / normal_goal_minutes
stress_adjustment = 1 - 0.6 × stress
```

Available time is compared with the selected goal's `normal_goal_minutes`, not a universal benchmark. This allows a long A-Level past-paper session and a short SAT vocabulary session to be evaluated relative to their own normal workloads.

### 4.3 Burnout Risk

Burnout Risk estimates how dangerous it would be to push harder today.

```text
B = 0.45 × stress²
    + 0.20 × low_mood
    + 0.20 × low_energy
    + 0.15 × low_readiness

low_mood = 1 - mood
low_energy = 1 - energy
low_readiness = 1 - readiness
```

Stress is squared so that very high stress raises burnout risk more sharply.

### 4.4 Daily modes

The function selects one of five modes:

| Mode | When it is used | Workload multiplier |
| --- | --- | ---: |
| **LOCK IN** | Goal pressure is high and the user's condition can support a push. | 1.20 |
| **STEADY** | The user is stable and should make normal progress. | 1.00 |
| **MINIMUM** | The goal still matters, but capacity is low or burnout risk is high. | 0.35 |
| **RECOVERY** | Burnout risk is high and goal pressure is not extreme. | 0.15 |
| **CATCH-UP** | The previous task was skipped and burnout risk is not too high. | 1.20 |

### 4.5 Task amount

After mode selection, the task amount is calculated as:

```text
task_amount = normal_amount × mode_multiplier × style_task_multiplier
```

The mode remains the main factor. The study-style multiplier should only make a small adjustment.

## 5. Goal model and interaction

The app supports multiple goal tabs, but the user performs a daily check-in for one selected goal at a time. This keeps each goal's calculation and progress independent.

Each goal stores:

- Goal name
- Importance
- Deadline
- Main daily action
- Normal daily amount
- Unit
- Average time needed for the action (`normal_goal_minutes`)
- Estimated progress

## 6. Progress and effort

Progress is estimated from daily check-in evidence instead of manual progress input:

| Completion result | Estimated progress change | Consistency graph value |
| --- | ---: | ---: |
| Completed | +1.0% | 100% |
| Partly completed | +0.4% | 40% |
| Skipped | +0% | 0% |

This is a practical consistency signal, not a claim of perfect subject mastery.

The main progress visualization uses effort in minutes:

```text
planned_effort_minutes = normal_goal_minutes × final_multiplier
daily_effort_minutes = planned_effort_minutes × completion_weight
total_integrated_effort = sum of daily_effort_minutes over the selected period
```

Completed, partly completed, and skipped tasks have completion weights of `1.0`,
`0.4`, and `0.0`. The main graph shows chronological daily effort bars, not
cumulative effort or completion percentage. Total integrated effort, average
daily effort, and the highest effort day are shown as summary metrics.

Daily effort estimates how much work was completed each day. The integrated
effort is the area under the daily effort curve. Since the app records daily
data, this is approximated by summing daily effort values.

## 7. Study Style Profile

The profile adapts how the plan is presented and executed. It currently measures:

1. **Focus endurance** — whether longer focus blocks are realistic.
2. **Sprint preference** — whether work should be split into shorter blocks.
3. **Start difficulty** — whether a small starter step should be suggested.
4. **Metacognitive regulation** — how much planning guidance the app should provide.
5. **Cognitive load sensitivity** — whether the task should be shown as fewer, smaller visible steps.
6. **Motor/sensory regulation** — whether harmless movement or holding an object may help the user focus.

### Guidance rules

- High metacognitive regulation: avoid over-directing, allow the user's preferred strategy, and suggest only a quick reflection.
- Low metacognitive regulation: provide a simple sequence, more structure, and a prompt to reflect on what worked.
- High cognitive load sensitivity: simplify presentation and show only the next few steps, rather than heavily reducing capacity or task amount.

For example: “Write only the next 2–3 steps, not the whole plan.”

## 8. Functional requirements

The MVP includes:

- Home screen
- Daily Check-In
- Add New Goal
- Goal Tabs
- Check Progress
- Delete Goal Tab
- History
- What is YMF(x)?
- Study Style Profile
- About the Study Style Test

## 9. Technical plan

### Platform

- Python
- Streamlit
- Local JSON and CSV persistence

### Main application

- `smf_visual_app.py` — primary Streamlit interface
- `smf_app.py` — simpler command-line interface

### Local data files

| File | Purpose |
| --- | --- |
| `smf_goals.json` | Goal definitions and estimated progress |
| `smf_state.json` | Most recent planning state |
| `smf_history.csv` | Check-in, completion, and plan history |
| `study_profile.json` | Study-style profile |

### Run command

```bash
python3 -m streamlit run smf_visual_app.py
```

## 10. Research basis

The Study Style Test is inspired by cognitive science and educational psychology. The app should clearly state that these sources inform its planning concepts but do not make the profile diagnostic.

1. [Motivated Strategies for Learning Questionnaire (MSLQ)](https://files.eric.ed.gov/fulltext/ED338122.pdf) — self-regulated learning, metacognitive self-regulation, effort regulation, time and study environment, and learning strategies.
2. [Zimmerman (2002), Becoming a Self-Regulated Learner: An Overview](https://www.tandfonline.com/doi/abs/10.1207/s15430421tip4102_2) — planning, performance, monitoring, and reflection.
3. [Cognitive Load Theory and instructional design](https://pmc.ncbi.nlm.nih.gov/articles/PMC12246501/) — working-memory limits and mental overload.
4. [Sustained Attention overview](https://www.sciencedirect.com/topics/psychology/sustained-attention) — maintaining focus and engagement over time.
5. [Cognitive Load Theory and individual differences](https://www.sciencedirect.com/science/article/pii/S1041608024000165) — interactions between learning design, cognitive load, and individual differences.

## 11. Development history

1. **Broad self-management idea** — the initial scope included many areas of life.
2. **Academic focus** — the scope was narrowed to make the model coherent and measurable.
3. **Mathematical function** — YMF(x) was defined to return a daily mode and task.
4. **Daily modes** — Lock In, Steady, Minimum, Recovery, and Catch-Up were introduced.
5. **Goal tabs** — each academic goal received an independent state.
6. **Single-goal check-in** — daily calculation was limited to one selected goal.
7. **Estimated progress** — subjective manual input was replaced by completion evidence.
8. **Study Style Test** — individual learning differences were added to the model.
9. **Research basis** — the profile was connected to relevant educational psychology concepts.
10. **Credibility and explanation** — an About section was added to explain the profile and its limits.

## 12. Current status and next priorities

The project is a working MVP/prototype. The core concept and decision model are complete enough to demonstrate mathematical modeling, human-centered design, adaptive daily planning, and explainable recommendations.

The next development priorities are:

1. Validate that the formulas and thresholds produce sensible recommendations across realistic scenarios.
2. Keep the mode decision and workload calculation explainable in the interface.
3. Test persistence and independent state handling across multiple goals.
4. Improve completion-history and consistency visualizations.
5. Refine study-style advice without allowing it to overpower the daily mode.
6. Add safeguards and clearer wording around estimated progress and the non-diagnostic profile.
7. Collect user feedback before expanding beyond the academic-goal scope.
