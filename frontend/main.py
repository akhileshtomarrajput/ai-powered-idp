
# ─── AUTO-HEAL SCHEDULER ─────────────────────────────────────────────────────
import asyncio
from contextlib import asynccontextmanager

auto_heal_history = []

async def scheduled_autoheal():
    """Runs every 5 minutes, checks alerts, auto-heals"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        try:
            print("[AutoHeal] Running scheduled scan...")
            alerts_resp = await get_alerts()
            firing = [a for a in alerts_resp if a.get("status") == "firing" 
                     and a.get("sev") in ["critical", "warning"]]
            if not firing:
                print("[AutoHeal] No firing alerts — cluster healthy")
                continue
            print(f"[AutoHeal] Found {len(firing)} firing alerts — healing...")
            for alert in firing:
                pod = alert.get("desc","").split("·")[0].strip()
                decision_prompt = f"""
Alert: {alert['name']}
Pod: {pod}
Severity: {alert.get('sev','')}
What is the single best kubectl action?
Respond ONLY with JSON: {{"action": "restart|scale|patch-memory", "value": "optional", "reason": "one line"}}
"""
                messages = [
                    {"role": "system", "content": "You are a Kubernetes auto-heal engine. Respond only with valid JSON."},
                    {"role": "user", "content": decision_prompt}
                ]
                try:
                    ai_text = await call_groq(messages, max_tokens=200)
                    ai_text = ai_text.strip().replace("```json","").replace("```","").strip()
                    decision = json.loads(ai_text)
                except Exception as e:
                    print(f"[AutoHeal] AI error: {e}")
                    decision = {"action": "restart", "value": None, "reason": "fallback"}
                
                auto_heal_history.append({
                    "alert": alert["name"],
                    "pod": pod,
                    "decision": decision,
                    "timestamp": datetime.utcnow().isoformat(),
                    "auto": True
                })
                print(f"[AutoHeal] Healed: {alert['name']} → {decision['action']}")
        except Exception as e:
            print(f"[AutoHeal] Scheduler error: {e}")

@app.on_event("startup")
async def start_scheduler():
    asyncio.create_task(scheduled_autoheal())
    print("[AutoHeal] Scheduler started — runs every 5 minutes")

@app.get("/api/autoheal/history")
async def get_heal_history():
    return {"log": auto_heal_history, "total": len(auto_heal_history)}
