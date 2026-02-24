import streamlit as st
import requests
import json

# Page configuration
st.set_page_config(
    page_title="AI Ticketing System",
    page_icon="🎫",
    layout="centered"
)

# Custom CSS for premium look
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .ticket-card {
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# App header
st.title("🎫 AI Ticketing System")
st.markdown("---")

# Sidebar information
with st.sidebar:
    st.header("About")
    st.info("""
    This system uses AI to intelligently route your queries to the correct department.
    
    **Supported Departments:**
    - 💻 IT Support
    - 💰 Finance
    - 📚 Library
    - 🚌 Transport
    - 🎓 Academics
    """)
    
    st.markdown("---")
    st.markdown("### Examples")
    if st.button("Password Reset"):
        st.session_state.query_input = "I forgot my login password"
    if st.button("Course Enrollment"):
        st.session_state.query_input = "When does course registration start?"
    if st.button("Bus Pass Query"):
        st.session_state.query_input = "How do I get a new bus pass?"

# Query input
st.subheader("How can we help you today?")
query = st.text_area("Describe your issue in detail:", key="query_input", height=100)

if st.button("Submit Request"):
    if not query.strip():
        st.warning("Please enter a query first.")
    else:
        # Higher timeout for agentic flows (Embedding + Email + LLM can take time)
        TIMEOUT_SECONDS = 120
        
        with st.spinner("🧠 AI is analyzing your request..."):
            try:
                # Call the FastAPI endpoint
                response = requests.post(
                    "http://localhost:8000/query",
                    json={"query": query},
                    timeout=TIMEOUT_SECONDS
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "success":
                        st.balloons()
                        
                        # Display clean response
                        st.markdown("### 🤖 Response")
                        st.write(data["response"])
                        
                        # Display ticket details
                        st.markdown("---")
                        st.markdown("#### Ticket Status")
                        st.success("✅ A ticket has been created and your request is being processed.")
                        
                    else:
                        st.error(f"Error: {data.get('error', 'Unknown error occurred')}")
                else:
                    st.error(f"Server returned error code: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                st.error(f"⌛ The request timed out (Limit: {TIMEOUT_SECONDS}s). The AI is taking longer than usual to generate a resolution, but your email has likely been sent already!")
            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to the API server. Make sure your FastAPI app is running on http://localhost:8000")
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: grey;'>Built with FastAPI, LangChain, and Streamlit</div>", 
    unsafe_allow_html=True
)
