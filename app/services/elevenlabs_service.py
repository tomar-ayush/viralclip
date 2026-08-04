import httpx
from typing import Dict, Any, List, Tuple
from app.schemas.script import TimedCaption


class ElevenLabsService:
    async def synthesize_speech_with_timestamps(
        self,
        text: str,
        voice_id: str,
        elevenlabs_api_key: str
    ) -> Tuple[bytes, List[TimedCaption]]:
        """
        Calls ElevenLabs TTS API with timestamps endpoint (/v1/text-to-speech/{voice_id}/with-timestamps).
        Returns raw audio MP3 bytes and word-level alignment timestamp list.
        """
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
        headers = {
            "xi-api-key": elevenlabs_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    res_json = response.json()
                    # Audio comes as base64 or binary depending on endpoint headers
                    audio_bytes = response.content
                    alignment = res_json.get("alignment", {})
                    characters = alignment.get("characters", [])
                    char_starts = alignment.get("character_start_times_seconds", [])
                    char_ends = alignment.get("character_end_times_seconds", [])

                    captions = self._convert_alignment_to_word_timestamps(characters, char_starts, char_ends)
                    return audio_bytes, captions
                else:
                    print(f"[ElevenLabs Warning] API returned status {response.status_code}. Using fallback synth.")
        except Exception as e:
            print(f"[ElevenLabs Error] Request failed ({e}). Using mock synthesis.")

        return self._generate_fallback_audio_and_alignment(text)

    def _convert_alignment_to_word_timestamps(
        self,
        characters: List[str],
        starts: List[float],
        ends: List[float]
    ) -> List[TimedCaption]:
        """
        Aggregates character-level timestamps into word-level timestamps.
        """
        words: List[TimedCaption] = []
        current_word = ""
        word_start = None

        for i, char in enumerate(characters):
            if word_start is None and char.strip():
                word_start = starts[i]
            
            if char.strip():
                current_word += char
            
            if (char.isspace() or i == len(characters) - 1) and current_word:
                word_end = ends[i]
                words.append(TimedCaption(word=current_word, start=round(word_start, 2), end=round(word_end, 2)))
                current_word = ""
                word_start = None

        return words

    def _generate_fallback_audio_and_alignment(self, text: str) -> Tuple[bytes, List[TimedCaption]]:
        """
        Mock fallback generator for development & testing without live ElevenLabs credits.
        """
        # Minimal valid silent/sine wave MP3 header mock bytes
        mock_mp3_bytes = b"\xFF\xF3\x44\xC4\x00\x00\x00\x03\x48\x00\x00\x00\x00" * 200
        
        words_list = text.split()
        captions: List[TimedCaption] = []
        current_time = 0.0
        duration_per_word = 0.35

        for word in words_list:
            clean_word = word.strip(",.?!")
            start = round(current_time, 2)
            end = round(current_time + duration_per_word, 2)
            captions.append(TimedCaption(word=clean_word, start=start, end=end))
            current_time += duration_per_word + 0.05

        return mock_mp3_bytes, captions


elevenlabs_service = ElevenLabsService()
