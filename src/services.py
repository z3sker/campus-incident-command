import asyncio

async def notify_new_incident(incident_id: int):
    print(f"[Event] New incident created: {incident_id}")
    await asyncio.sleep(0.1)