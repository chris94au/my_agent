class Tool:


    def __init__(self, name, description, function):

        self.name = name
        self.description = description
        self.function = function



    def execute(self, input_data):

        return self.function(input_data)



class ToolManager:


    def __init__(self):

        self.tools = {}



    def register(self, tool):

        self.tools[tool.name] = tool



    def get(self, name):

        return self.tools.get(name)



    def list_tools(self):

        return list(self.tools.values())



    def get_descriptions(self):

        text = ""

        for tool in self.tools.values():

            text += (
                f"{tool.name}: "
                f"{tool.description}\n"
            )

        return text