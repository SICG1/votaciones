from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

class Member(BaseModel):
    username: str
    rut: str
    role: str  # 'admin', 'manager', 'user'

class Candidate(BaseModel):
    id: int
    name: str
    votes: int = 0

members: Dict[str, Member] = {}
candidates: Dict[int, Candidate] = {}
votes: Dict[str, int] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection)

manager = ConnectionManager()

# Utility functions

def require_role(username: str, roles: list[str]):
    member = members.get(username)
    if not member or member.role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    return member

# Routes

@app.post("/members")
async def add_member(acting_user: str, member: Member):
    require_role(acting_user, ["admin", "manager"])
    if member.username in members:
        raise HTTPException(status_code=400, detail="Member already exists")
    members[member.username] = member
    return member

@app.post("/candidates")
async def add_candidate(acting_user: str, candidate: Candidate):
    require_role(acting_user, ["admin", "manager"])
    if candidate.id in candidates:
        raise HTTPException(status_code=400, detail="Candidate id exists")
    candidates[candidate.id] = candidate
    await manager.broadcast({"event": "candidate_added", "candidate": candidate.dict()})

@app.post("/vote")
async def vote(acting_user: str, candidate_id: int):
    voter = require_role(acting_user, ["admin", "manager", "user"])
    if acting_user in votes:
        raise HTTPException(status_code=400, detail="User already voted")
    candidate = candidates.get(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.votes += 1
    votes[acting_user] = candidate_id
    await manager.broadcast({"event": "vote", "candidate_id": candidate_id, "votes": candidate.votes})
    return {"candidate": candidate.name, "votes": candidate.votes}

@app.get("/results")
async def results():
    return {cid: c.votes for cid, c in candidates.items()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
