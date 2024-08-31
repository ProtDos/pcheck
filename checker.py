import asyncio
from typing import Any
import aiohttp
import re
import time
import sys
import argparse


parser = argparse.ArgumentParser(description='Test and save working proxies.')
parser.add_argument('-i', '--input', type=str, required=True, help='Path to the input file containing proxies.')
parser.add_argument('-o', '--output', type=str, required=True, help='Path to the output file to save working proxies.')
parser.add_argument('-u', '--url', type=str, default='http://httpbin.org/ip', help='URL to test proxies against.')
parser.add_argument('-t', '--timeout', type=int, default=5, help='Timeout for proxy requests in seconds.')

args = parser.parse_args()

INPUT_FILE: str = args.input
OUTPUT_FILE: str = args.output
TEST_URL: str = args.url
TIMEOUT: int = args.timeout


def return_unique() -> list:
    lines_seen = set()
    unique = []
    for line in open(INPUT_FILE, "r"):
        if line not in lines_seen:
            unique.append(line)
            lines_seen.add(line)
    return unique


def parse_proxy(proxy: str) -> dict[str, str | int | Any] | dict[str, str | int | Any] | None:
    """Parse the proxy string and return a dictionary with the proxy details."""
    # Regex to detect format
    match1 = re.match(r'^(http://)?([^:]+):([^:]+):([^:]+):([^@]+)$', proxy)
    match2 = re.match(r'^(http://)?([^:]+):([^@]+)@([^:]+):([^/]+)$', proxy)

    if match1:
        return {
            'scheme': 'http',
            'host': match1.group(2),
            'port': int(match1.group(3)),
            'username': match1.group(4),
            'password': match1.group(5)
        }
    elif match2:
        return {
            'scheme': 'http',
            'host': match2.group(4),
            'port': int(match2.group(5)),
            'username': match2.group(2),
            'password': match2.group(3)
        }
    else:
        return None


async def check_proxy(session: aiohttp.ClientSession, proxy: str) -> tuple[str, bool]:
    """Check if the proxy is working."""
    proxy_info = parse_proxy(proxy)
    if proxy_info is None:
        return proxy, False

    proxy_url = f"http://{proxy_info['username']}:{proxy_info['password']}@{proxy_info['host']}:{proxy_info['port']}"
    try:
        async with session.get(TEST_URL, proxy=proxy_url, timeout=TIMEOUT) as response:
            return proxy, response.status == 200
    except Exception:
        return proxy, False


async def main() -> None:
    """Main function to handle proxy checking and reporting."""
    proxies = return_unique()

    total_proxies = len(proxies)
    working_proxies = []
    invalid_proxies = []

    async with aiohttp.ClientSession() as session:
        tasks = [check_proxy(session, proxy) for proxy in proxies]

        start_time = time.time()
        completed_tasks = 0
        working_count = 0
        invalid_count = 0

        for future in asyncio.as_completed(tasks):
            proxy, is_working = await future
            completed_tasks += 1
            if is_working:
                working_proxies.append(proxy)
                working_count += 1
            else:
                invalid_proxies.append(proxy)
                invalid_count += 1

            elapsed_time = time.time() - start_time
            checks_per_second = completed_tasks / elapsed_time if elapsed_time > 0 else 0
            remaining = total_proxies - completed_tasks

            sys.stdout.write(f'\rChecks/s: {checks_per_second:.2f} | '
                             f'Working: {working_count} | '
                             f'Invalid: {invalid_count} | '
                             f'Remaining: {remaining}')
            sys.stdout.flush()

    with open(OUTPUT_FILE, 'w') as f:
        for proxy in working_proxies:
            f.write(proxy + '\n')

    sys.stdout.write('\nCompleted!\n')


if __name__ == '__main__':
    asyncio.run(main())
