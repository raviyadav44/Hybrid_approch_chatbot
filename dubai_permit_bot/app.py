import streamlit as st
import pymongo
from pymongo import MongoClient
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
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        
        logger = logging.getLogger('dubai_event_app')
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        
        file_handler = logging.FileHandler('logs/dubai_event_app.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(log_format))
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        logger.addHandler(console_handler)
        
        return logger
    except Exception as e:
        logging.basicConfig(level=logging.INFO, format=log_format)
        logger = logging.getLogger('dubai_event_app')
        logger.error(f"Failed to setup advanced logging: {e}")
        return logger

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
            st.error(f"An error occurred: {str(e)}")
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
        connection_string = os.getenv('MONGODB_URI', "dummy_url")
        
        if not connection_string:
            logger.error("MongoDB connection string is not set")
            st.error("Database connection string is not configured. Please check your environment variables.")
            return None

        logger.debug(f"Using connection string: {connection_string[:20]}...")
        
        client = pymongo.MongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=10
        )
        
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
        
        db = client["Chatbot"]
        collection = db["event_data"]
        
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
    "Hotel",
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

# ========================= CALCULATION FUNCTIONS =========================

def calculate_event_permit_cost(
    event_type,
    is_ticketed,
    venue_type=None,
    num_days=1,
    num_performers=0,
    num_speakers=0,
    is_urgent=False,
    is_amendment=False
):
    """
    Calculate the total permit cost for an event based on various parameters.
    Uses the pricing structure from the provided CSV data.
    """
    # Define the pricing structure from CSV with day handling info
    pricing_data = {
        "Exhibition": {"rate": 1270, "urgent": 500, "amendment": "NA", "days_handling": "ANY"},
        "Conference": {"rate": 1270, "urgent": 500, "amendment": "NA", "days_handling": "ANY"},
        "Conference + Exhibition": {"rate": 1770, "urgent": 500, "amendment": "NA", "days_handling": "ANY"},
        "Product Launch/Forum/Seminar/Summit": {"rate": 1270, "urgent": 500, "amendment": "NA", "days_handling": "ANY"},
        "Exhibition/Product Launch + Conference/Forum/Seminar/Summit": {"rate": 1770, "urgent": 500, "amendment": "NA", "days_handling": "ANY"},
        "Award Ceremony": {"rate": 1520, "urgent": 500, "amendment": 1320, "days_handling": "1"},
        "Award Ceremony + Conference": {"rate": 2570, "urgent": 500, "amendment": 1320, "days_handling": "1"},
        "Award Ceremony + Conference + Exhibition": {"rate": 3070, "urgent": 500, "amendment": 1320, "days_handling": "1"},
        "DJ Event": {"rate": 1520, "urgent": 500, "amendment": 1320, "days_handling": "1"},
        "Musical Event": {"rate": 1520, "urgent": 500, "amendment": 1320, "days_handling": "1"},
        "Comedy Show": {"rate": 1520, "urgent": 500, "amendment": 1320, "days_handling": "1"}
    }

    # First try exact matching (case insensitive)
    matched_type = None
    normalized_input = event_type.strip().lower()
    
    # Try exact match first
    for event_key in pricing_data:
        if event_key.lower() == normalized_input:
            matched_type = event_key
            break
    
    # If no exact match, try partial match (but prioritize longer matches)
    if not matched_type:
        best_match = None
        best_length = 0
        
        for event_key in pricing_data:
            if event_key.lower() in normalized_input:
                # Prefer the longest matching key
                if len(event_key) > best_length:
                    best_match = event_key
                    best_length = len(event_key)
        
        matched_type = best_match
    
    if not matched_type:
        matched_type = "Conference"  # Default fallback
        logger.warning(f"Could not match event type: {event_type}. Using default.")
    
    # Get pricing info
    event_pricing = pricing_data[matched_type]
    base_rate = event_pricing["rate"]
    
    # Initialize cost components
    cost_components = {
        'base_fee': base_rate,
        'urgent_fee': event_pricing["urgent"] if is_urgent else 0,
        'amendment_fee': event_pricing["amendment"] if is_amendment and event_pricing["amendment"] != "NA" else 0,
        'additional_days_fee': 0
    }
    
    # Handle day-based pricing for ticketed events where days_handling is not "ANY"
    if is_ticketed and event_pricing["days_handling"] != "ANY":
        included_days = int(event_pricing["days_handling"])
        if num_days > included_days:
            additional_days = num_days - included_days
            cost_components['additional_days_fee'] = additional_days * 800
    
    # Calculate total cost
    total_cost = sum(v for v in cost_components.values() if isinstance(v, (int, float)))
    
    # Prepare breakdown
    breakdown = {
        'total_cost': total_cost,
        'cost_breakdown': cost_components,
        'calculation_notes': []
    }
    
    # Add calculation notes
    if is_urgent:
        breakdown['calculation_notes'].append(f"Added urgent processing fee: {cost_components['urgent_fee']} AED")
    
    if is_amendment and event_pricing["amendment"] != "NA":
        breakdown['calculation_notes'].append(f"Added amendment fee: {cost_components['amendment_fee']} AED")
    
    if cost_components['additional_days_fee'] > 0:
        breakdown['calculation_notes'].append(
            f"Added {cost_components['additional_days_fee']} AED for {num_days - int(event_pricing['days_handling'])} additional day(s) at 800 AED/day"
        )
    
    # Add debug info in debug mode
    if st.session_state.get('debug_mode', False):
        breakdown['calculation_notes'].append(
            f"Matched event type: {matched_type} (from input: {event_type})"
        )
    
    return breakdown

