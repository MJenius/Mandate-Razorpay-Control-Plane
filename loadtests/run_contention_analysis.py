"""Print the Locust command for each requested contention profile."""

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", default="100,200,500")
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    for users in map(int, args.concurrency.split(",")):
        command = ["locust", "-f", "loadtests/locustfile.py", "--headless", "-u", str(users), "-r", str(users), "-t", "30s", "--host", args.host]
        print(" ".join(command))
        if subprocess.run(command, check=False).returncode:
            sys.exit(1)


if __name__ == "__main__":
    main()
