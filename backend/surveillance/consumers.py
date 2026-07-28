import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger("audit")


class LiveStreamConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            user = self.scope.get("user", AnonymousUser())
            if user.is_anonymous:
                await self.close()
                return
            await self.accept()
            await self.channel_layer.group_add("live_stream", self.channel_name)
            from surveillance.ai.engine_instance import get_engine
            engine = get_engine()
            running = engine is not None and engine.is_running
            await self.send(text_data=json.dumps({"type": "status", "running": running}))
            self._stream_task = asyncio.ensure_future(self._stream_reader())
        except Exception as e:
            logger.warning(f"[WS] Connection failed: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "_stream_task") and self._stream_task:
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    pass
            await self.channel_layer.group_discard("live_stream", self.channel_name)
        except Exception as e:
            logger.warning(f"[WS] Disconnect error: {e}")

    async def _stream_reader(self):
        from surveillance.stream_queue import frame_queue
        loop = asyncio.get_running_loop()
        while True:
            try:
                data = await loop.run_in_executor(None, frame_queue.get)
                if self.channel_layer is None:
                    break
                await self.send(text_data=data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[WS] Stream reader error: {e}")
                await asyncio.sleep(0.01)

    async def engine_status(self, event):
        try:
            await self.send(text_data=json.dumps(event["data"]))
        except Exception as e:
            logger.warning(f"[WS] Engine status send failed: {e}")
