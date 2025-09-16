# test_gemini.py
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def test_gemini_simple():
    # Check if API key exists
    api_key = os.getenv('GEMINI_API_KEY')
    print(f"1. API Key found: {'✅ Yes' if api_key else '❌ No'}")
    
    if api_key:
        print(f"2. API Key preview: {api_key[:10]}...{api_key[-5:]}")
    else:
        print("❌ Please add GEMINI_API_KEY to your .env file")
        return
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        print("3. Gemini configured: ✅ Success")
        
        # Create model
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("4. Model created: ✅ Success")
        
        # Test simple request
        print("5. Testing simple request...")
        response = model.generate_content("Hello, can you say 'API working'?")
        
        if response.text:
            print(f"6. Simple test: ✅ Success - {response.text.strip()}")
        else:
            print("6. Simple test: ❌ Empty response")
            return
        
        # Test agriculture summary
        print("7. Testing agriculture summary...")
        test_content = """
        Title: Kerala Farmers Receive Government Support
        Content: The Kerala government announced new subsidies for farmers to help with crop production and modernization of farming techniques.
        """
        
        prompt = f"Please summarize this agricultural news in 2 sentences: {test_content}"
        response = model.generate_content(prompt)
        
        if response.text:
            print(f"8. Agriculture test: ✅ Success")
            print(f"   Summary: {response.text.strip()}")
        else:
            print("8. Agriculture test: ❌ Empty response")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_gemini_simple()
