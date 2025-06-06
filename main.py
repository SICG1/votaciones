from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional

app = FastAPI()

DATABASE_URL = "sqlite:///database.db"
engine = create_engine(DATABASE_URL, echo=False)


class Member(SQLModel, table=True):
    username: str = Field(primary_key=True)
    rut: str
    role: str  # 'admin', 'manager', 'user'


class Candidate(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    votes: int = 0


class Vote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    voter_username: str = Field(foreign_key="member.username")
    candidate_id: int = Field(foreign_key="candidate.id")


@app.on_event("startup")
def on_startup() -> None:
    SQLModel.metadata.create_all(engine)

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
    with Session(engine) as session:
        member = session.get(Member, username)
        if not member or member.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return member

# Routes

@app.post("/members")
async def add_member(acting_user: str, member: Member):
    require_role(acting_user, ["admin", "manager"])
    with Session(engine) as session:
        if session.get(Member, member.username):
            raise HTTPException(status_code=400, detail="Member already exists")
        session.add(member)
        session.commit()
        session.refresh(member)
        return member

@app.post("/candidates")
async def add_candidate(acting_user: str, candidate: Candidate):
    require_role(acting_user, ["admin", "manager"])
    with Session(engine) as session:
        if session.get(Candidate, candidate.id):
            raise HTTPException(status_code=400, detail="Candidate id exists")
        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        await manager.broadcast({"event": "candidate_added", "candidate": candidate.dict()})

@app.post("/vote")
async def vote(acting_user: str, candidate_id: int):
    require_role(acting_user, ["admin", "manager", "user"])
    with Session(engine) as session:
        existing_vote = session.exec(select(Vote).where(Vote.voter_username == acting_user)).first()
        if existing_vote:
            raise HTTPException(status_code=400, detail="User already voted")
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        candidate.votes += 1
        vote_entry = Vote(voter_username=acting_user, candidate_id=candidate_id)
        session.add(vote_entry)
        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        await manager.broadcast({"event": "vote", "candidate_id": candidate_id, "votes": candidate.votes})
        return {"candidate": candidate.name, "votes": candidate.votes}

@app.get("/results")
async def results():
    with Session(engine) as session:
        cands = session.exec(select(Candidate)).all()
        return {c.id: c.votes for c in cands}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
