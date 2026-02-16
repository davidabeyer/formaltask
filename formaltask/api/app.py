"""FastAPI application with OpenAPI documentation for all endpoints."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# --- Request/Response Models ---


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service health status")
    version: str = Field(description="API version")

    model_config = {"json_schema_extra": {"example": {"status": "ok", "version": "0.1.0"}}}


class TaskCreate(BaseModel):
    """Create a new task."""

    title: str = Field(description="Task title", min_length=1, max_length=200)
    epic: str = Field(description="Epic this task belongs to")
    description: str = Field(default="", description="Detailed task description")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Add user authentication",
                "epic": "auth-system",
                "description": "Implement JWT-based authentication for API endpoints",
            }
        }
    }


class TaskResponse(BaseModel):
    """Task details."""

    id: int = Field(description="Task ID")
    title: str = Field(description="Task title")
    epic: str = Field(description="Epic name")
    status: str = Field(description="Current status")
    description: str = Field(default="", description="Task description")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 42,
                "title": "Add user authentication",
                "epic": "auth-system",
                "status": "in_progress",
                "description": "Implement JWT-based authentication for API endpoints",
            }
        }
    }


class TaskUpdate(BaseModel):
    """Update task fields."""

    title: str | None = Field(default=None, description="New title")
    status: str | None = Field(default=None, description="New status")
    description: str | None = Field(default=None, description="New description")

    model_config = {
        "json_schema_extra": {
            "example": {"title": None, "status": "completed", "description": None}
        }
    }


class TaskListResponse(BaseModel):
    """List of tasks."""

    tasks: list[TaskResponse] = Field(description="Task list")
    total: int = Field(description="Total count")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tasks": [
                    {
                        "id": 42,
                        "title": "Add user authentication",
                        "epic": "auth-system",
                        "status": "in_progress",
                        "description": "Implement JWT-based auth",
                    }
                ],
                "total": 1,
            }
        }
    }


class EpicResponse(BaseModel):
    """Epic details."""

    name: str = Field(description="Epic identifier")
    status: str = Field(description="Current status")
    task_count: int = Field(description="Number of tasks")

    model_config = {
        "json_schema_extra": {
            "example": {"name": "auth-system", "status": "in_progress", "task_count": 5}
        }
    }


class EpicListResponse(BaseModel):
    """List of epics."""

    epics: list[EpicResponse] = Field(description="Epic list")

    model_config = {
        "json_schema_extra": {
            "example": {
                "epics": [
                    {"name": "auth-system", "status": "in_progress", "task_count": 5},
                    {"name": "api-v2", "status": "planning", "task_count": 10},
                ]
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str = Field(description="Error message")

    model_config = {"json_schema_extra": {"example": {"detail": "Task not found"}}}


# --- Application Factory ---


def create_app() -> FastAPI:
    """Create FastAPI application with OpenAPI documentation."""
    app = FastAPI(
        title="FormalTask API",
        version="0.1.0",
        description="Structured task management for AI-assisted development workflows.",
    )

    @app.get(
        "/api/health",
        response_model=HealthResponse,
        summary="Health check",
        description="Returns service health status and API version.",
    )
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get(
        "/api/tasks",
        response_model=TaskListResponse,
        summary="List tasks",
        description="List all tasks, optionally filtered by epic.",
    )
    def list_tasks(epic: str | None = None):
        return {"tasks": [], "total": 0}

    @app.post(
        "/api/tasks",
        response_model=TaskResponse,
        status_code=201,
        summary="Create task",
        description="Create a new task in the specified epic.",
        responses={404: {"model": ErrorResponse, "description": "Epic not found"}},
    )
    def create_task(body: TaskCreate):
        return {
            "id": 1,
            "title": body.title,
            "epic": body.epic,
            "status": "pending",
            "description": body.description,
        }

    @app.get(
        "/api/tasks/{task_id}",
        response_model=TaskResponse,
        summary="Get task",
        description="Get a task by its ID.",
        responses={404: {"model": ErrorResponse, "description": "Task not found"}},
    )
    def get_task(task_id: int):
        raise HTTPException(status_code=404, detail="Task not found")

    @app.put(
        "/api/tasks/{task_id}",
        response_model=TaskResponse,
        summary="Update task",
        description="Update an existing task's title, status, or description.",
        responses={404: {"model": ErrorResponse, "description": "Task not found"}},
    )
    def update_task(task_id: int, body: TaskUpdate):
        raise HTTPException(status_code=404, detail="Task not found")

    @app.get(
        "/api/epics",
        response_model=EpicListResponse,
        summary="List epics",
        description="List all epics and their status.",
    )
    def list_epics():
        return {"epics": []}

    @app.get(
        "/api/epics/{epic_name}",
        response_model=EpicResponse,
        summary="Get epic",
        description="Get an epic by name.",
        responses={404: {"model": ErrorResponse, "description": "Epic not found"}},
    )
    def get_epic(epic_name: str):
        raise HTTPException(status_code=404, detail="Epic not found")

    return app
