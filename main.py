from agent import Agent


def main():

    agent = Agent()

    print("Agent gestartet. 'exit' zum Beenden.")

    while True:

        user_input = input("\nDu: ")

        if user_input.lower() == "exit":
            break

        answer = agent.think(user_input)

        print("\nAgent:")
        print(answer)



if __name__ == "__main__":
    main()