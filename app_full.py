"""
Antahkarana AI - Full Prototype v1.0
Sprints 1-3 merged: Buddhi + Chitta + Signal Extraction
Wellness restoration for students - NOT spiritual elevation
© Conscious Bridge Labs, Bengaluru | Founder - Nagesh Jayanti
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date
import numpy as np
import cv2

app = FastAPI(
    title="Antahkarana AI",
    description="Wellness restoration tool inspired by Pancha Kosha. For students and working adults. © Conscious Bridge Labs",
    version="1.0.0"
)

# ===== CHITTA MEMORY =====
class ChittaMemory:
    def __init__(self):
        self.memories = []
    
    def _vectorize(self, data: dict) -> List[float]:
        return [
            data.get('sleep_hours',7)/12, data.get('hrv_rmssd',40)/100,
            data.get('breath_coherence',0.5), data.get('sattva',40)/100,
            data.get('rajas',40)/100, data.get('tamas',20)/100,
            data.get('mood_score',6)/10, data.get('witness_rating',6)/10,
            data.get('jyotish_stress',0.5), data.get('reflection_words',80)/200
        ]
    
    def store(self, user_id: str, date_str: str, data: dict, outcome: dict):
        self.memories.append({
            'user_id': user_id, 'date': date_str,
            'vector': self._vectorize(data), 'data': data, 'outcome': outcome
        })
    
    def recall(self, user_id: str, current: dict, k: int = 3):
        if not self.memories: return []
        cur = np.array(self._vectorize(current))
        user_mems = [m for m in self.memories if m['user_id']==user_id]
        sims = []
        for m in user_mems:
            vec = np.array(m['vector'])
            sim = np.dot(cur, vec) / (np.linalg.norm(cur)*np.linalg.norm(vec)+1e-8)
            sims.append((sim, m))
        sims.sort(reverse=True, key=lambda x: x[0])
        return [{'date':m['date'],'similarity':round(float(s),2),
                 'practice':m['outcome'].get('practice'),
                 'hrv':m['data'].get('hrv_rmssd')} for s,m in sims[:k]]

# ===== SIGNAL EXTRACTORS =====
class ThermalExtractor:
    def extract(self, img_bytes: bytes) -> dict:
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None: raise ValueError("Invalid image")
        h,w = img.shape
        left = img[int(h*0.6):int(h*0.9), int(w*0.1):int(w*0.4)]
        right = img[int(h*0.6):int(h*0.9), int(w*0.6):int(w*0.9)]
        forehead = img[int(h*0.1):int(h*0.3), int(w*0.4):int(w*0.6)]
        to_temp = lambda r: 25 + (np.mean(r)/255)*15
        lt, rt, ft = to_temp(left), to_temp(right), to_temp(forehead)
        return {
            "left_hand_c": round(lt,1), "right_hand_c": round(rt,1),
            "hand_delta_c": round(abs(lt-rt),2),
            "forehead_hand_gradient": round(ft-((lt+rt)/2),2),
            "wellness_note": "Hand temp proxy for circulation, not aura"
        }

class HRVExtractor:
    def extract(self, rr: List[float]) -> dict:
        if len(rr) < 30: raise ValueError("Need 30+ RR intervals")
        arr = np.array(rr)
        rmssd = np.sqrt(np.mean(np.diff(arr)**2))
        pnn50 = np.sum(np.abs(np.diff(arr))>50)/len(np.diff(arr))*100
        coherence = max(0, min(1, 1 - (np.std(arr)/np.mean(arr))))
        state = "Low" if rmssd<20 else "Moderate" if rmssd<40 else "Good"
        return {
            "rmssd_ms": round(float(rmssd),1),
            "pnn50_percent": round(float(pnn50),1),
            "coherence_score": round(float(coherence),2),
            "mean_hr_bpm": round(60000/np.mean(arr),1),
            "wellness_interpretation": f"{state} parasympathetic - for recovery focus",
            "source": "ESC/NASPE standards"
        }

# ===== AGENTS =====
class AnnaAgent:
    def analyze(self, d): 
        return {'kosha':'annamaya','insight':f"Sleep {d['sleep_hours']}h",'conf':0.85 if d['sleep_hours']<6.5 else 0.6,'source':'Sleep Foundation'}

class PranaAgent:
    def analyze(self, d, h):
        if len(h)>=7:
            avg = sum(x['hrv_rmssd'] for x in h[-7:])/7
            if d['hrv_rmssd'] < avg*0.88:
                return {'kosha':'pranamaya','insight':'HRV down 12%','conf':0.78,'source':'Hatha Pradipika 2.7-10'}
        return {'kosha':'pranamaya','insight':'Stable','conf':0.5}

class ManoAgent:
    def analyze(self, d):
        if d['rajas']>50 and d['mood_score']<6:
            return {'kosha':'manomaya','insight':'High rajas','conf':0.72,'source':'YS 2.33'}
        return {'kosha':'manomaya','insight':'Ok','conf':0.55}

# ===== BUDDHI =====
class Buddhi:
    def __init__(self, chitta: ChittaMemory):
        self.chitta = chitta
        self.agents = [AnnaAgent(), PranaAgent(), ManoAgent()]
    
    def decide(self, data: dict, history: list, user_id: str, date_str: str):
        insights = [self.agents[0].analyze(data), self.agents[1].analyze(data, history), self.agents[2].analyze(data)]
        similar = self.chitta.recall(user_id, data)
        consistency = len([x for x in history[-7:] if x])/7 if len(history)>=7 else 0.8
        abhyasa, vairagya = (0.7,0.3) if consistency>=0.7 else (0.5,0.5)
        top = max([i for i in insights if i['conf']>0.6], key=lambda x:x['conf'], default=insights[0])
        practices = {'pranamaya':("Nadi Shodhana 1:2, 6 min","Hatha Pradipika 2.7-10"),
                     'annamaya':("Sleep window 10:30-6:30","Sleep Foundation"),
                     'manomaya':("5-min breath focus","YS 1.32")}
        practice, source = practices.get(top['kosha'], ("Walk 10 min","General"))
        if consistency<0.7 and "6 min" in practice: practice = practice.replace("6 min","4 min")
        rationale = top['insight']
        if similar: rationale += f". Chitta: similar to {similar[0]['date']} (sim {similar[0]['similarity']})"
        decision = {
            'chosen_kosha': top['kosha'], 'practice': practice, 'source': source,
            'rationale': rationale,
            'pantanjali_rule': f"1.12 abhyasa/vairagya {abhyasa}/{vairagya}",
            'wellness_goal': "Restore baseline for academic/social engagement",
            'spiritual_claim': None, 'chitta_recall': similar,
            'abhyasa': abhyasa, 'vairagya': vairagya
        }
        self.chitta.store(user_id, date_str, data, {'practice':practice})
        return decision

# ===== MODELS =====
class KoshaInput(BaseModel):
    user_id: str
    date: date
    sleep_hours: float = Field(..., ge=0, le=12)
    steps: int
    hrv_rmssd: float
    breath_coherence: float = 0.5
    sattva: int = Field(..., ge=0, le=100)
    rajas: int = Field(..., ge=0, le=100)
    tamas: int = Field(..., ge=0, le=100)
    mood_score: float = Field(..., ge=1, le=10)
    witness_rating: float = Field(..., ge=1, le=10)
    reflection_words: int = 0
    jyotish_stress: float = 0.5
    thermal_hand_c: Optional[float] = None

class HRVRequest(BaseModel):
    rr_intervals_ms: List[float]

# ===== INIT =====
chitta = ChittaMemory()
buddhi = Buddhi(chitta)
thermal = ThermalExtractor()
hrv_ext = HRVExtractor()
histories = {}

# ===== ENDPOINTS =====
@app.post("/extract/thermal")
async def extract_thermal(file: UploadFile = File(...)):
    data = await file.read()
    return thermal.extract(data)

@app.post("/extract/hrv")
async def extract_hrv(req: HRVRequest):
    return hrv_ext.extract(req.rr_intervals_ms)

@app.post("/ingest")
async def ingest(data: KoshaInput):
    if not 95 <= data.sattva + data.rajas + data.tamas <= 105:
        raise HTTPException(400, "Gunas sum ~100")
    hist = histories.get(data.user_id, [])
    decision = buddhi.decide(data.dict(), hist, data.user_id, str(data.date))
    hist.append(data.dict())
    histories[data.user_id] = hist[-30:]
    return decision

@app.get("/memory/{user_id}")
async def memory(user_id: str):
    mems = [m for m in chitta.memories if m['user_id']==user_id]
    return {"count": len(mems), "recent": mems[-3:]}

@app.get("/")
async def root():
    return {
        "name": "Antahkarana AI",
        "version": "1.0",
        "copyright": "© Conscious Bridge Labs, Bengaluru | Founder - Nagesh Jayanti",
        "principle": "Wellness restoration for students. Inspired by Vedanta, applied for daily life. Not a spiritual elevation platform.",
        "endpoints": ["/ingest", "/extract/thermal", "/extract/hrv", "/memory/{user_id}"]
    }
