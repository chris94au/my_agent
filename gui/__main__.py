from .app import launch


if __name__ == "__main__":
    app, window = launch()
    window.show()
    raise SystemExit(app.exec())
