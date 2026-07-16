from embedding import Embedding


embedder = Embedding()


vector = embedder.create(
    "Metallica ist meine Lieblingsband"
)


print(
    len(vector)
)

print(
    vector[:10]
)