class UserInteractionHandler:
    def __init__(self, users_collection, feedback_collection, bot, main_keyboard):
        self.users_collection = users_collection
        self.feedback_collection = feedback_collection
        self.bot = bot
        self.main_keyboard = main_keyboard
    
    def get_all_users(self):
        return [user["_id"] for user in self.users_collection.find({}, {"_id": 1})]
    
    def send_main_keyboard(self, user_id, message="Выберите опцию:"):
        return self.bot.send_message(user_id, message, reply_markup=self.main_keyboard)
    
    def save_feedback(self, user_id, text):
        feedback_document = {
            "user_id": user_id,
            "text": text,
        }
        self.feedback_collection.insert_one(feedback_document)
