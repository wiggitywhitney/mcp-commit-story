def test_tasks_plan_no_operational_cli_commands():
    """tasks.json and task files should not require operational CLI commands (expected to fail until plan updated)."""
    import json
    with open("tasks/tasks.json") as f:
        data = json.load(f)
        # Handle the current nested structure with "master" -> "tasks"
        if isinstance(data, dict) and "master" in data and "tasks" in data["master"]:
            tasks = data["master"]["tasks"]
        elif isinstance(data, dict) and "tasks" in data:
            tasks = data["tasks"]
        else:
            tasks = data
        
        for task in tasks:
            # Ensure task is a dictionary
            if not isinstance(task, dict):
                continue
                
            if any(str(task.get("id")) == str(tid) for tid in [7, 9, 10, 11, 22]):
                desc = json.dumps(task).lower()
                # Check for CLI command patterns, not MCP operations
                assert "mcp-commit-story new-entry" not in desc, f"Task {task['id']} still mentions new-entry CLI command"
                assert "mcp-commit-story add-reflection" not in desc, f"Task {task['id']} still mentions add-reflection CLI command"
                assert "setup" in desc or "mcp" in desc, f"Task {task['id']} does not mention setup CLI or MCP operation" 