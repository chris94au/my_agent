import argparse
import logging

from agent import Agent


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)


def run_cli():
    agent = Agent()

    print("Agent gestartet. 'exit' zum Beenden.")

    while True:
        user_input = input("\nDu: ")
        if user_input.lower() == "exit":
            break
        answer = agent.think(user_input)
        print("\nAgent:")
        print(answer)



def run_gui():
    from gui.app import launch

    app, window = launch()
    return app.exec()



def main():
    parser = argparse.ArgumentParser(description="Lokaler AI-Agent")
    parser.add_argument("--gui", action="store_true", help="Desktop-GUI starten")
    parser.add_argument("--cli", action="store_true", help="Konsolenmodus starten")
    args = parser.parse_args()

    if args.gui:
        run_gui()
    else:
        run_cli()


if __name__ == "__main__":
    main()
