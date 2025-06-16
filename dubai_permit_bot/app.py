import streamlit as st
import pymongo
from datetime import datetime, date
import json

# Initialize MongoDB connection (replace with your connection string)
@st.cache_resource
def init_connection():
    try:
        # Replace with your MongoDB connection string
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        return client["dubai_events"]["event_applications"]
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# Initialize session state
def init_session_state():
    if 'conversation_step' not in st.session_state:
        st.session_state.conversation_step = 'greeting'
    if 'event_data' not in st.session_state:
        st.session_state.event_data = {}
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'show_greeting' not in st.session_state:
        st.session_state.show_greeting = True

# Event types based on ticketing
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

def add_to_chat(message, is_bot=True):
    st.session_state.chat_history.append({
        'message': message,
        'is_bot': is_bot,
        'timestamp': datetime.now()
    })

def display_chat_history():
    for chat in st.session_state.chat_history:
        if chat['is_bot']:
            with st.chat_message("assistant"):
                st.markdown(chat['message'])
        else:
            with st.chat_message("user"):
                st.markdown(chat['message'])

def calculate_estimated_fees(event_data):
    """Calculate estimated government fees based on event data"""
    base_fee = 0
    
    # Base fee calculation based on event classification
    if event_data.get('event_classification') == 'internal':
        base_fee = 2000  # AED
    elif event_data.get('event_classification') == 'external':
        if event_data.get('ticketing_type') == 'paid':
            base_fee = 8000
        elif event_data.get('ticketing_type') == 'free_registered':
            base_fee = 5000
        else:
            base_fee = 3000
    
    # Additional fees based on participants
    participants = event_data.get('no_of_participants', 0)
    if participants > 500:
        base_fee += 3000
    elif participants > 200:
        base_fee += 1500
    elif participants > 100:
        base_fee += 800
    
    # Additional fees based on duration
    days = event_data.get('no_of_days', 1)
    if days > 3:
        base_fee += (days - 3) * 500
    
    # Additional fees based on performers
    performers = event_data.get('no_of_performers', 0)
    if performers > 0:
        base_fee += performers * 200
    
    return base_fee

def save_to_mongodb(event_data):
    """Save event data to MongoDB"""
    try:
        collection = init_connection()
        if collection is not None:
            event_data['created_at'] = datetime.now()
            event_data['estimated_fee'] = calculate_estimated_fees(event_data)
            result = collection.insert_one(event_data)
            return result.inserted_id
        return None
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        return None

