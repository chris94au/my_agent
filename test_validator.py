from memory_validator import MemoryValidator


validator = MemoryValidator()


tests = [

{
"category":"skill",
"key":"programming_language",
"value":"Python",
"importance":8
},


{
"category":"state",
"key":"current_food",
"value":"Pizza",
"importance":5
},


{
"category":"interest",
"key":"favorite_book",
"value":"Das Parfum von Patrick Süskind",
"importance":7
}

]


for test in tests:

    print(test)

    result = validator.validate(test)

    print(result)
    print()