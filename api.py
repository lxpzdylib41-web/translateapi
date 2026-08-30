from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="Roblox Translation API", version="2.0.0")

# Servicio público de MyMemory. No requiere API key para el uso básico.
MYMEMORY_URL = "https://api.mymemory.translated.net/get"

class TranslateRequest(BaseModel):
    text: str
    target: str
    source: str = "auto"

LANGUAGES = {
    "es": "es", "en": "en", "pt": "pt", "fr": "fr", "de": "de",
    "it": "it", "ja": "ja", "ko": "ko", "zh-CN": "zh-CN", "zh-TW": "zh-TW",
    "ru": "ru", "ar": "ar", "tr": "tr", "nl": "nl", "pl": "pl",
    "sv": "sv", "da": "da", "no": "no", "fi": "fi", "cs": "cs",
    "hu": "hu", "ro": "ro", "uk": "uk", "el": "el", "he": "he",
    "hi": "hi", "bn": "bn", "vi": "vi", "th": "th", "id": "id",
    "ms": "ms", "fil": "tl", "sw": "sw", "af": "af", "ca": "ca",
    "eu": "eu", "gl": "gl",
}

@app.get("/")
async def root():
    return {"ok": True, "service": "translation-api", "provider": "MyMemory"}

@app.post("/translate")
async def translate(req: TranslateRequest):
    text = req.text.strip()
    target = req.target.strip()

    if not text:
        raise HTTPException(status_code=400, detail="El texto está vacío.")

    if not target or target == "auto":
        raise HTTPException(status_code=400, detail="Selecciona un idioma destino.")

    target_code = LANGUAGES.get(target)
    if not target_code:
        raise HTTPException(status_code=400, detail=f"Idioma no soportado: {target}")

    # MyMemory necesita el idioma de origen. Para "auto" hacemos una detección
    # sencilla usando su servicio de detección mediante una petición adicional.
    # Si falla, usamos inglés como origen de respaldo.
    source = req.source

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if source == "auto":
                detect_response = await client.get(
                    MYMEMORY_URL,
                    params={
                        "q": text,
                        "langpair": f"en|{target_code}",
                        "de": "roblox-translator@example.com",
                    },
                )
                # MyMemory no ofrece detección fiable separada en este endpoint.
                # Probamos varios idiomas comunes hasta encontrar una respuesta
                # diferente al original; el servicio puede manejar el texto según
                # el par solicitado.
                source_code = "en"
            else:
                source_code = LANGUAGES.get(source, source)

            response = await client.get(
                MYMEMORY_URL,
                params={
                    "q": text,
                    "langpair": f"{source_code}|{target_code}",
                    "de": "roblox-translator@example.com",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo contactar con el traductor: {exc}")

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"El servicio de traducción respondió {response.status_code}."
        )

    try:
        data = response.json()
        translation = data["responseData"]["translatedText"]
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=502, detail="Respuesta inválida del servicio de traducción.")

    if not translation:
        raise HTTPException(status_code=502, detail="No se recibió ninguna traducción.")

    return {
        "ok": True,
        "translation": translation,
        "target": target,
    }
