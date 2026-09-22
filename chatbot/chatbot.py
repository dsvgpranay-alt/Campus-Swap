import joblib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

model = joblib.load(BASE_DIR / "intent_model.pkl")
vectorizer = joblib.load(BASE_DIR / "vectorizer.pkl")


def predict_intent(message):
    X = vectorizer.transform([message])
    intent = model.predict(X)[0]
    confidence = model.predict_proba(X).max()

    return intent, confidence


def get_response(message):
    intent, confidence = predict_intent(message)

    if confidence < 0.20:
        return {
            "intent": "unknown",
            "response": "Sorry, I didn't understand that. Try asking about buying, selling, or finding an item."
        }

    if intent == "greeting":
        return {
            "intent": intent,
            "response": "Hey! How can I help you with Campus Swap?"
        }

    elif intent == "sell_item":
        return {
            "intent": intent,
            "response": "You can sell an item by going to the Sell Item section."
        }

    elif intent == "buy_item":
        return {
            "intent": intent,
            "response": "You can browse available listings and contact the seller."
        }

    elif intent == "contact_seller":
        return {
            "intent": intent,
            "response": "Open an item listing to contact the seller."
        }

    elif intent == "platform_info":
        return {
            "intent": intent,
            "response": "Campus Swap is a platform where students can buy and sell items within the campus community."
        }

    elif intent == "report_problem":
        return {
            "intent": intent,
            "response": "Sorry about that. Please describe the problem or contact the administrator."
        }

    elif intent == "goodbye":
        return {
            "intent": intent,
            "response": "Bye! Good luck with Campus Swap!"
        }

    elif intent == "search_item":
        return {
            "intent": intent,
            "response": "Sure! Tell me what item you're looking for."
        }

    return {
        "intent": intent,
        "response": "I'm not sure how to help with that."
    }