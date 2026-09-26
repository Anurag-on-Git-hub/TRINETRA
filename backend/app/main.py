import os, math, asyncio, random
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from jose import jwt
from passlib.context import CryptContext

app = FastAPI(title="TRINETRA API", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SECRET = os.getenv("JWT_SECRET", "dev-secret")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Deterministic demo dataset. Replace repository layer with SQLAlchemy models
# when connecting the production persistence layer.
CAMERAS = [
    {"id":"C01","name":"Ring Road North","lat":28.6139,"lng":77.2090,"status":"ONLINE","fps":25},
    {"id":"C04","name":"Central Avenue","lat":28.6200,"lng":77.2150,"status":"ONLINE","fps":24},
    {"id":"C07","name":"Metro Junction","lat":28.6255,"lng":77.2200,"status":"DEGRADED","fps":22},
    {"id":"C12","name":"Tech Park Gate","lat":28.6320,"lng":77.2260,"status":"ONLINE","fps":25},
    {"id":"C19","name":"East Bypass","lat":28.6380,"lng":77.2350,"status":"ONLINE","fps":24},
]
VEHICLES = [
    {"id":"V-00127","plate":"MP04AB1234","color":"White","type":"SUV","make":"Mahindra","model":"XUV","confidence":0.97},
    {"id":"V-00128","plate":"MP04AB1284","color":"White","type":"SUV","make":"Mahindra","model":"XUV","confidence":0.84},
    {"id":"V-00129","plate":"MP04AB1239","color":"White","type":"SUV","make":"Mahindra","model":"XUV","confidence":0.78},
    {"id":"V-00130","plate":"MP04AB1294","color":"White","type":"SUV","make":"Mahindra","model":"XUV","confidence":0.73},
    {"id":"V-00211","plate":"DL08CA5521","color":"Black","type":"Sedan","make":"Hyundai","model":"Verna","confidence":0.94},
    {"id":"V-00212","plate":"DL09CQ7312","color":"Red","type":"Hatchback","make":"Maruti","model":"Baleno","confidence":0.91},
]
def obs(v, cam, ts, i):
    c=next(x for x in CAMERAS if x["id"]==cam)
    return {"id":f"O-{v['id']}-{i}","vehicle_id":v["id"],"plate":v["plate"],"plate_confidence":0.95,
            "color":v["color"],"type":v["type"],"camera_id":cam,"timestamp":ts,
            "lat":c["lat"],"lng":c["lng"],"direction":"NE","speed":42+i*2}
base=datetime.now(timezone.utc)-timedelta(minutes=28)
OBS=[]
for v in VEHICLES:
    route=["C01","C04","C07","C12","C19"] if v["id"].endswith(("127","128","129","130")) else ["C04","C07","C12"]
    for i,cam in enumerate(route):
        OBS.append(obs(v,cam,base+timedelta(minutes=i*6),i))

ALERTS=[
 {"id":"A-1001","severity":"HIGH","type":"Identity Conflict","vehicle":"V-00127","camera":"C12","status":"OPEN","reason":"Partially occluded plate; multi-factor verification required.","time":datetime.now(timezone.utc).isoformat()},
 {"id":"A-1002","severity":"MEDIUM","type":"Traffic Spike","vehicle":"—","camera":"C07","status":"OPEN","reason":"Traffic volume exceeded rolling baseline.","time":datetime.now(timezone.utc).isoformat()},
 {"id":"A-1003","severity":"LOW","type":"Camera Health","vehicle":"—","camera":"C07","status":"OPEN","reason":"FPS dropped below configured threshold.","time":datetime.now(timezone.utc).isoformat()},
]

class Login(BaseModel):
    email: str
    password: str
class MatchRequest(BaseModel):
    plate: str
    color: Optional[str]=None
    type: Optional[str]=None
    vehicle_id: Optional[str]=None

def token(email):
    return jwt.encode({"sub":email,"exp":datetime.now(timezone.utc)+timedelta(hours=8)}, SECRET, algorithm="HS256")

@app.get("/api/health")
def health(): return {"status":"ok","ai_mode":"demo","database":"demo-repository","version":"1.0.0"}

@app.post("/api/auth/login")
def login(body: Login):
    if body.email=="admin@trinetra.local" and body.password=="Admin@123":
        return {"access_token":token(body.email),"token_type":"bearer","user":{"email":body.email,"role":"ADMIN"}}
    raise HTTPException(401,"Invalid credentials")

@app.get("/api/dashboard/stats")
def stats():
    return {"cameras_total":128,"cameras_online":124,"vehicles_today":18429,"active_tracks":342,
            "ocr_confidence":94.7,"traffic_density":68,"active_alerts":len([a for a in ALERTS if a["status"]=="OPEN"])}

@app.get("/api/cameras")
def cameras(): return CAMERAS

@app.get("/api/vehicles")
def vehicles(q: str=""):
    q=q.lower()
    return [v for v in VEHICLES if not q or q in v["plate"].lower() or q in v["id"].lower()]

@app.get("/api/vehicles/{vid}")
def vehicle(vid: str):
    v=next((x for x in VEHICLES if x["id"]==vid),None)
    if not v: raise HTTPException(404,"Vehicle not found")
    observations=[o for o in OBS if o["vehicle_id"]==vid]
    return {**v,"observations":observations,"first_seen":observations[0]["timestamp"] if observations else None,
            "last_seen":observations[-1]["timestamp"] if observations else None,"total_sightings":len(observations)}

@app.get("/api/tracking/{plate}")
def tracking(plate: str):
    v=next((x for x in VEHICLES if x["plate"].lower()==plate.lower()),None)
    if not v: raise HTTPException(404,"Vehicle not found")
    return vehicle(v["id"])

@app.post("/api/ai/vehicle-match")
def match(body: MatchRequest):
    q=body.plate.upper().replace(" ","")
    def plate_score(p):
        n=max(len(q),len(p)); return sum(a==b for a,b in zip(q,p))/n
    out=[]
    for v in VEHICLES[:4]:
        ps=plate_score(v["plate"])
        appearance=0.96 if v["id"]=="V-00127" else 0.72+random.Random(v["id"]).random()*0.12
        color=1.0 if not body.color or body.color.lower()==v["color"].lower() else .25
        typ=1.0 if not body.type or body.type.lower()==v["type"].lower() else .2
        route=0.93 if v["id"]=="V-00127" else 0.61
        temporal=0.91 if v["id"]=="V-00127" else 0.68
        weights={"plate":.45,"appearance":.25,"color":.08,"type":.07,"route":.02,"temporal":.03}
        score=(ps*weights["plate"]+appearance*weights["appearance"]+color*weights["color"]+
               typ*weights["type"]+route*weights["route"]+temporal*weights["temporal"])
        reasons=["Plate characters strongly match" if ps>.75 else "Plate is partially ambiguous",
                 "Vehicle appearance is similar" if appearance>.8 else "Appearance similarity is moderate",
                 "Vehicle color matches" if color>.9 else "Color conflicts",
                 "Vehicle type matches" if typ>.9 else "Vehicle type conflicts",
                 "Route transition is plausible" if route>.8 else "Route evidence is weak"]
        out.append({"vehicle":v,"plate_similarity":round(ps,3),"appearance_similarity":round(appearance,3),
                    "color_similarity":color,"type_similarity":typ,"route_consistency":route,
                    "temporal_consistency":temporal,"final_score":round(score,3),
                    "confidence":"HIGH" if score>=.85 else "MEDIUM" if score>=.65 else "LOW","explanation":reasons})
    return {"mode":"DEMO","query":body.model_dump(),"matches":sorted(out,key=lambda x:x["final_score"],reverse=True)}

@app.get("/api/alerts")
def alerts(): return ALERTS

@app.put("/api/alerts/{aid}/resolve")
def resolve(aid: str):
    a=next((x for x in ALERTS if x["id"]==aid),None)
    if not a: raise HTTPException(404,"Alert not found")
    a["status"]="RESOLVED"; return a

@app.get("/api/analytics")
def analytics():
    return {"hourly":[{"hour":f"{h:02d}:00","vehicles":420+h*17} for h in range(8,19)],
            "types":[{"name":"SUV","value":38},{"name":"Sedan","value":27},{"name":"Hatchback","value":21},{"name":"Two-wheeler","value":14}],
            "cameras":[{"camera":c["id"],"vehicles":120+i*47} for i,c in enumerate(CAMERAS)]}

@app.websocket("/ws/live")
async def live(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            v=random.choice(VEHICLES); c=random.choice(CAMERAS)
            await ws.send_json({"event":"vehicle_detected","vehicle_id":v["id"],"plate":v["plate"],
                                "camera_id":c["id"],"timestamp":datetime.now(timezone.utc).isoformat(),
                                "lat":c["lat"]+random.uniform(-.001,.001),"lng":c["lng"]+random.uniform(-.001,.001)})
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        pass

# Production single-service mode: serve the Vite build from FastAPI.
# The local Docker Compose setup still runs frontend and backend separately.
STATIC_DIR = "/app/static"
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "ws/live":
            raise HTTPException(404, "Not found")
        candidate = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
