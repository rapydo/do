"""
    Command line script: main function
"""

from controller.app import Application


def main():
    Application.load_projectrc()
    Application()


if __name__ == "__main__":
    main()
