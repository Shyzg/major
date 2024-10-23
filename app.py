from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout
)
from colorama import *
from datetime import datetime, timedelta
from fake_useragent import FakeUserAgent
from faker import Faker
from urllib.parse import parse_qs
import asyncio, json, os, re, sys

class Major:
    def __init__(self) -> None:
        self.faker = Faker()
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Host': 'major.bot',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': FakeUserAgent().random
        }

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_timestamp(self, message):
        print(
            f"{Fore.BLUE + Style.BRIGHT}[ {datetime.now().astimezone().strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{message}",
            flush=True
        )

    def process_queries(self, lines_per_file: int):
        if not os.path.exists('queries.txt'):
            raise FileNotFoundError(f"File 'queries.txt' not found. Please ensure it exists.")

        queries = [line.strip() for line in open('queries.txt', 'r') if line.strip()]
        if not queries:
            raise ValueError("File 'queries.txt' is empty.")

        existing_queries = set()
        for file in os.listdir():
            if file.startswith('queries-') and file.endswith('.txt'):
                existing_queries.update(line.strip() for line in open(file, 'r') if line.strip())

        new_queries = [query for query in queries if query not in existing_queries]
        if not new_queries:
            self.print_timestamp(f"{Fore.YELLOW + Style.BRIGHT}[ No New Queries To Add ]{Style.RESET_ALL}")
            return

        files = [f for f in os.listdir() if f.startswith('queries-') and f.endswith('.txt')]
        files.sort(key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0)

        last_file_number = int(re.findall(r'\d+', files[-1])[0]) if files else 0

        for i in range(0, len(new_queries), lines_per_file):
            chunk = new_queries[i:i + lines_per_file]
            if files and len(open(files[-1], 'r').readlines()) < lines_per_file:
                with open(files[-1], 'a') as outfile:
                    outfile.write('\n'.join(chunk) + '\n')
                self.print_timestamp(f"{Fore.GREEN + Style.BRIGHT}[ Updated '{files[-1]}' ]{Style.RESET_ALL}")
            else:
                last_file_number += 1
                queries_file = f"queries-{last_file_number}.txt"
                with open(queries_file, 'w') as outfile:
                    outfile.write('\n'.join(chunk) + '\n')
                self.print_timestamp(f"{Fore.GREEN + Style.BRIGHT}[ Generated '{queries_file}' ]{Style.RESET_ALL}")

    def load_queries(self, file_path):
        return [line.strip() for line in open(file_path, 'r') if line.strip()]

    async def generate_token(self, query: str):
        url = 'https://major.bot/api/auth/tg/'
        data = json.dumps({'init_data':query})
        headers = {
            **self.headers,
            'Content-Length': str(len(data)),
            'Content-Type': 'application/json'
        }
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.post(url, headers=headers, data=data, ssl=False) as response:
                    response.raise_for_status()
                    generate_token = await response.json()
                    user_data = json.loads(parse_qs(query)['user'][0])
                    id = user_data['id']
                    first_name = user_data['first_name'] or user_data['username']
                    return (generate_token['access_token'], id, first_name)
        except (Exception, ClientResponseError) as e:
            self.print_timestamp(
                f"{Fore.YELLOW + Style.BRIGHT}[ Failed To Process {query} ]{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.RED + Style.BRIGHT}[ {str(e)} ]{Style.RESET_ALL}"
            )
            return None

    async def generate_tokens(self, queries):
        tasks = [self.generate_token(query) for query in queries]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result is not None]

    async def visit(self, token: str):
        url = 'https://major.bot/api/user-visits/visit/'
        headers = {
            **self.headers,
            'Authorization': f"Bearer {token}",
            'Content-Length': '0'
        }
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.post(url=url, headers=headers, ssl=False) as response:
                    if response.status in [500, 503, 520]:
                        return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ Server Major Down While Daily Visit ]{Style.RESET_ALL}")
                    response.raise_for_status()
                    visit = await response.json()
                    if visit['is_increased']:
                        if visit['is_allowed']:
                            return self.print_timestamp(f"{Fore.GREEN + Style.BRIGHT}[ Claimed Daily Visit ]{Style.RESET_ALL}")
                        return self.print_timestamp(f"{Fore.YELLOW + Style.BRIGHT}[ Subscribe Major Community To Claim Your Daily Visit Bonus And Increase Your Streak ]{Style.RESET_ALL}")
                    return self.print_timestamp(f"{Fore.YELLOW + Style.BRIGHT}[ Daily Visit Already Claimed ]{Style.RESET_ALL}")
        except ClientResponseError as e:
            return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An HTTP Error Occurred While Daily Visit: {str(e)} ]{Style.RESET_ALL}")
        except Exception as e:
            return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Unexpected Error Occurred While Daily Visit: {str(e)} ]{Style.RESET_ALL}")

    async def streak(self, token: str):
        url = 'https://major.bot/api/user-visits/streak/'
        headers = {
            **self.headers,
            'Authorization': f"Bearer {token}"
        }
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.get(url=url, headers=headers, ssl=False) as response:
                    if response.status in [500, 503, 520]:
                        self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ Server Major Down While Fetching Streak ]{Style.RESET_ALL}")
                        return None
                    response.raise_for_status()
                    return await response.json()
        except ClientResponseError as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An HTTP Error Occurred While Fetching Streak: {str(e)} ]{Style.RESET_ALL}")
            return None
        except Exception as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Unexpected Error Occurred While Fetching Streak: {str(e)} ]{Style.RESET_ALL}")
            return None

    async def user(self, token: str, id: str):
        url = f'https://major.bot/api/users/{id}/'
        headers = {
            **self.headers,
            'Authorization': f"Bearer {token}"
        }
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.get(url=url, headers=headers, ssl=False) as response:
                    if response.status in [500, 503, 520]:
                        self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ Server Major Down While Fetching User ]{Style.RESET_ALL}")
                        return None
                    response.raise_for_status()
                    return await response.json()
        except ClientResponseError as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An HTTP Error Occurred While Fetching User: {str(e)} ]{Style.RESET_ALL}")
            return None
        except Exception as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Unexpected Error Occurred While Fetching User: {str(e)} ]{Style.RESET_ALL}")
            return None

    async def tasks(self, token: str, type: str):
        url = f'https://major.bot/api/tasks/?is_daily={type}'
        headers = {
            **self.headers,
            'Authorization': f"Bearer {token}"
        }
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.get(url=url, headers=headers, ssl=False) as response:
                    if response.status in [500, 503, 520]:
                        self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ Server Major Down While Fetching Tasks ]{Style.RESET_ALL}")
                        return None
                    response.raise_for_status()
                    return await response.json()
        except ClientResponseError as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An HTTP Error Occurred While Fetching Tasks: {str(e)} ]{Style.RESET_ALL}")
            return None
        except Exception as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Unexpected Error Occurred While Fetching Tasks: {str(e)} ]{Style.RESET_ALL}")
            return None

    async def complete_task(self, token: str, task_title: str, task_award: int, payload: dict):
        url = 'https://major.bot/api/tasks/'
        data = json.dumps(payload)
        headers = {
            **self.headers,
            'Authorization': f"Bearer {token}",
            'Content-Length': str(len(data)),
            'Content-Type': 'application/json'
        }
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                    if response.status in [500, 503, 520]:
                        return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ Server Major Down While Complete Tasks ]{Style.RESET_ALL}")
                    response.raise_for_status()
                    complete_task = await response.json()
                    if complete_task['is_completed']:
                        return self.print_timestamp(f"{Fore.GREEN + Style.BRIGHT}[ You\'ve Got {task_award} $MAJOR From {task_title} ]{Style.RESET_ALL}")
                    return self.print_timestamp(f"{Fore.YELLOW + Style.BRIGHT}[ {task_title} Isn\'t Completed ]{Style.RESET_ALL}")
        except ClientResponseError as e:
            return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An HTTP Error Occurred While Complete Tasks: {str(e)} ]{Style.RESET_ALL}")
        except Exception as e:
            return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Unexpected Error Occurred While Complete Tasks: {str(e)} ]{Style.RESET_ALL}")

    async def answer(self):
        url = 'https://raw.githubusercontent.com/Shyzg/answer/refs/heads/main/answer.json'
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.get(url=url, ssl=False) as response:
                    response.raise_for_status()
                    return json.loads(await response.text())
        except ClientResponseError as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An HTTP Error Occurred While Get Task Answer: {str(e)} ]{Style.RESET_ALL}")
            return None
        except Exception as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Unexpected Error Occurred While Get Task Answer: {str(e)} ]{Style.RESET_ALL}")
            return None

    async def main(self):
        while True:
            try:
                queries = [line.strip() for line in open('queries.txt') if line.strip()]
                accounts = await self.generate_tokens(queries=queries)
                total_rating = 0

                for (token, id, name) in accounts:
                    self.print_timestamp(
                        f"{Fore.WHITE + Style.BRIGHT}[ Information ]{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.CYAN + Style.BRIGHT}[ {name} ]{Style.RESET_ALL}"
                    )
                    await self.visit(token=token)
                    await asyncio.sleep(3)
                    streak = await self.streak(token=token)
                    await asyncio.sleep(3)
                    user = await self.user(token=token, id=id)
                    await asyncio.sleep(3)
                    if user is not None and streak is not None:
                        self.print_timestamp(
                            f"{Fore.GREEN + Style.BRIGHT}[ {user['rating']} $MAJOR ]{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                            f"{Fore.BLUE + Style.BRIGHT}[ Streak {streak['streak']} ]{Style.RESET_ALL}"
                        )
                        total_rating += user['rating']

                for (token, id, name) in accounts:
                    self.print_timestamp(
                        f"{Fore.WHITE + Style.BRIGHT}[ Earn ]{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.CYAN + Style.BRIGHT}[ {name} ]{Style.RESET_ALL}"
                    )
                    for type in ['true', 'false']:
                        tasks = await self.tasks(token=token, type=type)
                        await asyncio.sleep(3)
                        if tasks is not None:
                            for task in tasks:
                                if not task['is_completed']:
                                    if task['type'] == 'code':
                                        answer = await self.answer()
                                        if answer is not None:
                                            if task['title'] in answer['major']['youtube']:
                                                code = answer['major']['youtube'][task['title']]
                                                await self.complete_task(token=token, task_title=task['title'], task_award=task['award'], payload={'task_id':task['id'],'payload':{'code':code}})
                                                await asyncio.sleep(3)
                                    else:
                                        await self.complete_task(token=token, task_title=task['title'], task_award=task['award'], payload={'task_id':task['id']})
                                        await asyncio.sleep(3)

                self.print_timestamp(
                    f"{Fore.CYAN + Style.BRIGHT}[ Total Account {len(accounts)} ]{Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                    f"{Fore.GREEN + Style.BRIGHT}[ Total Rating {total_rating} $MAJOR ]{Style.RESET_ALL}"
                )

                sleep_timestamp = (datetime.now().astimezone() + timedelta(seconds=3600)).strftime('%X %Z')
                self.print_timestamp(f"{Fore.CYAN + Style.BRIGHT}[ Restarting At {sleep_timestamp} ]{Style.RESET_ALL}")

                await asyncio.sleep(3600)
                self.clear_terminal()
            except Exception as e:
                self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ {str(e)} ]{Style.RESET_ALL}")
                continue

if __name__ == '__main__':
    try:
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        init(autoreset=True)
        major = Major()

        asyncio.run(major.main())
    except (ValueError, IndexError, FileNotFoundError) as e:
        major.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ {str(e)} ]{Style.RESET_ALL}")
    except KeyboardInterrupt:
        sys.exit(0)