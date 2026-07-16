from memory import Memory


memory = Memory()


memory.save_fact(
    key="editor",
    value="VS Code",
    category="preference",
    importance=9
)


print(
    memory.get_all_facts()
)


print(
    memory.get_context()
)