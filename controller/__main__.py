"""
    Command line script: main function
"""

from controller.app import Application


def main():
    Application.load_projectrc()
    controller = Application()
    controller.app()


if __name__ == "__main__":
    main()
