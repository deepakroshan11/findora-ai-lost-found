# 🔍 Findora – AI-Powered Lost & Found Platform

Findora is a full-stack AI-powered lost and found platform that uses
computer vision and intelligent similarity matching to efficiently
connect lost items with found items.

---

## 🚀 Features

- 📸 Image-based item reporting  
- 🤖 CNN-based AI matching engine  
- 📍 Location-aware item search  
- 💰 Optional reward support  
- 🎯 High-confidence match detection (≥80%)

---

## 🛠️ Tech Stack

### Backend
- Python (FastAPI)
- SQLite
- TensorFlow (CNN-based vision encoder)
- Computer Vision (image embeddings & similarity matching)

### Frontend
- React.js
- Tailwind CSS
- Lucide Icons

---

## 🧠 AI / ML Overview

- A CNN-based vision encoder extracts feature embeddings from item images  
- Text descriptions and metadata are combined with image similarity  
- A similarity scoring engine identifies potential matches  
- Matches with confidence ≥80% are flagged as high-confidence results  

 

## 📦 Installation

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

Frontend
cd frontend
npm install
npm start

🔁 How It Works

Users report lost or found items with images and descriptions

AI extracts visual features using a CNN-based encoder

Similarity scores are computed across items

High-confidence matches are identified automatically

Users can view matches with confidence visualization

📄 License

MIT License

👨‍💻 Author

Deepak Roshan
AI / ML • Computer Vision • Full-Stack Development