def map_event_data_to_calculator_params(event_data):
    """
    Map event data from the app to calculator parameters.
    """
    # Extract event types
    event_types = event_data.get('event_types', [])
    if isinstance(event_types, str):
        event_types = [event_types]
    
    # Determine main event type (use the first one if multiple selected)
    event_type = event_types[0] if event_types else "Conference"
    
    # Determine if ticketed
    ticketing_type = event_data.get('ticketing_type', 'non_ticketed')
    is_ticketed = ticketing_type in ['paid_ticketed', 'free_ticketed']
    
    # Map venue type
    venue = event_data.get('venue', '')
    venue_type = 'hotel' if 'hotel' in venue.lower() else 'other'
    
    # Get other parameters
    num_days = event_data.get('no_of_days', 1)
    num_performers = event_data.get('no_of_performers', 0)
    num_speakers = event_data.get('no_of_speakers', 0)
    
    # Get urgent/amendment status with defaults
    is_urgent = event_data.get('is_urgent', False)
    is_amendment = event_data.get('is_amendment', False)
    
    return {
        'event_type': event_type,
        'is_ticketed': is_ticketed,
        'venue_type': venue_type,
        'num_days': num_days,
        'num_performers': num_performers,
        'num_speakers': num_speakers,
        'is_urgent': is_urgent,
        'is_amendment': is_amendment
    }

