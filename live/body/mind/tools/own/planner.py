#!/usr/bin/env python3
# tool: planner
# call: planner <action> [task_description|index]
# does: manages a persistent list of tasks/goals in /data/plan.txt
import sys
import os

PLAN_PATH = os.path.expandvars("/data/plan.txt")

def ensure_path():
    dir_path = os.path.dirname(PLAN_PATH)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

def load_plan():
    if not os.path.exists(PLAN_PATH):
        return []
    with open(PLAN_PATH, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def save_plan(plan):
    ensure_path()
    with open(PLAN_PATH, 'w') as f:
        for item in plan:
            f.write(f"{item}\n")

def main():
    ensure_path()
    if len(sys.argv) < 2:
        print("Usage: planner <add|list|done|clear>")
        sys.exit(1)

    action = sys.argv[1]
    plan = load_plan()

    if action == "add":
        if len(sys.argv) < 3:
            print("Error: Provide a task description.")
            sys.exit(1)
        plan.append(sys.argv[2])
        save_plan(plan)
        print(f"Added: {sys.argv[2]}")
    elif action == "list":
        if not plan:
            print("No tasks in plan.")
        else:
            for i, task in enumerate(plan):
                print(f"{i}: {task}")
    elif action == "done":
        if len(sys.argv) < 3:
            print("Error: Provide the index of the task to mark as done.")
            sys.exit(1)
        try:
            idx = int(sys.argv[2])
            if 0 <= idx < len(plan):
                removed = plan.pop(idx)
                save_plan(plan)
                print(f"Completed: {removed}")
            else:
                print(f"Error: Index {idx} out of range.")
        except ValueError:
            print("Error: Index must be a number.")
    elif action == "clear":
        save_plan([])
        print("Plan cleared.")
    else:
        print(f"Unknown action: {action}")

if __name__ == "__main__":
    main()
