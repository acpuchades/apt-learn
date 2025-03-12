#!/usr/bin/env python3

from atp import ATP, TournamentRef

import asyncio
from aiohttp import ClientSession

async def main():
    atp = ATP()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0'
    }

    async with ClientSession(headers=headers) as session:
        tref = TournamentRef(id=336, slug='hong-kong')
        print(await atp.get_tournament_singles_results(session, tref, 2024))

asyncio.run(main())