def handle_button_clicks():
    """Handle all button clicks and update conversation state"""
    
    # Greeting buttons
    if st.session_state.get('fee_calc_clicked'):
        add_to_chat("I'd like to calculate government fees for my event", False)
        st.session_state.conversation_step = 'event_classification'
        st.session_state.show_greeting = False
        st.session_state.fee_calc_clicked = False
        return True
    
    if st.session_state.get('requirements_clicked'):
        add_to_chat("I want to check document requirements", False)
        requirements_message = """
        **📋 DOCUMENT REQUIREMENTS CHECKER**
        
        For Dubai event permits, you'll typically need:
        
        **For All Events:**
        ✅ Completed application form
        ✅ Company trade license copy
        ✅ Event concept/description
        ✅ Venue booking confirmation
        ✅ Event layout/floor plan
        
        **For External Events:**
        ✅ Marketing materials/brochures
        ✅ Speaker/performer details
        ✅ Security plan (for large events)
        ✅ Insurance certificate
        
        **For Paid Events:**
        ✅ Ticketing system details
        ✅ Revenue projections
        ✅ Payment processing setup
        
        Would you like me to help calculate your fees as well?
        """
        add_to_chat(requirements_message)
        st.session_state.requirements_clicked = False
        return True
    
    if st.session_state.get('specialist_clicked'):
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
        📧 Email: permits@dubaievents.gov.ae
        📱 Phone: +971-4-XXX-XXXX
        🕐 Hours: Sunday-Thursday, 8:00 AM - 3:00 PM
        
        In the meantime, I can help you get started with fee calculations!
        """
        add_to_chat(specialist_message)
        st.session_state.specialist_clicked = False
        return True
    
    if st.session_state.get('general_clicked'):
        add_to_chat("I have general permit questions", False)
        general_message = """
        **❓ GENERAL PERMIT INFORMATION**
        
        **Common Questions:**
        
        **Q: How long does permit processing take?**
        A: 5-15 working days depending on event complexity
        
        **Q: Can I apply for multiple events at once?**
        A: Yes, but each event needs a separate application
        
        **Q: What if my event details change?**
        A: You must notify authorities within 48 hours of changes
        
        **Q: Are there restrictions on event timing?**
        A: Yes, some venues have restrictions during Ramadan and national holidays
        
        For more specific questions, please refer to this [Dubai Events FAQ](https://epermits.det.gov.ae/ePermit/FAQDocumentEN.html) or contact our support team.

        Let me help you calculate your specific event fees!
        """
        add_to_chat(general_message)
        st.session_state.general_clicked = False
        return True
    
    # Event classification buttons
    if st.session_state.get('internal_clicked'):
        add_to_chat("Internal Event - Company/organizational event for employees only", False)
        st.session_state.event_data['event_classification'] = 'internal'
        st.session_state.conversation_step = 'internal_event_info'
        st.session_state.internal_clicked = False
        return True
    
    if st.session_state.get('external_clicked'):
        add_to_chat("External Event - Event with external guests, clients, or public attendance", False)
        st.session_state.event_data['event_classification'] = 'external'
        st.session_state.conversation_step = 'external_ticketing'
        st.session_state.external_clicked = False
        return True
    
    # Internal event button
    if st.session_state.get('calc_internal_clicked'):
        add_to_chat("Yes, let's calculate the estimated fees", False)
        st.session_state.conversation_step = 'collect_event_details'
        st.session_state.calc_internal_clicked = False
        return True
    
    # Ticketing buttons
    if st.session_state.get('paid_clicked'):
        add_to_chat("Paid Event - Admission fees/ticket sales", False)
        st.session_state.event_data['ticketing_type'] = 'paid'
        st.session_state.conversation_step = 'collect_event_details'
        st.session_state.paid_clicked = False
        return True
    
    if st.session_state.get('free_reg_clicked'):
        add_to_chat("Free with Registration - Controlled access", False)
        st.session_state.event_data['ticketing_type'] = 'free_registered'
        st.session_state.conversation_step = 'collect_event_details'
        st.session_state.free_reg_clicked = False
        return True
    
    if st.session_state.get('free_open_clicked'):
        add_to_chat("Free Open Access - No registration required", False)
        st.session_state.event_data['ticketing_type'] = 'free_open'
        st.session_state.conversation_step = 'collect_event_details'
        st.session_state.free_open_clicked = False
        return True
    
    # Results buttons
    if st.session_state.get('save_app_clicked'):
        application_id = save_to_mongodb(st.session_state.event_data)
        if application_id:
            add_to_chat("✅ Application saved successfully! Reference ID: " + str(application_id)[:8], True)
        else:
            add_to_chat("❌ Failed to save application. Please try again.", True)
        st.session_state.save_app_clicked = False
        return True
    
    if st.session_state.get('new_calc_clicked'):
        st.session_state.conversation_step = 'greeting'
        st.session_state.event_data = {}
        st.session_state.show_greeting = True
        add_to_chat("Let's calculate fees for another event!", False)
        st.session_state.new_calc_clicked = False
        return True
    
    if st.session_state.get('summary_clicked'):
        estimated_fee = calculate_estimated_fees(st.session_state.event_data)
        base_fee = 2000 if st.session_state.event_data['event_classification'] == 'internal' else 3000
        participant_fee = (st.session_state.event_data['no_of_participants'] // 100) * 500
        duration_fee = max(0, (st.session_state.event_data['no_of_days'] - 3) * 500)
        performer_fee = st.session_state.event_data['no_of_performers'] * 200
        
        breakdown = f"""
        **DETAILED FEE BREAKDOWN**
        
        Base Fee: AED {base_fee:,}
        Participant Fee: AED {participant_fee:,}
        Duration Fee: AED {duration_fee:,}
        Performer Fee: AED {performer_fee:,}
        
        **Total: AED {estimated_fee:,}**
        """
        add_to_chat(breakdown, True)
        st.session_state.summary_clicked = False
        return True
    
    return False

def main():
    st.set_page_config(
        page_title="Dubai Event Permit Assistant",
        page_icon="🎪",
        layout="wide"
    )
    
    # Custom CSS for better styling
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
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
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
    
    # Show initial greeting message when app loads
    if st.session_state.show_greeting and len(st.session_state.chat_history) == 0:
        greeting_message = """
        Hello! 👋 Welcome to Dubai Event Permit Business Support Assistant.
        I'm here to help you with:
        
        ✅ Event permit applications in Dubai

        ✅ **Government fee calculations and estimates**

        ✅ Document requirements and checklists  

        ✅ Application timeline planning

        ✅ Regulatory compliance guidance
        
        Let's get your event permit sorted efficiently! How can I assist you today?
        """
        add_to_chat(greeting_message)
        st.session_state.show_greeting = False
        st.rerun()
    
    # Handle button clicks
    if handle_button_clicks():
        st.rerun()
    
    # Conversation flow
    if st.session_state.conversation_step == 'greeting':
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.button("🎯 Start Fee Calculator", key="fee_calc", on_click=lambda: setattr(st.session_state, 'fee_calc_clicked', True))
        
        with col2:
            st.button("📋 Check Requirements", key="requirements", on_click=lambda: setattr(st.session_state, 'requirements_clicked', True))
        
        with col3:
            st.button("📞 Speak with Specialist", key="specialist", on_click=lambda: setattr(st.session_state, 'specialist_clicked', True))
        
        with col4:
            st.button("❓ General Questions", key="general", on_click=lambda: setattr(st.session_state, 'general_clicked', True))
    
    elif st.session_state.conversation_step == 'event_classification':
        classification_message = """
        Perfect! I'll guide you through the government fee calculation process.

        **Step 1: Event Classification**

        Is your event:

        🏢 **INTERNAL** - Company/organizational event for employees only

        🌍 **EXTERNAL** - Event with external guests, clients, or public attendance

        This determines your permit category and fee structure.
        """
        add_to_chat(classification_message)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.button("🏢 Internal Event", key="internal", on_click=lambda: setattr(st.session_state, 'internal_clicked', True))
        
        with col2:
            st.button("🌍 External Event", key="external", on_click=lambda: setattr(st.session_state, 'external_clicked', True))
    
    elif st.session_state.conversation_step == 'internal_event_info':
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
        
        st.button("📊 Calculate Fees for Internal Event", key="calc_internal", on_click=lambda: setattr(st.session_state, 'calc_internal_clicked', True))
    
    elif st.session_state.conversation_step == 'external_ticketing':
        ticketing_message = """
        **EXTERNAL EVENT IDENTIFIED** 🌍
        For external events, I need to understand your ticketing structure:
        💰 **PAID TICKETED** - Admission fees, ticket sales, revenue generation
        🎫 **FREE TICKETED** - No charge but controlled access with registration/badges  
        🆓 **NON-TICKETED** - No charge, no registration, open to public
        This classification significantly impacts your permits and fees.
        """
        add_to_chat(ticketing_message)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.button("💰 Paid Event", key="paid", on_click=lambda: setattr(st.session_state, 'paid_clicked', True))
        
        with col2:
            st.button("🎫 Free with Registration", key="free_reg", on_click=lambda: setattr(st.session_state, 'free_reg_clicked', True))
        
        with col3:
            st.button("🆓 Free Open Access", key="free_open", on_click=lambda: setattr(st.session_state, 'free_open_clicked', True))
    
    elif st.session_state.conversation_step == 'collect_event_details':
        details_message = """
        **EVENT DETAILS COLLECTION** 📝
        Now I need specific information to calculate accurate government fees. Please fill out the form below:
        """
        add_to_chat(details_message)
        
        # Event details form
        with st.form("event_details_form"):
            st.subheader("📋 Event Information Form")
            
            col1, col2 = st.columns(2)
            
            with col1:
                event_name = st.text_input("Event Name*", placeholder="Enter your event name")
                
                # Event types based on classification
                if st.session_state.event_data.get('ticketing_type') in ['paid', 'free_registered']:
                    event_types = st.multiselect("Event Type*", TICKETED_EVENT_TYPES)
                else:
                    event_types = st.multiselect("Event Type*", NON_TICKETED_EVENT_TYPES)
                
                venue = st.selectbox("Event Venue*", ["Select a venue..."] + DUBAI_VENUES)
                industry = st.selectbox("Industry Type*", ["Select industry..."] + INDUSTRIES)
                no_of_days = st.number_input("Number of Days*", min_value=1, max_value=30, value=1)
            
            with col2:
                no_of_participants = st.number_input("Number of Participants*", min_value=1, max_value=10000, value=50)
                no_of_performers = st.number_input("Number of Performers", min_value=0, max_value=100, value=0)
                
                start_date = st.date_input("Event Start Date*", min_value=date.today())
                end_date = st.date_input("Event End Date*", min_value=start_date)
            
            event_description = st.text_area("Event Description", placeholder="Brief description of your event...")
            
            submitted = st.form_submit_button("💰 Calculate Government Fees", use_container_width=True)
            
            if submitted:
                # Validate required fields
                if not all([event_name, event_types, venue != "Select a venue...", industry != "Select industry..."]):
                    st.error("Please fill in all required fields marked with *")
                else:
                    # Store event data
                    st.session_state.event_data.update({
                        'event_name': event_name,
                        'event_types': event_types,
                        'venue': venue,
                        'industry': industry,
                        'no_of_days': no_of_days,
                        'no_of_participants': no_of_participants,
                        'no_of_performers': no_of_performers,
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'event_description': event_description
                    })
                    
                    add_to_chat(f"Event Details Submitted: {event_name}", False)
                    st.session_state.conversation_step = 'show_results'
                    st.rerun()
    
    elif st.session_state.conversation_step == 'show_results':
        # Calculate fees
        estimated_fee = calculate_estimated_fees(st.session_state.event_data)
        
        # Display results
        results_message = f"""
        **🎉 FEE CALCULATION COMPLETE**
        **Event:** {st.session_state.event_data['event_name']}
        **Classification:** {st.session_state.event_data['event_classification'].title()}
        **Participants:** {st.session_state.event_data['no_of_participants']}
        **Duration:** {st.session_state.event_data['no_of_days']} days
        **Venue:** {st.session_state.event_data['venue']}
        **💰 ESTIMATED GOVERNMENT FEES: AED {estimated_fee:,}**
        *Note: This is an estimated calculation. Final fees may vary based on additional requirements and current government rates.*
        Would you like me to save this information for future reference?
        """
        add_to_chat(results_message)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.button("💾 Save Application", key="save_app", on_click=lambda: setattr(st.session_state, 'save_app_clicked', True))
        
        with col2:
            st.button("🔄 Calculate Another Event", key="new_calc", on_click=lambda: setattr(st.session_state, 'new_calc_clicked', True))
        
        with col3:
            st.button("📋 View Summary", key="summary", on_click=lambda: setattr(st.session_state, 'summary_clicked', True))
    
    # Sidebar with current event info
    if st.session_state.event_data:
        with st.sidebar:
            st.subheader("📊 Current Event Info")
            for key, value in st.session_state.event_data.items():
                if key not in ['created_at']:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            if st.button("🗑️ Clear Current Event", key="clear_event"):
                st.session_state.event_data = {}
                st.session_state.conversation_step = 'greeting'
                st.session_state.chat_history = []
                st.session_state.show_greeting = True
                st.rerun()

if __name__ == "__main__":
    main()