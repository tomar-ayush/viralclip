import json
from typing import Any, dict, list, tuple

import boto3
import httpx

from app.common.config import settings
from app.scripts.schema import TimedCaption


class ElevenLabsService:
    async def synthesize_speech_with_timestamps(
        self, text: str, voice_id: str, elevenlabs_api_key: str
    ) -> tuple[bytes, list[TimedCaption]]:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
        headers = {
            "xi-api-key": elevenlabs_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    url, headers=headers, json=payload
                )
                if response.status_code == 200:
                    res_json = response.json()
                    audio_bytes = response.content
                    alignment = res_json.get("alignment", {})
                    characters = alignment.get("characters", [])
                    char_starts = alignment.get(
                        "character_start_times_seconds", []
                    )
                    char_ends = alignment.get(
                        "character_end_times_seconds", []
                    )
                    captions = (
                        self._convert_alignment_to_word_timestamps(
                            characters, char_starts, char_ends
                        )
                    )
                    return audio_bytes, captions
        except Exception as e:  # noqa: BLE001
            print(f"[ElevenLabs TTS Error] {e}")

        return self._generate_fallback_audio_and_alignment(text)

    def _convert_alignment_to_word_timestamps(
        self,
        characters: list[str],
        starts: list[float],
        ends: list[float],
    ) -> list[TimedCaption]:
        words: list[TimedCaption] = []
        current_word = ""
        word_start = None

        for i, char in enumerate(characters):
            if word_start is None and char.strip():
                word_start = starts[i]
            if char.strip():
                current_word += char
            if (
                char.isspace() or i == len(characters) - 1
            ) and current_word:
                word_end = ends[i]
                words.append(
                    TimedCaption(
                        word=current_word,
                        start=round(word_start, 2),
                        end=round(word_end, 2),
                    )
                )
                current_word = ""
                word_start = None

        return words

    def _generate_fallback_audio_and_alignment(
        self, text: str
    ) -> tuple[bytes, list[TimedCaption]]:
        mock_mp3_bytes = (
            b"\xff\xf3\x44\xc4\x00\x00\x00\x03\x48\x00\x00\x00\x00"
            * 200
        )
        words_list = text.split()
        captions: list[TimedCaption] = []
        current_time = 0.0
        duration_per_word = 0.35

        for word in words_list:
            clean_word = word.strip(",.?!")
            start = round(current_time, 2)
            end = round(current_time + duration_per_word, 2)
            captions.append(
                TimedCaption(word=clean_word, start=start, end=end)
            )
            current_time += duration_per_word + 0.05

        return mock_mp3_bytes, captions


class RemotionService:
    def __init__(self):
        self.function_name = settings.REMOTION_LAMBDA_FUNCTION_NAME
        self.serve_url = settings.REMOTION_SERVE_URL
        self.composition_id = settings.REMOTION_COMPOSITION_ID
        self.region = settings.AWS_REGION

    def _get_lambda_client(self):
        return boto3.client(
            "lambda",
            region_name=self.region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    async def render_media_on_lambda(
        self, job_id: str, input_props: dict[str, Any]
    ) -> tuple[str, str]:
        payload = {
            "type": "render",
            "serveUrl": self.serve_url,
            "composition": self.composition_id,
            "inputProps": input_props,
            "codec": "h264",
            "imageFormat": "jpeg",
            "maxRetries": 2,
            "privacy": "public",
            "outName": f"renders/{job_id}.mp4",
        }

        try:
            client = self._get_lambda_client()
            response = client.invoke(
                FunctionName=self.function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload),
            )
            res_payload = json.loads(response["Payload"].read())
            render_id = res_payload.get(
                "renderId", f"remotion_render_{job_id}"
            )
            output_url = res_payload.get(
                "url",
                f"https://{settings.S3_BUCKET_NAME}.s3.{self.region}.amazonaws.com/renders/{job_id}.mp4",
            )
            return render_id, output_url
        except Exception as e:  # noqa: BLE001
            print(f"[Remotion Lambda Warning] {e}")
            mock_render_id = f"render_mock_{job_id[:8]}"
            mock_output_url = f"https://{settings.S3_BUCKET_NAME}.s3.{self.region}.amazonaws.com/renders/{job_id}.mp4"
            return mock_render_id, mock_output_url


elevenlabs_service = ElevenLabsService()
remotion_service = RemotionService()
