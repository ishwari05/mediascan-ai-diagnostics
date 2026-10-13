# 🏥 MediScan AI
## AI-Based Multimodal System for Early Disease Detection

![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![License](https://img.shields.io/badge/License-Academic-green)
![Status](https://img.shields.io/badge/Status-Production--Ready-brightgreen)

MediScan AI is a high-performance, full-stack medical diagnostic platform designed for the early detection of **Anemia** and **Diabetes** using non-invasive imaging. By analyzing images of the Eye (conjunctiva), Palm, and Retina, the system provides clinical-grade screenings powered by Deep Learning.

---

## ✨ Key Features

- 🧠 **Multimodal AI**: Simultaneous analysis of eye, palm, and retina scans.
- 🔍 **GradCAM Visualization**: Heatmaps highlighting precise anatomical regions influencing the AI's decision.
- 📊 **Clinical Dashboard**: Real-time metrics, scan history, and risk assessment (Low/Medium/High).
- 💬 **Intelligent Health Bot**: Integrated healthcare assistant for diagnostic queries.
- 📄 **Automated Reports**: Instant PDF generation for clinical forensic data.
- 🛡️ **Secure Infrastructure**: JWT-based authentication and role-based access control (RBAC).

---

## 🛠️ Technology Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | React.js, Tailwind CSS, Chart.js, Axios |
| **Backend** | Flask (Python), SQLAlchemy, JWT, OpenCV |
| **AI/ML** | PyTorch, MobileNetV2, ResNet50, GradCAM |
| **Database** | SQLite (Development), PostgreSQL (Production) |

---

## 📁 Project Structure

This project follows a modular architecture for scalability. The active code is contained within the `mediascan/` directory.

```bash
SB_Web-master/
├── mediascan/
│   ├── backend/                # 🐍 Flask API Service
│   │   ├── app.py              # Application Entry Point
│   │   ├── models/             # AI Inference Logic
│   │   └── routes/             # Authentication & Prediction endpoints
│   └── frontend/               # ⚛️ React Dashboard
│       └── src/                # UI Components & Application State
└── SB_Project/
    └── codebase/
        └── outputs/
            └── models/         # 🧠 4 Integrated AI Models (Preserved)
                ├── Anemia_eye_mobilenet.pth
                ├── diabetes_eye_resnet50.pth
                ├── diabetes_skin_resnet50.pth
                └── Anemia_skin_resnet50 .pth
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **pip** and **npm**

---

### 2. Backend Installation (Terminal 1)
```bash
# Navigate to backend
cd mediascan/backend

# Create virtual environment
python -m venv venv

# Activate venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Environment Configuration
Create a `.env` file in `mediascan/backend/`:
```env
SECRET_KEY=yoursecretkey_here
JWT_SECRET_KEY=yourjwtkey_here
DATABASE_URL=sqlite:///mediascan.db
```

#### Start Backend
```bash
python app.py
```
*The server will start at http://localhost:5000*

---

### 3. Frontend Installation (Terminal 2)
```bash
# Navigate to frontend
cd mediascan/frontend

# Install node packages
npm install

# Start development server
npm start
```
*The dashboard will open at http://localhost:3000*

---

## 🤖 Integrated AI Models

MediScan AI utilizes four professional-grade models trained on clinical datasets. These are preserved in the repository to ensure immediate functionality:

| Domain | Architecture | Purpose |
|--------|--------------|---------|
| **Eye Scan** | MobileNetV2 | Conjunctival pallor detection for Anemia |
| **Palm Scan** | ResNet50 | Palmar erythema analysis for Anemia |
| **Retina Scan**| ResNet50 | DR Classification (Mild to Severe) |
| **Skin Scan** | ResNet50 | Diabetic Foot Ulcer (DFU) detection |

> [!NOTE]
> The system includes a **Fusion Engine** that combines Eye and Palm confidence scores for a more robust Anemia diagnosis.

---

## 🗄️ Switching to Supabase / PostgreSQL

MediScan AI supports local SQLite (default for offline dev & tests) and production PostgreSQL (hosted on Supabase) via SQLAlchemy and Flask-Migrate without relying on proprietary Supabase SDKs.

### 1. Configure Connection
Create `mediascan/backend/.env` (from `.env.example`) and set your Supabase Transaction Pooler URI:

```bash
# Transaction Pooler (Port 6543) - handles connection pooling and SSL automatically
DATABASE_URL=postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

> [!NOTE]
> If `DATABASE_URL` starts with legacy `postgres://`, the backend automatically rewrites it to `postgresql://`. If `DATABASE_URL` is unset, the app safely defaults to local SQLite (`sqlite:///mediascan.db`).

### 2. Apply Database Migrations
Initialize the database tables on Supabase using Flask-Migrate (Alembic):

```bash
cd mediascan/backend
FLASK_APP=app.py python3 -m flask db upgrade
```

### 3. Migrate Existing SQLite Data (Optional)
If you have local scan records or users in SQLite you wish to copy over:

```bash
# Step A: Dry-run check (verifies connection and prints row counts without modifying DB)
python3 scripts/migrate_sqlite_to_postgres.py

# Step B: Live migration (inserts data preserving primary keys and resets sequence generators)
python3 scripts/migrate_sqlite_to_postgres.py --confirm
```

### 4. Verify Connection
Start the server and check the health endpoint:
```bash
python3 app.py
# Query health endpoint
curl http://localhost:5001/api/health
# Response will include: "db_backend": "postgresql"
```

---

## 🔐 Administrative Access

**Default Admin Credentials:**
- **Email:** `admin@mediascan.ai`
- **Password:** `Admin@123`

---

## ⚖️ Disclaimer & Ethics

> [!WARNING]
> This software is a **clinical screening tool** meant for educational and research support. It does not provide a final medical diagnosis. All AI results must be verified by a certified healthcare professional.

---

**Developed as Final Year Project — 2024–25**  
*MediScan AI — Bridging the gap between AI and Clinical Diagnostics*
