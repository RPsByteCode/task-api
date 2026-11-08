from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

import sqlite3

DB_PATH = "tasks.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  #Rows Behaves Like Dicts
    return conn

def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO tasks (title,done) VALUES (?,?)",
            [
                ("Learn HTTP",1),
                ("Build a CRUD API",0),
                ("Publish to GitHub", 0)
            ]
        )
    conn.commit()
    conn.close()

init_db()

def row_to_task(row):
    return {"id": row["id"],"title": row["title"], "done": bool(row["done"])}

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A Small In-Memory To-Do list API with Full CRUD.",
)

# In-memory Database
tasks = [
    {"id":1, "title":"Learn HTTP", "done":True},
    {"id":2, "title":"Build a CRUD API", "done":False},
    {"id":3, "title":"Publish to GitHub", "done":False},

]

@app.get("/", summary="API info")
def root():
    return {
        "name":"Task API",
        "version":"1.0",
        "endpoints":["/tasks"]
    }

@app.get("/health", summary="Health check")
def health():
    return {"status":"ok"}

@app.get("/tasks", summary="List all tasks")
def list_tasks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [row_to_task(r) for r in rows]

@app.get("/tasks/{task_id}", summary="Get one task",
         description="Returns one task, or 404 if the id does not exist.")
def get_task(task_id:int):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()

    if row is None:
        return JSONResponse(
            status_code = 404,
            content= {"error":f"Task {task_id} not found"}
        )
    return row_to_task(row) 

@app.post(
    "/tasks",
    status_code=201,
    summary="Create a task",
    description="Creates a task with the next free id. Returns 400 if title is missing or empty.",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}},
                        "required": ["title"],
                    },
                    "example": {"title": "Buy milk"},
                }
            },
        }
    },
)
async def create_task(request:Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error":"Request Body must be valid JSON"},
        )
    title = body.get("title") if isinstance(body,dict) else None
    if not isinstance(title,str) or not title.strip():
        return JSONResponse(
            status_code=400,
            content={"error":"Title is required & must be a non-empty string"},
        )
    new_id = max((t["id"] for t in tasks), default=0) +1

    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?,?)",
        (title.strip(), 0),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    # task = {"id":new_id, "title":title.strip(), "done":False}
    # tasks.append(task)
    return {"id":new_id, "title":title.strip(), "done": False}


@app.put(
    "/tasks/{task_id}",
    summary="Update a task",
    description="Changes title and/or done. Returns 404 for an unknown id, 400 for an invalid body.",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "done": {"type": "boolean"},
                        },
                    },
                    "example": {"done": True},
                }
            },
        }
    },
)
async def update_task(task_id:int, request: Request):
    task = next((t for t in tasks if t["id"]== task_id), None)
    if task is None:
        return JSONResponse(
            status_code= 404,
            content= {"error": f"Task {task_id} not found"}
        )
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error":"Request body must be valid JSON"}
        )
    if not isinstance(body,  dict) or ("title"  not in body and "done" not in body):
        return JSONResponse(
            status_code= 400,
            content={"error": "Provide title and/or done"}
        )
    if "title" in body and (
        not isinstance(body["title"], str) or not body["title"].strip()
    ):
        return JSONResponse(
            status_code=400,
            content={"error": "Title must be a non-empty string"}
        )
    if "done" in body and (not isinstance(body["done"], bool)):
        return JSONResponse(
            status_code=400,
            content={"error": "Done must be true/false"}
        )

    if "title" in body:
        task["title"] = body["title"].strip()
    if "done" in body:
        task["done"] = body["done"]
    return task

@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task",
            description="Removes the task. Returns 204 with no body, or 404 for an unknown id.")
def delete_task(task_id:int):
    for index,task in enumerate(tasks):
        if task["id"]== task_id :
            tasks.pop(index)
            return Response(status_code=204)
    return JSONResponse(
        status_code=404,
        content={"error":f"Task {task_id} not found"}
    )
