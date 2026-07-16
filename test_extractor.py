from memory_extractor import MemoryExtractor


extractor = MemoryExtractor()


result = extractor.extract(
"""
User:

Ich spiele seit ich 10 bin Gitarre.
Ich programmiere hauptsächlich Python.
Mein Lieblingsbuch ist Das Parfum von Patrick Süskind.
"""
)


print(result)