# app.py - Enhanced Government Agriculture News Aggregator with Kerala Focus
import os
import sys
import json
import time
import feedparser
import requests
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, jsonify, render_template, send_from_directory
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

class EnhancedAgriNewsAggregator:
    def __init__(self):
        # Enhanced feeds with Kerala-specific sources
        self.feeds = [
            # Kerala-specific government sources
            {
                "name": "Kerala Agriculture Department",
                "url": "https://kerala.gov.in/rss/agriculture",
                "type": "kerala-government",
                "priority": 10
            },
            {
                "name": "Mathrubhumi Agriculture Kerala",
                "url": "https://feed.mathrubhumi.com/agriculture-1.7424971",
                "type": "kerala-news",
                "priority": 9
            },
            {
                "name": "Kerala Kisan Portal",
                "url": "https://www.keralakisan.gov.in/rss.xml",
                "type": "kerala-government",
                "priority": 9
            },
            {
                "name": "Manorama Online Agriculture",
                "url": "https://www.manoramaonline.com/agriculture/rss.xml",
                "type": "kerala-news",
                "priority": 8
            },
            # National government sources
            {
                "name": "PIB Agriculture News",
                "url": "https://www.pib.gov.in/rss/lrel.xml",
                "type": "national-government",
                "priority": 7
            },
            {
                "name": "Rural Voice Kerala Focus",
                "url": "https://eng.ruralvoice.in/rss/latest-posts",
                "type": "kerala-focus",
                "priority": 8
            },
            {
                "name": "Krishi Jagran Kerala",
                "url": "https://krishijagran.com/rss/agriculture/",
                "type": "kerala-agriculture",
                "priority": 7
            },
            {
                "name": "Agriculture Today Kerala",
                "url": "https://www.agriculturetoday.in/rss.xml",
                "type": "agriculture-news",
                "priority": 6
            },
            {
                "name": "Apni Kheti Government Focus",
                "url": "https://blog.apnikheti.com/feed",
                "type": "government-focus",
                "priority": 6
            },
            # Additional Kerala sources
            {
                "name": "Kerala Farmers Portal",
                "url": "https://farmer.kerala.gov.in/rss/latest-news",
                "type": "kerala-farmers",
                "priority": 9
            }
        ]
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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

    def generate_enhanced_summary(self, title, description, source_type):
        """Generate enhanced AI summary with Kerala focus."""
        if not model:
            return "🤖 AI service not available"
        
        try:
            clean_title = self.clean_html(title) if title else ""
            clean_description = self.clean_html(description) if description else ""
            
            if not clean_title and not clean_description:
                return "❌ No content available for summary"
            
            content = f"Title: {clean_title}\nContent: {clean_description[:800]}"
            
            # Customize prompt based on source type
            if 'kerala' in source_type:
                focus_area = "Kerala farmers and state-specific agricultural schemes"
            else:
                focus_area = "Indian farmers and national agricultural policies"
            
            prompt = f"""
Summarize this agricultural news in 2-3 engaging sentences for social media style content.
Focus on:
- Impact on {focus_area}
- Key benefits or changes
- Practical implications
- Financial support or opportunities

Make it conversational and easy to understand.

Content: {content}

Summary:"""
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
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

    def is_relevant_article(self, title, description, source_type):
        """Enhanced relevance checking with Kerala focus."""
        if 'kerala' in source_type:
            kerala_keywords = [
                'kerala', 'malayalam', 'kochi', 'thiruvananthapuram', 'kozhikode', 'kannur',
                'alappuzha', 'kollam', 'palakkad', 'thrissur', 'ernakulam', 'wayanad',
                'kasargod', 'pathanamthitta', 'idukki', 'malappuram'
            ]
            text = f"{title} {description}".lower()
            if any(keyword in text for keyword in kerala_keywords):
                return True
        
        # General agriculture keywords
        agri_keywords = [
            'farmer', 'agriculture', 'crop', 'farming', 'kisan', 'subsidy', 'scheme',
            'policy', 'government', 'ministry', 'budget', 'loan', 'irrigation',
            'fertilizer', 'seed', 'harvest', 'production', 'rural', 'village'
        ]
        
        text = f"{title} {description}".lower()
        return any(keyword in text for keyword in agri_keywords)

    def calculate_enhanced_score(self, title, description, source_info):
        """Enhanced scoring system with Kerala priority."""
        score = source_info.get('priority', 5)
        text = f"{title} {description}".lower()
        
        # Kerala-specific bonus
        kerala_keywords = ['kerala', 'malayalam', 'kochi', 'thiruvananthapuram']
        for keyword in kerala_keywords:
            if keyword in text:
                score += 15
        
        # High priority keywords
        high_priority = [
            'pradhan mantri', 'pm kisan', 'ministry of agriculture', 'government scheme',
            'budget allocation', 'cabinet approval', 'crop insurance', 'msp',
            'kerala farmers', 'state government', 'chief minister'
        ]
        for keyword in high_priority:
            if keyword in text:
                score += 10
        
        # Medium priority keywords
        medium_priority = [
            'farmer', 'agriculture', 'subsidy', 'policy', 'scheme', 'government',
            'fund', 'rural', 'village', 'irrigation', 'fertilizer'
        ]
        for keyword in medium_priority:
            if keyword in text:
                score += 3
        
        # Recent date bonus
        current_year = str(datetime.now().year)
        if 'today' in text or current_year in text or '2025' in text:
            score += 5
            
        return score

    def fetch_enhanced_articles(self, max_articles=15):
        """Fetch articles with enhanced Kerala focus."""
        print("🌴 Starting Enhanced Kerala Agriculture News Aggregation...")
        
        all_articles = []
        processed_urls = set()
        
        # Sort feeds by priority (Kerala sources first)
        sorted_feeds = sorted(self.feeds, key=lambda x: x.get('priority', 0), reverse=True)
        
        for feed_info in sorted_feeds:
            feed_name = feed_info["name"]
            feed_url = feed_info["url"]
            feed_type = feed_info["type"]
            
            try:
                print(f"📡 Fetching: {feed_name} (Priority: {feed_info.get('priority', 0)})")
                
                response = requests.get(feed_url, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                feed = feedparser.parse(response.content)
                
                if not feed.entries:
                    print(f"⚠️ No entries found in {feed_name}")
                    continue
                
                articles_from_this_feed = 0
                for entry in feed.entries[:10]:  # Limit per feed
                    article_url = entry.get('link', '')
                    
                    if not article_url or article_url in processed_urls:
                        continue
                    
                    processed_urls.add(article_url)
                    
                    title = entry.get('title', 'No Title')
                    description = entry.get('summary', entry.get('description', ''))
                    
                    # Enhanced relevance check
                    if self.is_relevant_article(title, description, feed_type):
                        article_data = {
                            "title": title,
                            "url": article_url,
                            "description": self.clean_html(description)[:400],
                            "date": self.format_date(entry.get('published_parsed')),
                            "source": feed_name,
                            "source_type": feed_type,
                            "published_time": entry.get('published', ''),
                            "score": self.calculate_enhanced_score(title, description, feed_info),
                            "is_kerala_focused": 'kerala' in feed_type,
                            "category": self.get_article_category(title, description)
                        }
                        
                        all_articles.append(article_data)
                        articles_from_this_feed += 1
                        
                print(f"✅ Found {articles_from_this_feed} relevant articles from {feed_name}")
                
            except Exception as e:
                print(f"❌ Error fetching {feed_name}: {e}")
            
            time.sleep(0.5)  # Respectful delay
        
        if not all_articles:
            print("⚠️ No articles found from any source!")
            return self.get_empty_response()
        
        # Sort by score and take top articles
        all_articles.sort(key=lambda x: x['score'], reverse=True)
        top_articles = all_articles[:max_articles]
        
        print(f"\n🔥 Selected top {len(top_articles)} articles for AI summarization...")
        
        # Generate enhanced AI summaries
        for i, article in enumerate(top_articles, 1):
            print(f"🤖 Generating summary {i}/{len(top_articles)}: {article['title'][:50]}...")
            
            ai_summary = self.generate_enhanced_summary(
                article['title'], 
                article['description'],
                article['source_type']
            )
            
            article['ai_summary'] = ai_summary
            article['id'] = i
            article['reel_id'] = f"reel_{int(time.time())}_{i}"
            
            # Clean up internal data
            article.pop('score', None)
            
            time.sleep(1.5)  # API stability
        
        return {
            "articles": top_articles,
            "total_articles": len(top_articles),
            "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
            "sources_checked": len(self.feeds),
            "total_found": len(all_articles),
            "kerala_articles": len([a for a in top_articles if a.get('is_kerala_focused')])
        }

    def get_article_category(self, title, description):
        """Categorize articles for better organization."""
        text = f"{title} {description}".lower()
        
        if any(word in text for word in ['scheme', 'subsidy', 'government', 'policy']):
            return "Government Schemes"
        elif any(word in text for word in ['price', 'market', 'selling', 'procurement']):
            return "Market & Prices"
        elif any(word in text for word in ['technology', 'innovation', 'modern', 'digital']):
            return "Technology"
        elif any(word in text for word in ['weather', 'climate', 'rain', 'monsoon']):
            return "Weather & Climate"
        else:
            return "General News"

    def get_empty_response(self):
        """Return empty response structure."""
        return {
            "articles": [],
            "total_articles": 0,
            "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
            "sources_checked": len(self.feeds),
            "total_found": 0,
            "kerala_articles": 0,
            "error": "No relevant articles found"
        }

    def save_to_json(self, data, filename="enhanced_agri_news.json"):
        """Save data to JSON file."""
        os.makedirs('static/data', exist_ok=True)
        filepath = f'static/data/{filename}'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Data saved to {filepath}")

# Create directories
os.makedirs('static/data', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Initialize aggregator
aggregator = EnhancedAgriNewsAggregator()

# Flask Routes
@app.route('/')
def index():
    """Enhanced home page route."""
    return render_template('enhanced_agri_reels.html')

@app.route('/api/fetch-reels')
def fetch_reels():
    """API endpoint to fetch enhanced reels."""
    try:
        print("🔄 Starting enhanced fetch request...")
        data = aggregator.fetch_enhanced_articles(max_articles=12)
        aggregator.save_to_json(data)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        print(f"❌ API fetch error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/articles')
def get_articles():
    """API endpoint to get saved articles."""
    try:
        filepath = 'static/data/enhanced_agri_news.json'
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify(aggregator.get_empty_response()), 404
    except Exception as e:
        return jsonify({"error": f"Error loading articles: {str(e)}"}), 500

@app.route('/api/save-reel', methods=['POST'])
def save_reel():
    """API endpoint to save a reel."""
    try:
        from flask import request
        reel_data = request.json
        
        # Load existing saved reels
        try:
            with open('static/data/saved_reels.json', 'r', encoding='utf-8') as f:
                saved_reels = json.load(f)
        except FileNotFoundError:
            saved_reels = {"reels": []}
        
        # Add timestamp and save
        reel_data['saved_at'] = datetime.now(timezone.utc).isoformat()
        saved_reels["reels"].append(reel_data)
        
        # Keep only last 50 saved reels
        saved_reels["reels"] = saved_reels["reels"][-50:]
        
        with open('static/data/saved_reels.json', 'w', encoding='utf-8') as f:
            json.dump(saved_reels, f, indent=2, ensure_ascii=False)
        
        return jsonify({"status": "success", "message": "Reel saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/saved-reels')
def get_saved_reels():
    """API endpoint to get saved reels."""
    try:
        with open('static/data/saved_reels.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"reels": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

# Main execution
if __name__ == '__main__':
    print("🌴 Starting Enhanced Kerala Agriculture News Service...")
    print(f"🔑 API Key configured: {bool(os.getenv('GEMINI_API_KEY'))}")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--fetch':
        print("📰 Fetching enhanced Kerala agriculture articles...")
        data = aggregator.fetch_enhanced_articles()
        aggregator.save_to_json(data)
        
        print(f"\n🏆 TOP {len(data['articles'])} KERALA AGRICULTURE NEWS")
        print("=" * 60)
        
        for article in data['articles']:
            kerala_flag = "🌴" if article.get('is_kerala_focused') else "🇮🇳"
            print(f"\n{article['id']}. {kerala_flag} {article['title']}")
            print(f"   📰 Source: {article['source']}")
            print(f"   🏷️ Category: {article['category']}")
            print(f"   🤖 Summary: {article['ai_summary']}")
            print("-" * 40)
    else:
        print("🌐 Starting enhanced web server...")
        print("   Visit: http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
