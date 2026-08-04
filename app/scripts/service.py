import json

import httpx

from app.scripts.schema import SceneSchema, ScriptResponse


class ScriptService:
    async def generate_script(
        self,
        topic: str,
        tone: str,
        target_duration_seconds: int,
        openai_api_key: str,
    ) -> ScriptResponse:
        system_prompt = (
            "You are an expert viral short-form video creator for TikTok, YouTube Shorts, and Instagram Reels. "
            "Generate a highly engaging, timed script schema for a vertical video. "
            "Return strictly a valid JSON object matching this schema:\n"
            "{\n"
            '  "hook": "Punchy 3-5 word attention grabber",\n'
            '  "topic": "topic name",\n'
            '  "tone": "tone name",\n'
            '  "total_estimated_duration": 30.0,\n'
            '  "scenes": [\n'
            "    {\n"
            '      "scene_number": 1,\n'
            '      "text": "narration text",\n'
            '      "visual_description": "visual cue description",\n'
            '      "duration_seconds": 6.0\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = f"Topic: {topic}\nTone: {tone}\nTarget Duration: {target_duration_seconds} seconds."

        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 200:
                    res_data = response.json()
                    content = res_data["choices"][0]["message"][
                        "content"
                    ]
                    parsed = json.loads(content)
                    return ScriptResponse(**parsed)
        except Exception as e:
            print(
                f"[LLM Script Warning] OpenAI request failed ({e}). Using fallback synthesis."
            )

        return self._generate_fallback_script(
            topic, tone, target_duration_seconds
        )

    def _generate_fallback_script(
        self, topic: str, tone: str, target_duration: int
    ) -> ScriptResponse:
        scenes = [
            SceneSchema(
                scene_number=1,
                text=f"Stop scrolling! Did you know about {topic}?",
                visual_description="Fast zoom-in on vibrant neon text reading 'DID YOU KNOW?'",
                duration_seconds=5.0,
            ),
            SceneSchema(
                scene_number=2,
                text="Here is why everyone is talking about it. First, it completely changes how we think about automation.",
                visual_description="Split screen showcasing high speed futuristic digital graphics.",
                duration_seconds=10.0,
            ),
            SceneSchema(
                scene_number=3,
                text="Second, top creators are leveraging this exact secret to go viral in 24 hours.",
                visual_description="Chart spiking upward with dramatic particle lighting effects.",
                duration_seconds=10.0,
            ),
            SceneSchema(
                scene_number=4,
                text="Comment your thoughts below and subscribe for more viral secrets!",
                visual_description="Call to action animated arrow pointing down to comment button.",
                duration_seconds=5.0,
            ),
        ]
        return ScriptResponse(
            hook=f"The secret behind {topic}!",
            topic=topic,
            tone=tone,
            total_estimated_duration=float(target_duration),
            scenes=scenes,
        )


script_service = ScriptService()
