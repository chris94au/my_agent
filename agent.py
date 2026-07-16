import ollama

from tools import tool_manager
from tool_executor import ToolExecutor
from prompts import create_system_prompt
from parser import ToolParser
from conversation import Conversation
from memory import Memory
from memory_extractor import MemoryExtractor
from memory_validator import MemoryValidator
from normalizer import Normalizer


class Agent:


    def __init__(self, model="qwen2.5:7b"):

        self.model = model

        self.executor = ToolExecutor()

        self.parser = ToolParser()

        self.memory = Memory()

        self.memory_extractor = MemoryExtractor()

        self.memory_validator = MemoryValidator()

        self.normalizer = Normalizer()

        self.system_prompt = create_system_prompt(
            tool_manager
        )

        self.conversation = Conversation(
            self.system_prompt
        )


    def think(self, user_input):
    

        if user_input.startswith("memory test"):

            self.memory.save_fact(
                "test",
                "funktioniert"
            )

            return str(
                self.memory.get_all_facts()
            )


        self.conversation.add_user(
            user_input
        )

        memory_context = self.memory.get_semantic_context(
            user_input
        )


        self.conversation.add_system(
            memory_context
        )

        response = ollama.chat(
            model=self.model,
            messages=self.conversation.get_messages()
        )


        answer = response["message"]["content"]


        print("DEBUG:", answer)


        tool_call = self.parser.parse(
            answer
        )



        if tool_call and "tool" in tool_call:


            tool_name = tool_call["tool"]


            print(
                "TOOL ERKANNT:",
                tool_name
            )



            if "input" in tool_call:

                tool_input = tool_call["input"]


            else:

                tool_input = {
                    key: value
                    for key, value in tool_call.items()
                    if key != "tool"
                }



            success, result = self.executor.execute(
                tool_name,
                tool_input
            )


            if not success:

                return result



            print(
                "TOOL RESULT:",
                result
            )



            self.conversation.add_assistant(
                f"Ich habe das Werkzeug '{tool_name}' verwendet."
            )


            self.conversation.add_user(
                f"""
                Das Werkzeug wurde ausgeführt.

                Werkzeug:
                {tool_name}

                Ergebnis:
                {result}

                Beantworte jetzt die ursprüngliche Benutzeranfrage.
                Antworte nur mit normalem Text.
                Erzeuge kein JSON.
                """
            )



            final = ollama.chat(
                model=self.model,
                messages=self.conversation.get_messages()
            )


            final_answer = final["message"]["content"]


            self.conversation.add_assistant(
                final_answer
            )


            return final_answer



        self.conversation.add_assistant(
            answer
        )


        conversation_text = f"""
        User:
        {user_input}

        Assistant:
        {answer}
        """


        self.update_memory(
            conversation_text
        )


        return answer
        
    
    def update_memory(self, conversation_text):

        memories = self.memory_extractor.extract(
            conversation_text
        )


        if not memories:
            return
        
        for memory in memories:
            memory = self.normalizer.normalize(
                memory
            )


        for memory in memories:


            validation = self.memory_validator.validate(
                memory
            )


            if not validation:
                continue



            if not validation.get(
                "approved",
                False
            ):
                print(
                    "MEMORY REJECTED:",
                    memory
                )
                continue



            importance = validation.get(
                "importance",
                memory.get(
                    "importance",
                    5
                )
            )


            status=self.memory.save_fact(
                    key=memory["key"],
                    value=memory["value"],
                    category=memory.get(
                        "category",
                        "general"
                    ),
                    importance=importance
                )


            print(
                "MEMORY:",
                status
            )
