import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.redis import get_redis_client

router = APIRouter(prefix="/ws", tags=["WebSockets"])


@router.websocket("/jobs/{job_id}")
async def job_progress_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket streaming endpoint:
    Subscribes to Redis PubSub channel 'job_progress:{job_id}' and pushes real-time render progress (0-100%).
    """
    await websocket.accept()
    redis_client = get_redis_client()
    pubsub = redis_client.pubsub()
    channel_name = f"job_progress:{job_id}"

    try:
        await pubsub.subscribe(channel_name)
        # Send initial confirmation message
        await websocket.send_json({
            "event": "subscribed",
            "job_id": job_id,
            "message": f"Subscribed to real-time progress stream for job {job_id}"
        })

        while True:
            # Poll for message from Redis pubsub channel with timeout
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data_str = message.get("data")
                if data_str:
                    await websocket.send_text(data_str)
                    
                    # Parse data to auto-close socket if finished
                    try:
                        data_json = json.loads(data_str)
                        status = data_json.get("status")
                        if status in ["COMPLETED", "FAILED"]:
                            # Wait brief moment then close gracefully
                            await asyncio.sleep(0.5)
                            await websocket.close(code=1000, reason=f"Job terminated with status: {status}")
                            break
                    except Exception:
                        pass
            
            # Keep connection alive
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected from job_progress stream for job {job_id}")
    except Exception as e:
        print(f"[WebSocket Error] Exception in stream for job {job_id}: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
