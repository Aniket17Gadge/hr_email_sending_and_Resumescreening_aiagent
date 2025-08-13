import streamlit as st
import requests
import uuid
from datetime import datetime
import json

# Configure page
st.set_page_config(
    page_title="AI Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for powerful UI
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    
    .stApp > header {
        background-color: transparent;
    }
    
    .stApp {
        margin-top: -80px;
    }
    
    .chat-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .chat-header h1 {
        color: white;
        margin: 0;
        font-weight: 700;
        font-size: 2.5rem;
    }
    
    .chat-header p {
        color: rgba(255,255,255,0.8);
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    .chat-container {
        background: white;
        border-radius: 15px;
        padding: 1rem;
        box-shadow: 0 2px 20px rgba(0,0,0,0.08);
        border: 1px solid #e1e5e9;
        max-height: 600px;
        overflow-y: auto;
        margin-bottom: 1rem;
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 5px 20px;
        margin: 1rem 0;
        margin-left: 20%;
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
        animation: slideInRight 0.3s ease-out;
    }
    
    .bot-message {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 20px 5px;
        margin: 1rem 0;
        margin-right: 20%;
        box-shadow: 0 3px 10px rgba(240, 147, 251, 0.3);
        animation: slideInLeft 0.3s ease-out;
    }
    
    .system-message {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        color: #8b4513;
        padding: 0.8rem 1.2rem;
        border-radius: 15px;
        margin: 1rem auto;
        text-align: center;
        font-weight: 500;
        max-width: 300px;
        box-shadow: 0 2px 8px rgba(252, 182, 159, 0.3);
    }
    
    .session-info {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
        font-weight: 600;
        color: #2c3e50;
        box-shadow: 0 2px 10px rgba(168, 237, 234, 0.3);
    }
    
    .new-chat-btn {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 154, 158, 0.4);
        margin-bottom: 1rem;
    }
    
    .new-chat-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 154, 158, 0.6);
    }
    
    .input-container {
        background: white;
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 2px 15px rgba(0,0,0,0.1);
        border: 1px solid #e1e5e9;
    }
    
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(50px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-50px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    .stTextInput input {
        border-radius: 20px;
        border: 2px solid #e1e5e9;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
    }
    
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
    }
    
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.5);
    }
    
    .api-status {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        font-size: 0.9rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    
    .status-success {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        color: #0f5132;
    }
    
    .status-error {
        background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
        color: #842029;
    }
    
    .typing-indicator {
        background: #f8f9fa;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 20px 5px;
        margin: 1rem 0;
        margin-right: 20%;
        border: 2px dashed #dee2e6;
        color: #6c757d;
        font-style: italic;
        animation: pulse 1.5s ease-in-out infinite alternate;
    }
    
    @keyframes pulse {
        from { opacity: 0.6; }
        to { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
    
if 'messages' not in st.session_state:
    st.session_state.messages = []
    
if 'api_endpoint' not in st.session_state:
    st.session_state.api_endpoint = 'http://localhost:8000/api/chat/'  # Default Django endpoint

def call_django_api(session_id, message, api_endpoint):
    """
    Call your Django API endpoint
    Replace this URL with your actual Django API endpoint
    """
    try:
        payload = {
            "session_id": session_id,
            "message": message
        }
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Make POST request to your Django API
        response = requests.post(
            api_endpoint,
            data=json.dumps(payload),
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json(), True
        else:
            return f"API Error: {response.status_code} - {response.text}", False
            
    except requests.exceptions.ConnectionError:
        return "Connection Error: Could not connect to the API. Please check if your Django server is running.", False
    except requests.exceptions.Timeout:
        return "Timeout Error: The API request timed out.", False
    except Exception as e:
        return f"Error: {str(e)}", False

def create_new_chat():
    """Create a new chat session"""
    st.session_state.session_id = str(uuid.uuid4())[:8]
    st.session_state.messages = []
    st.rerun()

# Header
st.markdown("""
<div class="chat-header">
    <h1>🤖 AI Chatbot</h1>
    <p>Powered by Django API • Intelligent Conversations</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for API configuration
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # API Endpoint Configuration
    api_endpoint = st.text_input(
        "Django API Endpoint",
        value=st.session_state.api_endpoint,
        help="Enter your Django API endpoint URL"
    )
    
    if api_endpoint != st.session_state.api_endpoint:
        st.session_state.api_endpoint = api_endpoint
    
    st.markdown("---")
    st.markdown("### 📊 Session Info")
    st.markdown(f"**Session ID:** `{st.session_state.session_id}`")
    st.markdown(f"**Messages:** {len(st.session_state.messages)}")
    st.markdown(f"**API:** `{st.session_state.api_endpoint}`")

# Main interface
col1, col2 = st.columns([3, 1])

with col2:
    if st.button("🆕 New Chat", help="Start a new conversation"):
        create_new_chat()

with col1:
    st.markdown(f"""
    <div class="session-info">
        💬 Current Session: <strong>{st.session_state.session_id}</strong>
    </div>
    """, unsafe_allow_html=True)

# Chat container
chat_container = st.container()

with chat_container:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    if not st.session_state.messages:
        st.markdown("""
        <div class="system-message">
            👋 Welcome! Start a conversation below
        </div>
        """, unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="user-message">
                <strong>You:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        elif message["role"] == "assistant":
            st.markdown(f"""
            <div class="bot-message">
                <strong>AI:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        elif message["role"] == "system":
            st.markdown(f"""
            <div class="system-message">
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Input section
st.markdown('<div class="input-container">', unsafe_allow_html=True)

# Create input form
with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.text_input(
            "Message",
            placeholder="Type your message here...",
            label_visibility="collapsed",
            key="user_message_input"
        )
    
    with col2:
        send_button = st.form_submit_button("Send 🚀")

st.markdown('</div>', unsafe_allow_html=True)

# Handle message sending
if send_button and user_input.strip():
    # Add user message to chat
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    
    # Show typing indicator
    with st.spinner("🤖 AI is thinking..."):
        # Call Django API
        api_response, success = call_django_api(
            st.session_state.session_id,
            user_input,
            st.session_state.api_endpoint
        )
    
    if success:
        # Extract response from API (adjust based on your API response format)
        if isinstance(api_response, dict):
            if 'response' in api_response:
                bot_response = api_response['response']
            elif 'message' in api_response:
                bot_response = api_response['message']
            elif 'reply' in api_response:
                bot_response = api_response['reply']
            else:
                bot_response = str(api_response)
        else:
            bot_response = str(api_response)
        
        # Add API response to chat
        st.session_state.messages.append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # Show success status
        st.markdown("""
        <div class="api-status status-success">
            ✅ Message sent successfully!
        </div>
        """, unsafe_allow_html=True)
        
    else:
        # Add error message to chat
        st.session_state.messages.append({
            "role": "system",
            "content": f"❌ {api_response}",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # Show error status
        st.markdown("""
        <div class="api-status status-error">
            ❌ Failed to send message. Check API configuration.
        </div>
        """, unsafe_allow_html=True)
    
    # Rerun to update the chat display
    st.rerun()

# Footer with API information
st.markdown("---")
st.markdown(f"""
### 🔧 API Integration Instructions

**Where to put your Django API endpoint:**
1. In the sidebar configuration panel above
2. Or modify line 87 in the code: `st.session_state.api_endpoint = 'YOUR_API_URL_HERE'`

**Expected API Request Format:**
```json
{{
    "session_id": "002",
    "message": "tell me my name"
}}
```

**Expected API Response Format:**
Your Django API should return JSON with one of these fields:
- `"response"`: "Your bot's response here"
- `"message"`: "Your bot's response here"  
- `"reply"`: "Your bot's response here"

**Current API Endpoint:** `{st.session_state.api_endpoint}`
""")

# Development info
with st.expander("🛠️ Development Notes"):
    st.markdown("""
    **Session Management:**
    - Each "New Chat" generates a unique 8-character session ID
    - Session ID is automatically sent with every message
    - Messages are stored in Streamlit session state
    
    **API Integration:**
    - Configurable Django API endpoint
    - Automatic JSON payload formatting
    - Error handling for connection issues
    - Timeout protection (30 seconds)
    
    **UI Features:**
    - Gradient backgrounds and smooth animations
    - Responsive design
    - Real-time message updates
    - Typing indicators
    - Status notifications
    """)