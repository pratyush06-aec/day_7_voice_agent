# backend/test_murf_synth.py
import os
import asyncio
from dotenv import load_dotenv
import aiohttp
from livekit.plugins import murf

load_dotenv(".env.local")   # make sure this path is correct

async def main():
    api_key = os.getenv("MURF_API_KEY")
    if not api_key:
        print("MURF_API_KEY not set. Check .env.local and the shell environment.")
        return

    # create your own aiohttp session and pass it to the plugin
    async with aiohttp.ClientSession() as http_sess:
        tts = murf.TTS(
            api_key=api_key,
            model="FALCON",
            voice="en-US-matthew",
            http_session=http_sess,   # IMPORTANT: provide the session
        )

        text = "Hello — this is a Murf TTS test from the local script."
        print("Calling synthesize() ...")

        # synthesize returns an async iterable (stream). DO NOT await it.
        stream = tts.synthesize(text)

        out_path = "murf_test.wav"
        try:
            with open(out_path, "wb") as f:
                async for chunk in stream:
                    # chunk may be bytes-like
                    f.write(chunk)
            print("Saved", out_path)
        except Exception as e:
            print("Error while streaming synth output:", type(e), e)

        # cleanup
        await tts.aclose()

if __name__ == "__main__":
    asyncio.run(main())
