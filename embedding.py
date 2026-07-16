import ollama


class Embedding:

    def __init__(
        self,
        model="nomic-embed-text"
    ):
        self.model = model


    def create(
        self,
        text
    ):

        response = ollama.embeddings(
            model=self.model,
            prompt=text
        )

        return response["embedding"]