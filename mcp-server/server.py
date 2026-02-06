#!/usr/bin/env python3
"""
Simple Task Tracker MCP Server
A Kanban-style task tracker with Todo, In Progress, and Done columns.
"""

import json
from pathlib import Path
from typing import Literal
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field

# Define task status type
TaskStatus = Literal["todo", "in_progress", "done"]

# Data storage file
DATA_FILE = Path("tasks.json")

# Task model
class Task(BaseModel):
    id: int
    title: str
    description: str = ""
    status: TaskStatus = "todo"

# In-memory task storage
tasks: dict[int, Task] = {}
next_id = 1

# Load tasks from file
def load_tasks():
    global tasks, next_id
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            tasks = {int(k): Task(**v) for k, v in data.get('tasks', {}).items()}
            next_id = data.get('next_id', 1)

# Save tasks to file
def save_tasks():
    with open(DATA_FILE, 'w') as f:
        json.dump({
            'tasks': {str(k): v.model_dump() for k, v in tasks.items()},
            'next_id': next_id
        }, f, indent=2)

# Initialize server
app = Server("task-tracker")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available task management tools."""
    return [
        Tool(
            name="add_task",
            description="Add a new task to the tracker",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title (required)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description (optional)"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "done"],
                        "description": "Initial status (default: todo)"
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="list_tasks",
            description="List all tasks, optionally filtered by status",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "done", "all"],
                        "description": "Filter by status (default: all)"
                    }
                }
            }
        ),
        Tool(
            name="move_task",
            description="Move a task to a different status column",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to move"
                    },
                    "new_status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "done"],
                        "description": "New status for the task"
                    }
                },
                "required": ["task_id", "new_status"]
            }
        ),
        Tool(
            name="delete_task",
            description="Delete a task from the tracker",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to delete"
                    }
                },
                "required": ["task_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution."""
    
    if name == "add_task":
        global next_id
        title = arguments["title"]
        description = arguments.get("description", "")
        status = arguments.get("status", "todo")
        
        task = Task(
            id=next_id,
            title=title,
            description=description,
            status=status
        )
        tasks[next_id] = task
        next_id += 1
        save_tasks()
        
        return [TextContent(
            type="text",
            text=f"✅ Task created successfully!\n\nID: {task.id}\nTitle: {task.title}\nStatus: {task.status}"
        )]
    
    elif name == "list_tasks":
        status_filter = arguments.get("status", "all")
        
        if not tasks:
            return [TextContent(
                type="text",
                text="📋 No tasks found. Add your first task to get started!"
            )]
        
        # Filter tasks
        if status_filter == "all":
            filtered_tasks = list(tasks.values())
        else:
            filtered_tasks = [t for t in tasks.values() if t.status == status_filter]
        
        if not filtered_tasks:
            return [TextContent(
                type="text",
                text=f"📋 No tasks found with status '{status_filter}'"
            )]
        
        # Format output as Kanban board
        todo_tasks = [t for t in filtered_tasks if t.status == "todo"]
        in_progress_tasks = [t for t in filtered_tasks if t.status == "in_progress"]
        done_tasks = [t for t in filtered_tasks if t.status == "done"]
        
        output = "# 📋 Task Board\n\n"
        
        if status_filter == "all" or status_filter == "todo":
            output += "## 📝 Todo\n"
            if todo_tasks:
                for task in todo_tasks:
                    output += f"- **#{task.id}** {task.title}\n"
                    if task.description:
                        output += f"  _{task.description}_\n"
            else:
                output += "_No tasks_\n"
            output += "\n"
        
        if status_filter == "all" or status_filter == "in_progress":
            output += "## 🚀 In Progress\n"
            if in_progress_tasks:
                for task in in_progress_tasks:
                    output += f"- **#{task.id}** {task.title}\n"
                    if task.description:
                        output += f"  _{task.description}_\n"
            else:
                output += "_No tasks_\n"
            output += "\n"
        
        if status_filter == "all" or status_filter == "done":
            output += "## ✅ Done\n"
            if done_tasks:
                for task in done_tasks:
                    output += f"- **#{task.id}** {task.title}\n"
                    if task.description:
                        output += f"  _{task.description}_\n"
            else:
                output += "_No tasks_\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "move_task":
        task_id = arguments["task_id"]
        new_status = arguments["new_status"]
        
        if task_id not in tasks:
            return [TextContent(
                type="text",
                text=f"❌ Task #{task_id} not found"
            )]
        
        task = tasks[task_id]
        old_status = task.status
        task.status = new_status
        save_tasks()
        
        status_names = {
            "todo": "📝 Todo",
            "in_progress": "🚀 In Progress",
            "done": "✅ Done"
        }
        
        return [TextContent(
            type="text",
            text=f"✅ Task #{task_id} moved!\n\n{task.title}\n{status_names[old_status]} → {status_names[new_status]}"
        )]
    
    elif name == "delete_task":
        task_id = arguments["task_id"]
        
        if task_id not in tasks:
            return [TextContent(
                type="text",
                text=f"❌ Task #{task_id} not found"
            )]
        
        task = tasks.pop(task_id)
        save_tasks()
        
        return [TextContent(
            type="text",
            text=f"🗑️ Task deleted!\n\nID: #{task.id}\nTitle: {task.title}"
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"❌ Unknown tool: {name}"
        )]

async def main():
    """Run the MCP server."""
    import sys
    from mcp.server.stdio import stdio_server
    
    # Load existing tasks
    load_tasks()
    
    # Log to stderr so stdout stays clean for JSON-RPC
    print("Task Tracker MCP server running (stdio). Waiting for client...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())