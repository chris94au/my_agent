class Conversation:


    def __init__(self, system_prompt):

        self.messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]



    def add_user(self, content):

        self.messages.append(
            {
                "role": "user",
                "content": content
            }
        )



    def add_assistant(self, content):

        self.messages.append(
            {
                "role": "assistant",
                "content": content
            }
        )



    def get_messages(self):

        return self.messages
    
    def add_system(self, content):

        self.messages.append(
            {
                "role": "system",
                "content": content
            }
        )