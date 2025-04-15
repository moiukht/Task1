from sentence_transformers import SentenceTransformer, util
from pymongo import MongoClient
import nltk
import re
from db.connection import database_connect
nltk.download('punkt', download_dir='C:/Users/User/nltk_data')
nltk.download('punkt_tab' , download_dir='C:/Users/User/nltk_data')
nltk.download('wordnet')
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from datetime import datetime


# model
model = SentenceTransformer('all-MiniLM-L6-v2')
db = database_connect()

INTENTS= {
    "menu_inquiry": ["menu", "dish", "dishes", "food", "vegan", "vegetarian", "veg", "gluten", "pizza", "burger", "price", "cost", "drink", "drinks"],
    "reservation_request": ["book", "reservation", "reserve", "table", "party", "person", "people"],
    "restaurant_info" : ["contact", "social media", "facebook", "phone", "mobile", "cuisine", "features"],
    "restaurant_hours": ["open", "close", "hours", "timing"],
    "restaurant_location": ["location", "address", "where", "located"],
    "restaurant_specials": ["special", "offer", "deal", "discount", "happy hour"],
    "faq_query": ["How far in advance can I make a reservation?", "parking", "credit card", "dog", "wifi", "accessible", "faq"],
    "loyalty_info":["loyalty"],
    "promotional_offers":["promotions", "promotional", "event"],

}

SUGGESTED_ACTIONS = {
    "menu_inquiry": ["view_menu", "filter_by_diet", "ask_specials"],
    "reservation_request": ["make_reservation", "view_availability"],
    "restaurant_hours": ["view_hours"],
    "restaurant_location": ["get_directions"],
    "restaurant_specials": ["view_specials", "view_happy_hour"],
    "faq_query": ["view_faqs", "contact_support"],
    "unknown": ["repeat_question", "talk_to_staff"],
    "restaurant_info" : ["contact_info", "view_hours", "get_directions", "see_features", "about", "available_cuisines", "view_menu"]
}


intent_embeddings = {
    intent: model.encode(examples, convert_to_tensor=True)
    for intent, examples in INTENTS.items()
}

def preprocess(text):
    lemmatizer = WordNetLemmatizer()
    tokens = word_tokenize(text.lower())
    return " ".join([lemmatizer.lemmatize(token) for token in tokens if token.isalnum()])

# intent detection using cosine similarity
def detect_intent(user_input):
    user_embedding = model.encode(user_input, convert_to_tensor=True)
    scores = {}

    for intent, embeddings in intent_embeddings.items():
        cosine_scores = util.cos_sim(user_embedding, embeddings)
        scores[intent] = float(cosine_scores.max())

    best_intent = max(scores, key=scores.get)
    return best_intent if scores[best_intent] > 0.3 else "unknown"

