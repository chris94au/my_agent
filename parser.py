import json
import re


class ToolParser:


    def parse(self, text):

        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )


        if not match:
            return None


        try:

            return json.loads(
                match.group()
            )

        except json.JSONDecodeError:

            return None