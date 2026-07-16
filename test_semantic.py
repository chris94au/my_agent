from memory import Memory


memory = Memory()


results = memory.semantic_search(
    "Welche Musik könnte mir gefallen?"
)


for r in results:
    print(r)