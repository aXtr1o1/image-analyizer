## 📌 Image Analysis

This project analyzes construction images using OpenAI Vision and provides safety observations + interactive chat about the image.

---

## 📂 Project Structure

```
root/
 ├── backend/           # FastAPI backend (Image analysis API)
 ├── frontend/          # Next.js frontend (UI for uploading & chat)
```

---

## 🚀 Requirements

| Component      | Version          |
| -------------- | ---------------- |
| Python         | 3.9+             |
| Node           | 18+              |
| FastAPI        | Latest           |
| Next.js        | 14+ (App Router) |
| OpenAI API Key | Required         |

---

## ⚙️ Environment Variables Required

### **Backend (.env or OS Environment)**

| Variable         | Description                              |
| ---------------- | ---------------------------------------- |
| `OPENAI_API_KEY` | Your OpenAI key with vision model access |

Set it via terminal before running:

```bash
export OPENAI_API_KEY="your_key_here"
```

On Windows (PowerShell):

```powershell
setx OPENAI_API_KEY "your_key_here"
```

---

### **Frontend (`.env.local`)**

Create a file under `frontend/.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> This allows Next.js to call the FastAPI server.

---

## 🖥️ Backend Setup (FastAPI)

### 1️⃣ Create Virtual Environment & Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> If `requirements.txt` is not created yet, run:
>
> ```bash
> pip install fastapi uvicorn python-multipart pillow langchain-openai langchain-core
> ```

### 2️⃣ Run the FastAPI Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### API Endpoints

| Method   | Endpoint            | Description                                 |
| -------- | ------------------- | ------------------------------------------- |
| `POST`   | `/api/analyze`      | Upload image + keyword, get safety analysis |
| `POST`   | `/api/chat`         | Chat about the analyzed image               |
| `DELETE` | `/api/session/{id}` | Clear session & image                       |
| `GET`    | `/health`           | Health check                                |

---

## 🌐 Frontend Setup (Next.js)

### 1️⃣ Install Dependencies

```bash
cd frontend
npm install
```

### 2️⃣ Start Dev Server

```bash
npm run dev
```

> Frontend runs on `http://localhost:3000`

---

## 🔗 CORS Configuration

FastAPI CORS already allows requests from the Next.js dev server:

```python
allow_origins=["http://localhost:3000"]
```

If hosting frontend separately, update this to the deployed URL.

---

## 🧪 Usage Flow

| Step | Action                                                |
| ---- | ----------------------------------------------------- |
| 1    | Run FastAPI on `localhost:8000`                       |
| 2    | Run Next.js on `localhost:3000`                       |
| 3    | Open UI → Upload an image                             |
| 4    | (Optional) Enter keyword to influence safety analysis |
| 5    | View auto-generated safety observations               |
| 6    | Chat with AI about specifics in the image             |

---

## 🧹 Temp File Storage

Uploaded images are saved in `backend/temp_images/` and deleted when session is removed:

```python
TEMP_FOLDER = Path("temp_images")
```


## ✅ Health Check

Test backend:

```bash
curl http://localhost:8000/health
```

Expected Output:

```json
{ "status": "healthy" }
```