# Generate response 
def generate_response(intent, user_message):
    entities = []
    if intent == "restaurant_info":
       
        info = db.restaurant.find_one({}, {
            "_id": 0,
            "contact": 1,
            "social_media": 1,
            "cuisines": 1,
            "about": 1
        })
        return info, None

    if intent == "menu_inquiry":
        dietary_keywords = {
            "gluten-free": "gluten_free",
            "gluten free": "gluten_free",
            "vegan": "vegan",
            "vegetarian": "vegetarian",
            "veg": "vegetarian"
        }
        matched_items = []
        for keyword, field in dietary_keywords.items():
            if keyword in user_message.lower():
                # Query menu_items collection when specified dietary restriction
                query = {field: True}
                cursor = db.menu_items.find(query, {"name": 1})
                matched_items = [item["name"] for item in cursor]
                entities.append({"dietary":keyword})
                if matched_items:
                    res = f"Yes, we have the following {keyword} items: {', '.join(matched_items)}. Would you like more details?"
                else:
                    res = f"Sorry, we couldn't find any {keyword} items on the menu."
                return res, (entities if entities else None)

        # If want to see entire menu
        if "menu" in user_message.lower() or "dishes" in user_message.lower():
            cursor = db.menu_items.find({}, {"name": 1})
            all_items = [item["name"] for item in cursor]
            if all_items:
                res= f"Here's our full menu: {', '.join(all_items)}. Would you like to filter by dietary preferences or categories?"
            else:
                res= "Sorry, I couldn't retrieve the menu right now."
        res = "Yes, we have various items on the menu. Would you like to filter by category or dietary preference?"
        return res, None
    elif intent == "reservation_request":
        guests = time = date = None
        #number of guests
        guests_match = re.search(
            r'\b(?:for\s+(\d+)\s*(?:people|persons|guests|table|party)?|(\d+)\s*(?:people|persons|guests|table|party))\b',
            user_message, re.IGNORECASE
        )
        if guests_match:
            guests = int(guests_match.group(1) or guests_match.group(2))

        
        #time 
        time_match = re.search(r'\b(at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm))\b|\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', user_message, re.IGNORECASE)
        if time_match:
            
            if time_match.group(1):
                time = time_match.group(1).strip()
            if time and "at" in time:
                time = time.replace("at", "").strip()
            else:
                
                time = time_match.group(0).strip()

        #date
        date_match = re.search(
            r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}[,]?\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2}[,]?\s+\d{4})\b',
            user_message, re.IGNORECASE
        )
        if date_match:
            date = date_match.group(1).strip()

        for key, value in [("guests", guests), ("date", date), ("time", time)]:
            if value is not None:
                entities.append({key: value})

        
        # Check existing reservations
        existing_reservation = db.reservations.find_one({
            "details.date": date,
            "details.time": time,
            "details.party_size": guests,
        })

        if existing_reservation:
            response= f"Sorry, we already have a reservation for {guests} guests at {time} on {date}. Please choose another time."

        #responses
        response = "Got it!"
       
        if guests and date and time:
            response += f" A table for {guests} guests at {time} on {date}. Let me confirm your reservation."
        elif guests and date:
            response += f" A table for {guests} guests on {date}. For what time?"
        elif guests and time:
            response += f" A table for {guests} guests at {time}. Could you tell me the date?"
        elif date and time:
            response += f"Reservation at {time} on {date}. For how many guests?"
        elif guests:
            response += f"Reservation for {guests} guests. On what day and at what time?"
        elif date:
            response += f"Reservation on {date}. How many guests and what time?"
        elif time:
            response += f"Reservation at {time}. For how many guests and on what day?"
        elif not (guests and date and time):
            response += f'Could you please let me know the number of guests, as well as your preferred time and date for the reservation?'
        return response, (entities if entities else None)


    elif intent == "restaurant_hours":
        info = db.restaurant.find_one({}, {"_id": 0, "hours": 1})
        res= f"Our hours are: {info['hours']}"
        return res, None

    elif intent == "restaurant_location":
        info = db.restaurant.find_one({}, {"_id": 0, "address": 1})
        res= f"Our location is: {info['address']}"
        return res, None

    elif intent == "restaurant_specials":
    # Correct collection and fields
        specials = db.menu_specials.find_one({}, {"_id": 0})

        if specials:
            happy_hour = specials.get("happy_hour", {})
            weekly_specials = specials.get("weekly_specials", [])

            # Happy Hour Section
            if happy_hour:
                happy_hour_days = ", ".join(day.capitalize() for day in happy_hour.get("days", []))
                happy_hour_offers = ", ".join(happy_hour.get("offers", []))
                happy_hour_line = (
                    f"Happy Hour: Days- ({happy_hour_days}), Time-{happy_hour.get('times', 'N/A')}, "
                    f"Offers: {happy_hour_offers}"
                )
            else:
                happy_hour_line = "No Happy Hour specials available."

            # Weekly Specials Section
            if weekly_specials:
                specials_info = ", ".join(
                    [f"{special['name']}: {special['description']}" for special in weekly_specials]
                )
            else:
                specials_info = "No weekly specials available."

            response = f"{happy_hour_line}\n{specials_info}"
        else:
            response = "No restaurant specials found."

        return response, None


    elif intent == "faq_query":
        answer = f'Here are all the faqs: {db.faqs}'
        return answer, None
    else:
        res= "I'm not sure how to help with that. Would you like to speak to our staff?"
        return res, None
    


# Final handler
def handle_user_message(user_input, user_id,session_id):
    preprocessed_input = preprocess(user_input)
    intent = detect_intent(preprocessed_input)
    response, entities = generate_response(intent, user_input)
    actions = SUGGESTED_ACTIONS.get(intent, SUGGESTED_ACTIONS["unknown"])
    
    responsefull = {
    "response": response,
        "intent": intent,
        "suggested_actions": actions
    }

    return responsefull, entities