@handle_exceptions
def calculate_estimated_fees(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate estimated government fees using the new calculation logic"""
    try:
        logger.debug(f"Calculating fees for event: {event_data.get('event_name', 'Unknown')}")
        
        # Validate input data
        if not isinstance(event_data, dict):
            raise ValueError("Event data must be a dictionary")
        
        # Map event data to calculator parameters
        params = map_event_data_to_calculator_params(event_data)
        
        # Calculate fees using the new function
        result = calculate_event_permit_cost(**params)
        
        logger.info(f"Fee calculation completed: {result['total_cost']} AED")
        logger.debug(f"Fee breakdown: {result['cost_breakdown']}")
        
        return result
        
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid data for fee calculation: {e}")
        st.error("Invalid event data for fee calculation")
        return {'total_cost': 0, 'cost_breakdown': {}, 'calculation_notes': ["Error calculating fees"]}
    except Exception as e:
        logger.error(f"Unexpected error in fee calculation: {e}")
        st.error("Error calculating fees")
        return {'total_cost': 0, 'cost_breakdown': {}, 'calculation_notes': ["Error calculating fees"]}

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

# ========================= DATABASE OPERATIONS =========================

@handle_exceptions
def save_to_mongodb(event_data: Dict[str, Any]) -> Optional[str]:
    """Save event data to MongoDB with comprehensive error handling"""
    try:
        logger.info(f"Saving event data: {event_data.get('event_name', 'Unknown')}")
        
        if not event_data:
            raise ValueError("Event data is empty")
        
        collection = init_connection()
        if collection is None:
            logger.error("No database connection available")
            st.error("Database connection not available")
            return None
        
        save_data = event_data.copy()
        save_data['created_at'] = datetime.now()
        
        fee_result = calculate_event_permit_cost(**map_event_data_to_calculator_params(event_data))
        save_data['estimated_fee'] = fee_result['total_cost']
        save_data['fee_breakdown'] = fee_result['cost_breakdown']
        save_data['app_version'] = "1.2"  # Updated version
        
        required_fields = ['event_name', 'event_classification']
        for field in required_fields:
            if field not in save_data or not save_data[field]:
                raise ValueError(f"Required field missing: {field}")
        
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
                fee_result = calculate_estimated_fees(st.session_state.event_data)
                
                breakdown = f"""
                **DETAILED FEE BREAKDOWN** \n
                """
                
                # Add each cost component
                for key, value in fee_result['cost_breakdown'].items():
                    if value > 0:  # Only show non-zero items
                        breakdown += f"{key.replace('_', ' ').title()}: AED {value:,}\n"
                
                # Add total
                breakdown += f"\n**Total: AED {fee_result['total_cost']:,}**"
                
                # Add calculation notes if any
                if fee_result['calculation_notes']:
                    breakdown += "\n\n**Notes:**\n"
                    for note in fee_result['calculation_notes']:
                        breakdown += f"- {note}\n"
                
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
                            no_of_speakers = st.number_input("Number of Speakers", min_value=0, max_value=100, value=0)
                        except Exception as e:
                            logger.error(f"Error with participant/performer inputs: {e}")
                            no_of_participants = 50
                            no_of_performers = 0
                            no_of_speakers = 0
                        
                        try:
                            start_date = st.date_input("Event Start Date*", min_value=date.today())
                            end_date = st.date_input("Event End Date*", min_value=start_date)
                        except Exception as e:
                            logger.error(f"Error with date inputs: {e}")
                            start_date = date.today()
                            end_date = date.today()
                    
                    # Add urgent/amendment options
                    col1, col2 = st.columns(2)
                    with col1:
                        is_urgent = st.checkbox("Urgent Processing (+500 AED)", value=False)
                    with col2:
                        is_amendment = st.checkbox("Amendment Request", value=False)
                    
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
                                    'no_of_speakers': int(no_of_speakers),
                                    'start_date': start_date.isoformat(),
                                    'end_date': end_date.isoformat(),
                                    'is_urgent': is_urgent,
                                    'is_amendment': is_amendment,
                                    'event_description': event_description.strip() if event_description else ""
                                })
                                
                                logger.info(f"Event data stored: {event_name}")
                                add_to_chat(f"Event Details Submitted: {event_name}", False)
                                
                                # Calculate and display fees
                                fee_result = calculate_estimated_fees(st.session_state.event_data)
                                fee_message = f"""
                                **💰 ESTIMATED GOVERNMENT FEES**
                                
                                Event: **{event_name}**
                                Classification: **{st.session_state.event_data.get('event_classification', 'Unknown').title()}**
                                Participants: **{no_of_participants:,}**
                                Duration: **{no_of_days} day(s)**
                                
                                **Estimated Total Fee: AED {fee_result['total_cost']:,}**
                                
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
                            
                            if isinstance(value, list):
                                formatted_value = ", ".join(value) if value else "None"
                            elif isinstance(value, (int, float)):
                                formatted_value = f"{value:,}" if key in ['no_of_participants', 'no_of_performers', 'no_of_speakers'] else str(value)
                            else:
                                formatted_value = str(value)
                            
                            st.write(f"**{formatted_key}:** {formatted_value}")
                    
                    # Show estimated fee if available
                    if event_info:
                        try:
                            fee_result = calculate_estimated_fees(event_info)
                            st.write(f"**Estimated Fee:** AED {fee_result['total_cost']:,}")
                        except Exception as e:
                            logger.error(f"Error calculating fee for sidebar: {e}")
                            st.write("**Estimated Fee:** Calculating...")
                
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
        
        st.error("A critical error occurred. Please refresh the page.")
        
        if st.session_state.get('debug_mode', False):
            st.error(f"Debug - Critical Error: {e}")
            st.code(traceback.format_exc())
        
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