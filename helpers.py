import sys
import types



def install_dummy_ollama():
    if "ollama" in sys.modules:
        return sys.modules["ollama"]

    module = types.ModuleType("ollama")

    def _vector_for(text):
        text = str(text).casefold()

        if any(token in text for token in ("metallica", "favorite band", "favourite band", "lieblingsband")):
            return [1.0, 0.0, 0.0]

        if any(token in text for token in ("gitarre", "gitarren", "instrument", "guitar")):
            return [0.0, 1.0, 0.0]

        if any(token in text for token in ("python", "code", "programmiersprache")):
            return [0.0, 0.0, 1.0]

        if any(token in text for token in ("github", "repository", "branch")):
            return [0.5, 0.0, 0.5]

        return [0.2, 0.2, 0.2]

    def embeddings(model, prompt):
        return {"embedding": _vector_for(prompt)}

    def chat(model, messages):
        return {"message": {"content": "{}"}}

    module.embeddings = embeddings
    module.chat = chat
    sys.modules["ollama"] = module
    return module
