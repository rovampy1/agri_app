# gov_agri_news.py
import os
import json
import time
import feedparser
import requests
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, jsonify, render_template
from flask_cors import CORS

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Gemini AI
try:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini AI configured successfully")
except Exception as e:
    print(f"❌ Error configuring Gemini AI: {e}")
    model = None

class GovernmentAgriNewsAggregator:
    def __init__(self):
        # Government and official RSS feeds for agriculture
        self.feeds = [
            {
                "name": "PIB Agriculture News",
                "url": "https://www.pib.gov.in/rss/lrel.xml",
                "type": "government"
            },
            {
                "name": "Rural Voice - Government Schemes",
                "url": "https://eng.ruralvoice.in/rss/latest-posts",
                "type": "government"
            },
            {
                "name": "Agricultural Marketing Division",
                "url": "https://agmarknet.gov.in/rss/PriceAndArrivals.xml",
                "type": "government"
            },
            {
                "name": "Krishi Jagran",
                "url": "https://krishijagran.com/rss/agriculture/",
                "type": "agriculture-news"
            },
            {
                "name": "Agriculture Today",
                "url": "https://www.agriculturetoday.in/rss.xml",
                "type": "agriculture-news"
            },
            {
                "name": "Apni Kheti - Government Focus",
                "url": "https://blog.apnikheti.com/feed",
                "type": "government-focus"
            }
        ]
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def clean_html(self, raw_html):
        """Remove HTML tags and clean text."""
        if not raw_html:
            return ""
        cleanr = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext.strip()

    def format_date(self, parsed_date):
        """Convert parsed date to ISO format."""
        if parsed_date:
            try:
                dt = datetime(*parsed_date[:6])
                return dt.replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                return None
        return None

    def generate_government_summary(self, title, description):
        """Generate AI summary focusing on government schemes and policies."""
        if not model:
            return "🤖 AI service not available"
        
        try:
            clean_title = self.clean_html(title) if title else ""
            clean_description = self.clean_html(description) if description else ""
            
            if not clean_title and not clean_description:
                return "❌ No content available for summary"
            
            content = f"Title: {clean_title}\nContent: {clean_description[:800]}"
            
            prompt = f"""
Summarize this Indian government agricultural news/policy in 2-3 concise sentences. 
Focus on:
- Key government schemes or policies mentioned
- Benefits for farmers
- Implementation details or deadlines
- Financial support or subsidies

Content: {content}

Government Agriculture Summary:"""
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=150,
                    top_p=0.8
                )
            )
            
            if response.text:
                return response.text.strip()
            else:
                return "🤖 Unable to generate summary"
                
        except Exception as e:
            print(f"❌ Summary generation error: {e}")
            return f"🤖 Summary error: {str(e)[:100]}"

    def is_government_relevant(self, title, description):
        """Check if article is government/policy relevant."""
        govt_keywords = [
            'government', 'ministry', 'scheme', 'policy', 'cabinet', 'pm ', 'pradhan mantri',
            'central government', 'state government', 'budget', 'subsidy', 'fund', 'allocation',
            'launch', 'announcement', 'approved', 'sanction', 'pib', 'press information bureau'
        ]
        
        text = f"{title} {description}".lower()
        return any(keyword in text for keyword in govt_keywords)

    def fetch_top_10_articles(self):
        """Fetch exactly 10 most relevant government agriculture articles."""
        print("🏛️ Starting Government Agriculture News Aggregation...")
        
        all_articles = []
        processed_urls = set()
        
        for feed_info in self.feeds:
            feed_name = feed_info["name"]
            feed_url = feed_info["url"]
            
            try:
                print(f"📡 Fetching: {feed_name}")
                
                response = requests.get(feed_url, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries[:15]:  # Get more to filter later
                    article_url = entry.get('link', '')
                    
                    if not article_url or article_url in processed_urls:
                        continue
                    
                    processed_urls.add(article_url)
                    
                    title = entry.get('title', 'No Title')
                    description = entry.get('summary', entry.get('description', ''))
                    
                    # Filter for government relevance
                    if self.is_government_relevant(title, description):
                        article_data = {
                            "title": title,
                            "url": article_url,
                            "description": self.clean_html(description)[:400],
                            "date": self.format_date(entry.get('published_parsed')),
                            "source": feed_name,
                            "published_time": entry.get('published', ''),
                            "score": self.calculate_relevance_score(title, description)
                        }
                        
                        all_articles.append(article_data)
                        
                print(f"✅ Found {len([a for a in all_articles if a['source'] == feed_name])} relevant articles")
                
            except Exception as e:
                print(f"❌ Error fetching {feed_name}: {e}")
            
            time.sleep(1)  # Respectful delay
        
        # Sort by relevance and recency, take top 10
        all_articles.sort(key=lambda x: (x['score'], x['date'] or ''), reverse=True)
        top_10 = all_articles[:10]
        
        print(f"\n🔥 Selected top 10 articles for AI summarization...")
        
        # Generate AI summaries for top 10
        for i, article in enumerate(top_10, 1):
            print(f"🤖 Generating summary {i}/10: {article['title'][:50]}...")
            
            ai_summary = self.generate_government_summary(
                article['title'], 
                article['description']
            )
            
            article['ai_summary'] = ai_summary
            article['id'] = i
            
            # Longer delay for API stability
            time.sleep(2)
        
        return {
            "articles": top_10,
            "total_articles": 10,
            "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
            "sources_checked": len(self.feeds),
            "total_found": len(all_articles)
        }

    def calculate_relevance_score(self, title, description):
        """Calculate relevance score for government agriculture news."""
        score = 0
        text = f"{title} {description}".lower()
        
        # High priority keywords
        high_priority = ['pradhan mantri', 'pm kisan', 'ministry of agriculture', 'government scheme', 'budget allocation', 'cabinet approval']
        for keyword in high_priority:
            if keyword in text:
                score += 10
        
        # Medium priority keywords
        medium_priority = ['farmer', 'agriculture', 'subsidy', 'policy', 'scheme', 'government', 'fund']
        for keyword in medium_priority:
            if keyword in text:
                score += 5
        
        # Recent date bonus
        if 'today' in text or '2025' in text:
            score += 3
            
        return score

    def save_to_json(self, data, filename="government_agri_news.json"):
        """Save data to JSON file."""
        os.makedirs('static/data', exist_ok=True)
        with open(f'static/data/{filename}', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Data saved to static/data/{filename}")

# Create directories
os.makedirs('static/data', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Initialize aggregator
aggregator = GovernmentAgriNewsAggregator()

@app.route('/')
def index():
    return render_template('gov_agri_news.html')

@app.route('/api/fetch-top-10')
def fetch_top_10():
    """API endpoint to fetch top 10 government agriculture articles."""
    try:
        data = aggregator.fetch_top_10_articles()
        aggregator.save_to_json(data)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/articles')
def get_articles():
    """API endpoint to get saved articles."""
    try:
        with open('static/data/government_agri_news.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "No articles found. Please fetch articles first."}), 404

if __name__ == '__main__':
    print("🏛️ Starting Government Agriculture News Service...")
    print(f"🔑 API Key configured: {bool(os.getenv('GEMINI_API_KEY'))}")
    
    # Option to run directly without Flask
    if len(os.sys.argv) > 1 and os.sys.argv[1] == '--fetch':
        print("📰 Fetching top 10 articles directly...")
        data = aggregator.fetch_top_10_articles()
        aggregator.save_to_json(data)
        
        print(f"\n🏆 TOP 10 GOVERNMENT AGRICULTURE NEWS")
        print("=" * 60)
        
        for article in data['articles']:
            print(f"\n{article['id']}. {article['title']}")
            print(f"   Source: {article['source']}")
            print(f"   Summary: {article['ai_summary']}")
            print(f"   URL: {article['url']}")
            print("-" * 40)
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)
