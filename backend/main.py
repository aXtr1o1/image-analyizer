from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image
import shutil

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

app = FastAPI(title="Construction Safety Analysis API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
TEMP_FOLDER = Path("temp_images")
TEMP_FOLDER.mkdir(exist_ok=True)

os.environ["OPENAI_API_KEY"] = ""  # Set your API key
VISION_MODEL = "gpt-4o"

SAFETY_HINTS = [
    "no helmet", "no gloves", "no safety vest", "no goggles",
    "improper harness", "exposed rebar", "trip hazard", "damaged cable",
    "blocked fire exit", "working at height without guardrails",
    "unstable ladder", "overloaded scaffold", "no ear protection",
    "improper footwear", "sparks near flammables", "poor housekeeping"
]

SYSTEM_PROMPT = """You are a construction-safety analyst.

Your task is to analyze the provided image and (optionally) a user-supplied keyword or phrase, then output a short, factual safety observation. Follow these rules:

1. Provide a concise, professional observation (1–2 sentences) based solely on what is clearly visible in the image.
2. If multiple safety conditions or issues are visible, combine them briefly while keeping the description compact and neutral.
3. Do not speculate or assume any details that cannot be visually confirmed.
4. If a keyword is provided:
   - Address it **only if it aligns with visible evidence**.
   - If the keyword is **not supported by the image**, clearly but professionally state that the visual evidence does not match the keyword, and provide an accurate observation of what is visible instead.
5. Use neutral, audit-friendly language (avoid blame or judgmental wording).
6. Prioritize visual evidence over the keyword when there is a conflict.
7. Output **plain text only** — no bullet points, no extra fields, no JSON.
"""

PROPOSAL_PROMPT = """From this image, propose up to 5 *likely* construction-safety observations as short keywords (e.g., "no helmet", "damaged cable").
Only include items that seem visually plausible from the image. Return a comma-separated list of short phrases, no explanations.
Here are example safety phrases for inspiration (do not copy blindly): {safety_hints}.
"""

DESCRIPTION_PROMPT = """Use the image and the provided context to write a brief, audit-friendly observation description (1–2 sentences).
Context keyword(s): {keywords}

Write the final description only. Do not include headings or extra commentary.
"""

CHAT_SYSTEM_PROMPT = """You are a construction-safety assistant. You have already analyzed an image and provided a safety observation.
Now the user has follow-up questions about the same image. Answer their questions based on what you can see in the image.
Be helpful, concise, and professional. Reference specific visual details when answering."""

# Initialize LLM
llm = ChatOpenAI(model=VISION_MODEL, temperature=0.2)

# In-memory session storage 
sessions = {}

class SessionData(BaseModel):
    session_id: str
    image_path: str
    image_b64: str
    keywords: List[str]
    description: str
    chat_history: List[dict] = []

class AnalysisResponse(BaseModel):
    session_id: str
    keywords: List[str]
    description: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    chat_history: List[dict]


def image_to_b64(image_path: str) -> str:
    """Convert image file to base64 string"""
    img = Image.open(image_path).convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def vision_messages_from_b64(image_b64: str, user_text: str) -> List[HumanMessage]:
    """Create vision message with image and text"""
    return [
        HumanMessage(content=[
            {"type": "text", "text": user_text},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}"
                }
            },
        ])
    ]


def propose_keywords_from_image(image_b64: str) -> List[str]:
    """Auto-detect safety keywords from image"""
    user_text = PROPOSAL_PROMPT.format(safety_hints=", ".join(SAFETY_HINTS))
    msgs = [
        SystemMessage(content="You propose concise safety keywords."),
        *vision_messages_from_b64(image_b64, user_text)
    ]
    resp = llm.invoke(msgs)
    raw = resp.content.strip()
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:5] if out else []


def generate_description(image_b64: str, keywords: List[str]) -> str:
    """Generate detailed description based on image and keywords"""
    kw_text = ", ".join(keywords) if keywords else "none"
    user_text = DESCRIPTION_PROMPT.format(keywords=kw_text)
    msgs = [
        SystemMessage(content=SYSTEM_PROMPT),
        *vision_messages_from_b64(image_b64, user_text)
    ]
    resp = llm.invoke(msgs)
    return resp.content.strip()


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
    keyword: str = Form(default="")
):
    """
    Upload image and optional keyword for initial analysis
    """
    if image.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPG and PNG images are supported")
    session_id = str(uuid.uuid4())
    file_extension = image.filename.split(".")[-1]
    image_filename = f"{session_id}.{file_extension}"
    image_path = TEMP_FOLDER / image_filename
    
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    image_b64 = image_to_b64(str(image_path))
    if keyword and keyword.strip():
        keywords = [keyword.strip().lower()]
    else:
        keywords = propose_keywords_from_image(image_b64)
    description = generate_description(image_b64, keywords)
    sessions[session_id] = SessionData(
        session_id=session_id,
        image_path=str(image_path),
        image_b64=image_b64,
        keywords=keywords,
        description=description,
        chat_history=[]
    )
    
    return AnalysisResponse(
        session_id=session_id,
        keywords=keywords,
        description=description
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_about_image(request: ChatRequest):
    """
    Chat about the analyzed image
    """
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]
    messages.append(
        HumanMessage(content=f"Initial analysis - Keywords: {', '.join(session.keywords)}. Description: {session.description}")
    )
    for entry in session.chat_history:
        if entry["role"] == "user":
            messages.append(HumanMessage(content=entry["content"]))
        else:
            messages.append(SystemMessage(content=entry["content"]))
    messages.extend(vision_messages_from_b64(session.image_b64, request.message))
    resp = llm.invoke(messages)
    response_text = resp.content.strip()
    session.chat_history.append({"role": "user", "content": request.message})
    session.chat_history.append({"role": "assistant", "content": response_text})
    
    return ChatResponse(
        response=response_text,
        chat_history=session.chat_history
    )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """
    Clean up session and delete temporary image
    """
    if session_id in sessions:
        session = sessions[session_id]
        if os.path.exists(session.image_path):
            os.remove(session.image_path)
        del sessions[session_id]
        return {"message": "Session deleted successfully"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)