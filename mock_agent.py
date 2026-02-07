import time
import sys


def mock_agent():
    print("Starting Mock Agent...")
    time.sleep(1)
    print("Task: Analyze the codebase.")
    time.sleep(1)
    print("Thinking: I need to scan the directory structure.")
    time.sleep(1)
    print("Tool Call: list_files(path='.')")
    time.sleep(2)
    print("Files found: ['main.py', 'utils.py']")
    time.sleep(1)
    print("Thinking: Now I should read main.py.")
    time.sleep(1)
    print("Tool Call: read_file(path='main.py')")
    time.sleep(2)
    print("Content read.")
    time.sleep(1)
    print("Decision: The code looks good.")
    time.sleep(1)
    print("Done.")


if __name__ == "__main__":
    mock_agent()
