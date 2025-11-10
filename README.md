Django REST API for automated analysis of AI-human conversations with quality metrics and insights.
Features

12+ analysis metrics (clarity, relevance, sentiment, empathy, resolution, etc.)
Automated daily analysis via cron/Celery
REST API with filtering and reporting
Admin dashboard for management
SQLite/PostgreSQL support

Quick Start
bash# Setup
git clone <repo-url>
cd post-conversation-analysis
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Initialize
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
Visit: http://localhost:8000/api/
API Usage
Create Conversation:
bashcurl -X POST http://localhost:8000/api/conversations/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Support Chat",
    "messages": [
      {"sender": "user", "message": "I need help with my order"},
      {"sender": "ai", "message": "Sure! Please share your order ID"}
    ]
  }'
Analyze:
bashcurl -X POST http://localhost:8000/api/conversations/1/analyze/
Get Reports:
bashcurl http://localhost:8000/api/reports/
