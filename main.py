from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
# In-memory Database

tasks = [
    {"id":1, "title":"Learn HTTP", "done":True},
    {"id":2, "title":"Build a CRUD API", "done":False},
    {"id":3, "title":"Publish to GitHub", "done":False},

]

@app.get("/")
def root():
    return {
        "name":"Task API",
        "version":"1.0",
        "endpoints":["/tasks"]
    }

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/tasks")
def list_tasks():
    return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id:int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return JSONResponse(
        status_code = 404,
        content= {"error":f"Task {task_id} not found"}
    )

@app.post("/tasks", status_code=201)
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
    task = {"id":new_id, "title":title.strip(), "done":False}
    tasks.append(task)
    return task