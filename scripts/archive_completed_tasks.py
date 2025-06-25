#!/usr/bin/env python3
"""
Archive Complete Task Units

This script identifies main tasks where both the main task AND all subtasks
are marked as "done", then archives them according to the cursor rule.
"""

import json
import shutil
from pathlib import Path
from datetime import date

def find_complete_task_units(tasks_data):
    """Find main tasks that are complete units (main + all subtasks done)."""
    complete_units = []
    
    # Handle both old format (tasks_data['tasks']) and new format (tasks_data['master']['tasks'])
    if 'master' in tasks_data and 'tasks' in tasks_data['master']:
        tasks_list = tasks_data['master']['tasks']
    elif 'tasks' in tasks_data:
        tasks_list = tasks_data['tasks']
    else:
        raise ValueError("Unable to find tasks in the provided data structure")
    
    for task in tasks_list:
        # Check if main task is done
        if task['status'] != 'done':
            continue
            
        # Check if all subtasks are done (if any exist)
        all_subtasks_done = True
        if 'subtasks' in task and task['subtasks']:
            for subtask in task['subtasks']:
                if subtask.get('status') != 'done':
                    all_subtasks_done = False
                    break
        
        # Only include if it's a complete unit
        if all_subtasks_done:
            complete_units.append(task)
    
    return complete_units

def archive_task_unit(task, archive_dir, completed_tasks_json_path):
    """Archive a complete task unit."""
    task_id = task['id']
    
    # Move task file to archive
    task_file = Path(f"tasks/task_{task_id:03d}.txt")
    if task_file.exists():
        archive_task_file = archive_dir / task_file.name
        shutil.move(str(task_file), str(archive_task_file))
        print(f"✅ Moved {task_file.name} to archive")
    
    # Add to completed_tasks.json
    task_copy = task.copy()
    task_copy['completed_date'] = str(date.today())
    task_copy['archived_from_main'] = True
    
    # Load existing completed tasks or create new structure
    if completed_tasks_json_path.exists():
        with open(completed_tasks_json_path, 'r') as f:
            completed_data = json.load(f)
    else:
        completed_data = {
            "archived_date": str(date.today()),
            "project_name": "MCP Commit Story",
            "tasks": []
        }
    
    # Append to completed tasks (chronological order by completion)
    completed_data['tasks'].append(task_copy)
    
    # Save updated completed tasks
    with open(completed_tasks_json_path, 'w') as f:
        json.dump(completed_data, f, indent=2)
    
    return task_id

def main():
    # Setup paths
    tasks_json_path = Path("tasks/tasks.json")
    archive_dir = Path("tasks/completed_tasks")
    completed_tasks_json_path = archive_dir / "completed_tasks.json"
    
    # Create archive directory if needed
    archive_dir.mkdir(exist_ok=True)
    
    # Load current tasks
    with open(tasks_json_path, 'r') as f:
        tasks_data = json.load(f)
    
    # Find complete task units
    complete_units = find_complete_task_units(tasks_data)
    
    print(f"Found {len(complete_units)} complete task units ready for archival:")
    for task in complete_units:
        subtask_count = len(task.get('subtasks', []))
        status_info = f"({subtask_count} subtasks)" if subtask_count > 0 else "(no subtasks)"
        print(f"  - Task {task['id']}: {task['title']} {status_info}")
    
    if not complete_units:
        print("No complete task units found for archival.")
        return
    
    # Archive each complete unit
    archived_ids = []
    remaining_tasks = []
    
    # Handle both old format and new format
    if 'master' in tasks_data and 'tasks' in tasks_data['master']:
        tasks_list = tasks_data['master']['tasks']
        tasks_key = ['master', 'tasks']
    elif 'tasks' in tasks_data:
        tasks_list = tasks_data['tasks']
        tasks_key = ['tasks']
    else:
        raise ValueError("Unable to find tasks in the provided data structure")
    
    for task in tasks_list:
        if any(unit['id'] == task['id'] for unit in complete_units):
            archived_id = archive_task_unit(task, archive_dir, completed_tasks_json_path)
            archived_ids.append(archived_id)
        else:
            remaining_tasks.append(task)
    
    # Update main tasks.json with remaining tasks
    if len(tasks_key) == 2:
        tasks_data[tasks_key[0]][tasks_key[1]] = remaining_tasks
    else:
        tasks_data[tasks_key[0]] = remaining_tasks
    with open(tasks_json_path, 'w') as f:
        json.dump(tasks_data, f, indent=2)
    
    print(f"\n✅ Successfully archived {len(archived_ids)} complete task units:")
    print(f"   Task IDs: {archived_ids}")
    print(f"   Remaining active tasks: {len(remaining_tasks)}")
    
    # Check file size improvement
    new_size = tasks_json_path.stat().st_size
    print(f"   New tasks.json size: {new_size/1024:.1f}KB")

if __name__ == "__main__":
    main() 