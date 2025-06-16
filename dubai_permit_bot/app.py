import streamlit as st
import pymongo
from datetime import datetime, date
import json
import logging
import traceback
import os
from functools import wraps
from typing import Optional, Dict, Any, Union
import sys

# ========================= LOGGING CONFIGURATION =========================

def setup_logging():
    """Configure logging for the application"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Configure logging
        log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        
        # Create logger
        logger = logging.getLogger('dubai_event_app')
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler for all logs
        file_handler = logging.FileHandler('logs/dubai_event_app.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Error file handler for errors only
        error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(log_format))
        
        # Console handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        logger.addHandler(console_handler)
        
        return logger
    except Exception as e:
        # Fallback to basic logging if setup fails
        logging.basicConfig(level=logging.INFO, format=log_format)
        logger = logging.getLogger('dubai_event_app')
        logger.error(f"Failed to setup advanced logging: {e}")
        return logger

# Initialize logger
logger = setup_logging()

# ========================= ERROR HANDLING DECORATORS =========================

def handle_exceptions(func):
    """Decorator to handle exceptions gracefully"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger.debug(f"Executing function: {func.__name__}")
            result = func(*args, **kwargs)
            logger.debug(f"Function {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in function {func.__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Show user-friendly error message
            st.error(f"An error occurred: {str(e)}")
            
            # In debug mode, show more details
            if st.session_state.get('debug_mode', False):
                st.error(f"Debug Info: {traceback.format_exc()}")
            
            return None
    return wrapper

def safe_execute(func, *args, **kwargs):
    """Safe execution wrapper for critical operations"""
    try:
        logger.debug(f"Safe executing: {func.__name__ if hasattr(func, '__name__') else str(func)}")
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Safe execution failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

# ========================= DATABASE CONNECTION =========================

@st.cache_resource
@handle_exceptions
def init_connection():
    """Initialize MongoDB connection with enhanced error handling"""
    try:
        logger.info("Initializing MongoDB connection")
        
        # Get connection string from environment or use default
        connection_string = os.getenv('MONGODB_URI', "mongodb://localhost:27017/")
        logger.debug(f"Using connection string: {connection_string[:20]}...")
        
        # Create client with timeout settings
        client = pymongo.MongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            maxPoolSize=10
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
        
        # Return collection
        db = client["dubai_events"]
        collection = db["event_applications"]
        
        # Log collection info
        logger.info(f"Connected to database: {db.name}")
        logger.info(f"Using collection: {collection.name}")
        
        return collection
        
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB connection timeout: {e}")
        st.error("Database connection timeout. Please check if MongoDB is running.")
        return None
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        st.error("Failed to connect to database. Please check your connection settings.")
        return None
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        st.error(f"Database connection failed: {e}")
        return None

# ========================= SESSION STATE MANAGEMENT =========================

@handle_exceptions
def init_session_state():
    """Initialize session state with error handling"""
    logger.debug("Initializing session state")
    
    default_values = {
        'conversation_step': 'greeting',
        'event_data': {},
        'chat_history': [],
        'show_greeting': True,
        'debug_mode': False,
        'error_count': 0,
        'last_error': None
    }
    
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value
            logger.debug(f"Initialized session state: {key} = {value}")

# ========================= CONSTANTS =========================

TICKETED_EVENT_TYPES = [
    "Exhibition",
    "Conference",
    "Conference + Exhibition", 
    "Product Launch/Forum/Seminar/Summit",
    "Exhibition/Product Launch + Conference/Forum/Seminar/Summit",
    "Award Ceremony",
    "Award Ceremony + Conference",
    "Award Ceremony + Conference + Exhibition",
    "DJ Event",
    "Musical Event",
    "Comedy Show"
]

NON_TICKETED_EVENT_TYPES = [
    "Exhibition",
    "Conference/Forum/Meeting/Summit",
    "Conference + Exhibition",
    "Exhibition/Product Launch + Conference/Forum/Seminar/Summit",
    "Award Ceremony",
    "Award Ceremony + Conference",
    "Award Ceremony + Conference + Exhibition",
    "DJ Event",
    "Musical Event",
    "Comedy Show"
]

DUBAI_VENUES = [
    "Dubai Hotel 1",
    "Dubai Hotel 2",
    "Dubai Convention Center",
    "Emirates Palace",
    "Burj Al Arab",
    "Atlantis The Palm",
    "Other"
]

INDUSTRIES = [
    "IT & Technology",
    "Healthcare",
    "Finance & Banking",
    "Education",
    "Entertainment",
    "Sports",
    "Real Estate",
    "Automotive",
    "Fashion & Beauty",
    "Food & Beverage",
    "Other"
]

# ========================= CHAT FUNCTIONS =========================

@handle_exceptions
def add_to_chat(message: str, is_bot: bool = True):
    """Add message to chat history with error handling"""
    try:
        logger.debug(f"Adding chat message: {'Bot' if is_bot else 'User'} - {message[:50]}...")
        
        chat_entry = {
            'message': str(message),
            'is_bot': bool(is_bot),
            'timestamp': datetime.now()
        }
        
        st.session_state.chat_history.append(chat_entry)
        logger.debug(f"Chat history length: {len(st.session_state.chat_history)}")
        
    except Exception as e:
        logger.error(f"Failed to add chat message: {e}")
        # Don't break the app, just log the error

@handle_exceptions
def display_chat_history():
    """Display chat history with error handling"""
    try:
        logger.debug(f"Displaying {len(st.session_state.chat_history)} chat messages")
        
        for i, chat in enumerate(st.session_state.chat_history):
            try:
                if chat.get('is_bot', True):
                    with st.chat_message("assistant"):
                        st.markdown(chat.get('message', 'Error displaying message'))
                else:
                    with st.chat_message("user"):
                        st.markdown(chat.get('message', 'Error displaying message'))
            except Exception as e:
                logger.error(f"Error displaying chat message {i}: {e}")
                st.error(f"Error displaying message {i}")
                
    except Exception as e:
        logger.error(f"Failed to display chat history: {e}")
        st.error("Error displaying chat history")

# ========================= CALCULATION FUNCTIONS =========================

@handle_exceptions
def calculate_estimated_fees(event_data: Dict[str, Any]) -> int:
    """Calculate estimated government fees with enhanced error handling"""
    try:
        logger.debug(f"Calculating fees for event: {event_data.get('event_name', 'Unknown')}")
        
        # Validate input data
        if not isinstance(event_data, dict):
            raise ValueError("Event data must be a dictionary")
        
        base_fee = 0
        
        # Base fee calculation
        event_classification = event_data.get('event_classification', '')
        if event_classification == 'internal':
            base_fee = 2000
            logger.debug("Applied internal event base fee: 2000 AED")
        elif event_classification == 'external':
            ticketing_type = event_data.get('ticketing_type', '')
            if ticketing_type == 'paid_ticketed':
                base_fee = 8000
                logger.debug("Applied paid ticketed base fee: 8000 AED")
            elif ticketing_type == 'free_ticketed':
                base_fee = 5000
                logger.debug("Applied free ticketed base fee: 5000 AED")
            else:
                base_fee = 3000
                logger.debug("Applied non-ticketed base fee: 3000 AED")
        else:
            logger.warning(f"Unknown event classification: {event_classification}")
            base_fee = 3000  # Default fee
        
        # Additional fees based on participants
        participants = int(event_data.get('no_of_participants', 0))
        participant_fee = 0
        
        if participants > 500:
            participant_fee = 3000
        elif participants > 200:
            participant_fee = 1500
        elif participants > 100:
            participant_fee = 800
        
        logger.debug(f"Participant fee for {participants} participants: {participant_fee} AED")
        
        # Duration-based fees
        days = int(event_data.get('no_of_days', 1))
        duration_fee = max(0, (days - 3) * 500)
        logger.debug(f"Duration fee for {days} days: {duration_fee} AED")
        
        # Performer fees
        performers = int(event_data.get('no_of_performers', 0))
        performer_fee = performers * 200
        logger.debug(f"Performer fee for {performers} performers: {performer_fee} AED")
        
        # Calculate total
        total_fee = base_fee + participant_fee + duration_fee + performer_fee
        
        logger.info(f"Fee calculation completed: {total_fee} AED")
        logger.debug(f"Fee breakdown - Base: {base_fee}, Participants: {participant_fee}, Duration: {duration_fee}, Performers: {performer_fee}")
        
        return total_fee
        
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid data for fee calculation: {e}")
        st.error("Invalid event data for fee calculation")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error in fee calculation: {e}")
        st.error("Error calculating fees")
        return 0

# ========================= DATABASE OPERATIONS =========================

@handle_exceptions
def save_to_mongodb(event_data: Dict[str, Any]) -> Optional[str]:
    """Save event data to MongoDB with comprehensive error handling"""
    try:
        logger.info(f"Saving event data: {event_data.get('event_name', 'Unknown')}")
        
        # Validate event data
        if not event_data:
            raise ValueError("Event data is empty")
        
        # Get collection
        collection = init_connection()
        if collection is None:
            logger.error("No database connection available")
            st.error("Database connection not available")
            return None
        
        # Prepare data for saving
        save_data = event_data.copy()
        save_data['created_at'] = datetime.now()
        save_data['estimated_fee'] = calculate_estimated_fees(event_data)
        save_data['app_version'] = "1.0"
        
        # Validate required fields
        required_fields = ['event_name', 'event_classification']
        for field in required_fields:
            if field not in save_data or not save_data[field]:
                raise ValueError(f"Required field missing: {field}")
        
        # Insert into database
        logger.debug("Inserting data into MongoDB")
        result = collection.insert_one(save_data)
        
        if result.inserted_id:
            logger.info(f"Event saved successfully with ID: {result.inserted_id}")
            return str(result.inserted_id)
        else:
            logger.error("Failed to insert document - no ID returned")
            st.error("Failed to save event data")
            return None
            
    except pymongo.errors.DuplicateKeyError as e:
        logger.error(f"Duplicate event data: {e}")
        st.error("Event with similar details already exists")
        return None
    except pymongo.errors.WriteError as e:
        logger.error(f"Database write error: {e}")
        st.error("Failed to save event data - database error")
        return None
    except ValueError as e:
        logger.error(f"Data validation error: {e}")
        st.error(f"Data validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error saving to database: {e}")
        st.error("Unexpected error while saving event data")
        return None

# ========================= BUTTON HANDLER =========================

@handle_exceptions
def handle_button_clicks() -> bool:
    """Handle all button clicks with comprehensive error handling"""
    try:
        logger.debug("Processing button clicks")
        
        # Track button clicks for debugging
        button_states = {}
        for key in st.session_state:
            if key.endswith('_clicked') and st.session_state.get(key):
                button_states[key] = True
        
        if button_states:
            logger.debug(f"Active button states: {button_states}")
        
        # Greeting buttons
        if st.session_state.get('fee_calc_clicked'):
            logger.info("Fee calculator button clicked")
            add_to_chat("I'd like to calculate government fees for my event", False)
            classification_message = """
            Perfect! I'll guide you through the government fee calculation process.\n
            **Step 1: Event Classification**

            Is your event:\n

            🏢 **INTERNAL** - Company/organizational event for employees only \n
            🌍 **EXTERNAL** - Event with external guests, clients, or public attendance \n

            This determines your permit category and fee structure.
            """
            add_to_chat(classification_message)
            st.session_state.conversation_step = 'event_classification'
            st.session_state.show_greeting = False
            st.session_state.fee_calc_clicked = False
            return True
        
        if st.session_state.get('requirements_clicked'):
            logger.info("Requirements button clicked")
            add_to_chat("I want to check document requirements", False)
            requirements_message = """
            **📋 DOCUMENT REQUIREMENTS CHECKER**
            
            For Dubai event permits, you'll typically need:
            
            **For All Events:**\n
            ✅ Completed application form \n
            ✅ Company trade license copy \n
            ✅ Event concept/description  \n
            ✅ Venue booking confirmation \n
            ✅ Event layout/floor plan    \n
            
            **For External Events:**\n
            ✅ Marketing materials/brochures \n
            ✅ Speaker/performer details \n
            ✅ Security plan (for large events) \n
            ✅ Insurance certificate \n
            
            **For Paid Events:**\n
            ✅ Ticketing system details   \n
            ✅ Revenue projections        \n
            ✅ Payment processing setup   \n
            
            Would you like me to help calculate your fees as well?
            """
            add_to_chat(requirements_message)
            st.session_state.requirements_clicked = False
            return True
        
        if st.session_state.get('specialist_clicked'):
            logger.info("Specialist button clicked")
            add_to_chat("I'd like to speak with a permit specialist", False)
            specialist_message = """
            **📞 SPECIALIST CONSULTATION**
            
            Our permit specialists can help with:
            - Complex event scenarios
            - Multi-venue events
            - International performer permits
            - Expedited processing
            - Compliance reviews
            
            **Contact Information:**
            📧 Email: permits@dubaievents.gov.ae \n
            📱 Phone: +971-4-XXX-XXXX \n
            🕐 Hours: Sunday-Thursday, 8:00 AM - 3:00 PM \n
            
            In the meantime, I can help you get started with fee calculations!
            """
            add_to_chat(specialist_message)
            st.session_state.specialist_clicked = False
            return True
        
        if st.session_state.get('general_clicked'):
            logger.info("General questions button clicked")
            add_to_chat("I have general permit questions", False)
            general_message = """
            **❓ GENERAL PERMIT INFORMATION**
            
            **Common Questions:**
            
            **Q: How long does permit processing take?** \n
            A: 5-15 working days depending on event complexity
            
            **Q: Can I apply for multiple events at once?** \n
            A: Yes, but each event needs a separate application
            
            **Q: What if my event details change?** \n
            A: You must notify authorities within 48 hours of changes
            
            **Q: Are there restrictions on event timing?**\n
            A: Yes, some venues have restrictions during Ramadan and national holidays
            
            For more specific questions, please refer to this [Dubai Events FAQ](https://epermits.det.gov.ae/ePermit/FAQDocumentEN.html) or contact our support team.\n

            Let me help you calculate your specific event fees!
            """
            add_to_chat(general_message)
            st.session_state.general_clicked = False
            return True
        
        # Event classification buttons
        if st.session_state.get('internal_clicked'):
            logger.info("Internal event selected")
            add_to_chat("Internal Event - Company/organizational event for employees only", False)
            internal_message = """
            **INTERNAL EVENT IDENTIFIED** 🏢
            Good news! For internal company events:
            - Your venue handles the permit application
            - Simplified documentation required
            - Lower government fees typically apply
            - Faster processing times
            **What I can help you with:**
            - Calculate estimated fees for budgeting
            - Prepare information for your venue
            - Ensure compliance requirements are met
            Let's proceed with fee calculation! I'll need some basic event details.
            """
            add_to_chat(internal_message)
            st.session_state.event_data['event_classification'] = 'internal'
            st.session_state.conversation_step = 'internal_event_info'
            st.session_state.internal_clicked = False
            return True
        
        if st.session_state.get('external_clicked'):
            logger.info("External event selected")
            add_to_chat("External Event - Event with external guests, clients, or public attendance", False)
            ticketing_message = """
            **EXTERNAL EVENT IDENTIFIED** 🌍
            For external events, I need to understand your ticketing structure: \n
            💰 **PAID TICKETED** - Admission fees, ticket sales, revenue generation \n
            🎫 **FREE TICKETED** - No charge but controlled access with registration/badges  \n
            🆓 **NON-TICKETED** - No charge, no registration, open to public \n
            This classification significantly impacts your permits and fees.
            """
            add_to_chat(ticketing_message)
            st.session_state.event_data['event_classification'] = 'external'
            st.session_state.conversation_step = 'external_ticketing'
            st.session_state.external_clicked = False
            return True
        
        # Internal event button
        if st.session_state.get('calc_internal_clicked'):
            logger.info("Calculate internal event fees clicked")
            add_to_chat("Yes, let's calculate the estimated fees", False)
            st.session_state.conversation_step = 'collect_event_details'
            st.session_state.calc_internal_clicked = False
            return True
        
        # Ticketing buttons
        if st.session_state.get('paid_ticketed_clicked'):
            logger.info("Paid ticketed selected")
            add_to_chat("Paid Ticketed - Admission fees/ticket sales", False)
            st.session_state.event_data['ticketing_type'] = 'paid_ticketed'
            st.session_state.conversation_step = 'collect_event_details'
            st.session_state.paid_ticketed_clicked = False
            return True
        
        if st.session_state.get('free_ticketed_clicked'):
            logger.info("Free ticketed selected")
            add_to_chat("Free Ticketed - Controlled access with registration", False)
            st.session_state.event_data['ticketing_type'] = 'free_ticketed'
            st.session_state.conversation_step = 'collect_event_details'
            st.session_state.free_ticketed_clicked = False
            return True
        
        if st.session_state.get('non_ticketed_clicked'):
            logger.info("Non-ticketed selected")
            add_to_chat("Non-Ticketed - Open access with no registration", False)
            st.session_state.event_data['ticketing_type'] = 'non_ticketed'
            st.session_state.conversation_step = 'collect_event_details'
            st.session_state.non_ticketed_clicked = False
            return True
        
        # Results buttons
        if st.session_state.get('save_app_clicked'):
            logger.info("Save application clicked")
            application_id = save_to_mongodb(st.session_state.event_data)
            if application_id:
                add_to_chat("✅ Application saved successfully! Reference ID: " + str(application_id)[:8], True)
            else:
                add_to_chat("❌ Failed to save application. Please try again.", True)
            st.session_state.save_app_clicked = False
            return True
        
        if st.session_state.get('new_calc_clicked'):
            logger.info("New calculation clicked")
            st.session_state.conversation_step = 'greeting'
            st.session_state.event_data = {}
            st.session_state.show_greeting = True
            add_to_chat("Let's calculate fees for another event!", False)
            st.session_state.new_calc_clicked = False
            return True
        
        if st.session_state.get('summary_clicked'):
            logger.info("Summary clicked")
            try:
                estimated_fee = calculate_estimated_fees(st.session_state.event_data)
                
                # Calculate breakdown components
                base_fee = 2000 if st.session_state.event_data.get('event_classification') == 'internal' else 3000
                participants = st.session_state.event_data.get('no_of_participants', 0)
                participant_fee = 0
                if participants > 500:
                    participant_fee = 3000
                elif participants > 200:
                    participant_fee = 1500
                elif participants > 100:
                    participant_fee = 800
                
                duration_fee = max(0, (st.session_state.event_data.get('no_of_days', 1) - 3) * 500)
                performer_fee = st.session_state.event_data.get('no_of_performers', 0) * 200
                
                breakdown = f"""
                **DETAILED FEE BREAKDOWN** \n
                
                Base Fee: AED {base_fee:,} \n
                Participant Fee: AED {participant_fee:,} \n
                Duration Fee: AED {duration_fee:,} \n
                Performer Fee: AED {performer_fee:,} \n
                
                **Total: AED {estimated_fee:,}**
                """
                add_to_chat(breakdown, True)
            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                add_to_chat("❌ Error generating fee summary. Please try again.", True)
            
            st.session_state.summary_clicked = False
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error in handle_button_clicks: {e}")
        st.error("Error processing button click")
        return False

# ========================= MAIN APPLICATION =========================

@handle_exceptions
def main():
    """Main application function with comprehensive error handling"""
    try:
        logger.info("Starting Dubai Event Permit Assistant")
        
        # Page configuration
        st.set_page_config(
            page_title="Dubai Event Permit Assistant",
            page_icon="🎪",
            layout="wide"
        )
        
        # Custom CSS
        st.markdown("""
        <style>
            .stButton>button {
                width: 100%;
                padding: 0.5rem;
                border-radius: 8px;
                font-weight: bold;
            }
            .stChatMessage {
                padding: 1rem;
                border-radius: 10px;
                margin-bottom: 1rem;
            }
            .stTextInput>div>div>input, .stTextArea>div>div>textarea {
                border-radius: 8px;
            }
            .stSelectbox>div>div>div {
                border-radius: 8px;
            }
            .debug-info {
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Initialize session state
        init_session_state()
        
        # Debug panel in sidebar
        with st.sidebar:
            st.subheader("🔧 Debug Panel")
            
            # Debug mode toggle
            debug_mode = st.checkbox("Enable Debug Mode", value=st.session_state.get('debug_mode', False))
            st.session_state.debug_mode = debug_mode
            
            if debug_mode:
                st.write(f"**Session State Keys:** {len(st.session_state.keys())}")
                st.write(f"**Chat History:** {len(st.session_state.get('chat_history', []))}")
                st.write(f"**Current Step:** {st.session_state.get('conversation_step', 'Unknown')}")
                st.write(f"**Error Count:** {st.session_state.get('error_count', 0)}")
                
                if st.button("Clear Logs"):
                    try:
                        with open('logs/dubai_event_app.log', 'w') as f:
                            f.write('')
                        with open('logs/errors.log', 'w') as f:
                            f.write('')
                        st.success("Logs cleared")
                    except Exception as e:
                        st.error(f"Failed to clear logs: {e}")
                
                # Show recent logs
                if st.button("Show Recent Logs"):
                    try:
                        with open('logs/dubai_event_app.log', 'r') as f:
                            lines = f.readlines()
                            recent_logs = lines[-10:] if len(lines) > 10 else lines
                            st.text_area("Recent Logs", '\n'.join(recent_logs), height=200)
                    except Exception as e:
                        st.error(f"Failed to read logs: {e}")
        
        # Header
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;">
            <h1 style="color: white; margin: 0; font-size: 2.5rem;">🎪 Dubai Event Permit Business Support Assistant</h1>
            <p style="color: white; margin: 0.5rem 0 0 0; font-size: 1.2rem;">Your AI-powered guide for Dubai event permits and fee calculations</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Chat interface
        st.subheader("💬 Chat Assistant")
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            display_chat_history()
        
        # Show initial greeting
        if st.session_state.get('show_greeting', True) and len(st.session_state.get('chat_history', [])) == 0:
            greeting_message = """
            Hello! 👋 Welcome to Dubai Event Permit Business Support Assistant.
            I'm here to help you with:
            
            ✅ Event permit applications in Dubai \n
            ✅ **Government fee calculations and estimates** \n
            ✅ Document requirements and checklists \n 
            ✅ Application timeline planning \n
            ✅ Regulatory compliance guidance \n
            
            Let's get your event permit sorted efficiently! How can I assist you today?
            """
            add_to_chat(greeting_message)
            st.session_state.show_greeting = False
            st.rerun()
        
        # Handle button clicks
        if handle_button_clicks():
            st.rerun()
        
        # Conversation flow
        if st.session_state.get('conversation_step') == 'greeting':
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.button("🎯 Start Fee Calculator", key="fee_calc", on_click=lambda: setattr(st.session_state, 'fee_calc_clicked', True))
            
            with col2:
                st.button("📋 Check Requirements", key="requirements", on_click=lambda: setattr(st.session_state, 'requirements_clicked', True))
            
            with col3:
                st.button("📞 Speak with Specialist", key="specialist", on_click=lambda: setattr(st.session_state, 'specialist_clicked', True))
            
            with col4:
                st.button("❓ General Questions", key="general", on_click=lambda: setattr(st.session_state, 'general_clicked', True))
        
        elif st.session_state.get('conversation_step') == 'event_classification':
            col1, col2 = st.columns(2)
            
            with col1:
                st.button("🏢 Internal Event", key="internal", on_click=lambda: setattr(st.session_state, 'internal_clicked', True))
            
            with col2:
                st.button("🌍 External Event", key="external", on_click=lambda: setattr(st.session_state, 'external_clicked', True))
        
        elif st.session_state.get('conversation_step') == 'internal_event_info':
            st.button("📊 Calculate Fees for Internal Event", key="calc_internal", on_click=lambda: setattr(st.session_state, 'calc_internal_clicked', True))
        
        elif st.session_state.get('conversation_step') == 'external_ticketing':
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.button("💰 Paid Ticketed", key="paid_ticketed", on_click=lambda: setattr(st.session_state, 'paid_ticketed_clicked', True))
            
            with col2:
                st.button("🎫 Free Ticketed", key="free_ticketed", on_click=lambda: setattr(st.session_state, 'free_ticketed_clicked', True))
            
            with col3:
                st.button("🆓 Non-Ticketed", key="non_ticketed", on_click=lambda: setattr(st.session_state, 'non_ticketed_clicked', True))
        
        elif st.session_state.get('conversation_step') == 'collect_event_details':
            # Event details form with enhanced error handling
            with st.form("event_details_form"):
                st.subheader("📋 Event Information Form")
                
                try:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        event_name = st.text_input("Event Name*", placeholder="Enter your event name")
                        
                        # Event types based on classification
                        try:
                            if st.session_state.event_data.get('ticketing_type') in ['paid_ticketed', 'free_ticketed']:
                                event_types = st.multiselect("Event Type*", TICKETED_EVENT_TYPES)
                            else:
                                event_types = st.multiselect("Event Type*", NON_TICKETED_EVENT_TYPES)
                        except Exception as e:
                            logger.error(f"Error with event types selection: {e}")
                            event_types = st.multiselect("Event Type*", TICKETED_EVENT_TYPES)
                        
                        venue = st.selectbox("Event Venue*", ["Select a venue..."] + DUBAI_VENUES)
                        industry = st.selectbox("Industry Type*", ["Select industry..."] + INDUSTRIES)
                        
                        try:
                            no_of_days = st.number_input("Number of Days*", min_value=1, max_value=30, value=1)
                        except Exception as e:
                            logger.error(f"Error with days input: {e}")
                            no_of_days = 1
                    
                    with col2:
                        try:
                            no_of_participants = st.number_input("Number of Participants*", min_value=1, max_value=10000, value=50)
                            no_of_performers = st.number_input("Number of Performers", min_value=0, max_value=100, value=0)
                        except Exception as e:
                            logger.error(f"Error with participant/performer inputs: {e}")
                            no_of_participants = 50
                            no_of_performers = 0
                        
                        try:
                            start_date = st.date_input("Event Start Date*", min_value=date.today())
                            end_date = st.date_input("Event End Date*", min_value=start_date)
                        except Exception as e:
                            logger.error(f"Error with date inputs: {e}")
                            start_date = date.today()
                            end_date = date.today()
                    
                    event_description = st.text_area("Event Description", placeholder="Brief description of your event...")
                    
                    submitted = st.form_submit_button("💰 Calculate Government Fees", use_container_width=True)
                    
                    if submitted:
                        try:
                            logger.info("Event details form submitted")
                            
                            # Validate required fields
                            validation_errors = []
                            
                            if not event_name or event_name.strip() == "":
                                validation_errors.append("Event name is required")
                            
                            if not event_types:
                                validation_errors.append("Please select at least one event type")
                            
                            if venue == "Select a venue...":
                                validation_errors.append("Please select a venue")
                            
                            if industry == "Select industry...":
                                validation_errors.append("Please select an industry")
                            
                            if no_of_participants <= 0:
                                validation_errors.append("Number of participants must be greater than 0")
                            
                            if start_date > end_date:
                                validation_errors.append("End date must be after start date")
                            
                            if validation_errors:
                                logger.warning(f"Form validation errors: {validation_errors}")
                                for error in validation_errors:
                                    st.error(error)
                            else:
                                # Store event data
                                st.session_state.event_data.update({
                                    'event_name': event_name.strip(),
                                    'event_types': event_types,
                                    'venue': venue,
                                    'industry': industry,
                                    'no_of_days': int(no_of_days),
                                    'no_of_participants': int(no_of_participants),
                                    'no_of_performers': int(no_of_performers),
                                    'start_date': start_date.isoformat(),
                                    'end_date': end_date.isoformat(),
                                    'event_description': event_description.strip() if event_description else ""
                                })
                                
                                logger.info(f"Event data stored: {event_name}")
                                add_to_chat(f"Event Details Submitted: {event_name}", False)
                                
                                # Calculate and display fees immediately
                                estimated_fee = calculate_estimated_fees(st.session_state.event_data)
                                fee_message = f"""
                                **💰 ESTIMATED GOVERNMENT FEES**
                                
                                Event: **{event_name}**
                                Classification: **{st.session_state.event_data.get('event_classification', 'Unknown').title()}**
                                Participants: **{no_of_participants:,}**
                                Duration: **{no_of_days} day(s)**
                                
                                **Estimated Total Fee: AED {estimated_fee:,}**
                                
                                *This is an estimate. Final fees may vary based on additional requirements and government regulations.*
                                """
                                add_to_chat(fee_message, True)
                                
                                st.session_state.conversation_step = 'show_results'
                                st.rerun()
                        
                        except ValueError as e:
                            logger.error(f"Value error in form submission: {e}")
                            st.error(f"Invalid input: {e}")
                        except Exception as e:
                            logger.error(f"Unexpected error in form submission: {e}")
                            st.error("An unexpected error occurred. Please try again.")
                
                except Exception as e:
                    logger.error(f"Error rendering form: {e}")
                    st.error("Error loading form. Please refresh the page.")
        
        elif st.session_state.get('conversation_step') == 'show_results':
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.button("💾 Save Application", key="save_app", on_click=lambda: setattr(st.session_state, 'save_app_clicked', True))
            
            with col2:
                st.button("🔄 Calculate Another Event", key="new_calc", on_click=lambda: setattr(st.session_state, 'new_calc_clicked', True))
            
            with col3:
                st.button("📋 View Summary", key="summary", on_click=lambda: setattr(st.session_state, 'summary_clicked', True))
        
        # Sidebar with current event info
        if st.session_state.get('event_data'):
            with st.sidebar:
                st.subheader("📊 Current Event Info")
                
                try:
                    event_info = st.session_state.event_data.copy()
                    
                    # Format and display event information
                    for key, value in event_info.items():
                        if key not in ['created_at'] and value is not None:
                            formatted_key = key.replace('_', ' ').title()
                            
                            # Format different types of values
                            if isinstance(value, list):
                                formatted_value = ", ".join(value) if value else "None"
                            elif isinstance(value, (int, float)):
                                formatted_value = f"{value:,}" if key in ['no_of_participants', 'no_of_performers'] else str(value)
                            else:
                                formatted_value = str(value)
                            
                            st.write(f"**{formatted_key}:** {formatted_value}")
                    
                    # Show estimated fee if available
                    if event_info:
                        try:
                            estimated_fee = calculate_estimated_fees(event_info)
                            st.write(f"**Estimated Fee:** AED {estimated_fee:,}")
                        except Exception as e:
                            logger.error(f"Error calculating fee for sidebar: {e}")
                            st.write("**Estimated Fee:** Error calculating")
                
                except Exception as e:
                    logger.error(f"Error displaying event info in sidebar: {e}")
                    st.error("Error displaying event information")
                
                # Clear event button
                if st.button("🗑️ Clear Current Event", key="clear_event"):
                    try:
                        logger.info("Clearing current event data")
                        st.session_state.event_data = {}
                        st.session_state.conversation_step = 'greeting'
                        st.session_state.chat_history = []
                        st.session_state.show_greeting = True
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error clearing event data: {e}")
                        st.error("Error clearing event data")
        
        # Footer with system info
        if st.session_state.get('debug_mode'):
            st.markdown("---")
            st.markdown("**System Information:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Python Version:** {sys.version_info.major}.{sys.version_info.minor}")
            
            with col2:
                try:
                    import streamlit as st_version
                    st.write(f"**Streamlit Version:** {st_version.__version__}")
                except:
                    st.write("**Streamlit Version:** Unknown")
            
            with col3:
                st.write(f"**App Uptime:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        logger.info("Main application completed successfully")
        
    except Exception as e:
        logger.critical(f"Critical error in main application: {e}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        
        # Show error to user
        st.error("A critical error occurred. Please refresh the page.")
        
        # In debug mode, show full error
        if st.session_state.get('debug_mode', False):
            st.error(f"Debug - Critical Error: {e}")
            st.code(traceback.format_exc())
        
        # Try to reset the application
        try:
            if st.button("🔄 Reset Application"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        except:
            pass

# ========================= APPLICATION ENTRY POINT =========================

if __name__ == "__main__":
    try:
        logger.info("=" * 50)
        logger.info("Dubai Event Permit Assistant Starting")
        logger.info("=" * 50)
        main()
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        print(f"Critical Error: {e}")
        print("Please check the logs for more details.")