# 🔍 Findora - AI-Powered Lost & Found Platform

An intelligent lost and found system using computer vision and natural language processing to match lost items with found items.

## 🚀 Features

- 📸 Image-based item reporting
- 🤖 AI-powered matching using vision encoders
- 📍 Location-based search
- 💰 Reward system
- 🎯 High-confidence matching (≥80%)

## 🛠️ Tech Stack

**Backend:**
- Python (FastAPI)
- SQLite
- TensorFlow/PyTorch
- Computer Vision Models

**Frontend:**
- React.js
- Tailwind CSS
- Lucide Icons

## 📦 Installation

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## 🎯 How It Works

1. Users upload images of lost/found items
2. AI extracts visual features using vision encoders
3. NLP processes text descriptions
4. Smart matching algorithm finds potential matches
5. Users get notified of high-confidence matches

## 📄 License

MIT License

## 👨‍💻 Author

Deepak Roshan