from datetime import datetime

from typing import Dict, List, NamedTuple, Tuple, Optional
from aiohttp import ClientSession

from lxml import html

class PlayerRef(NamedTuple):
    id: str
    slug: str

class TournamentRef(NamedTuple):
    id: str
    slug: str

class MatchRef(NamedTuple):
    tournament_id: str
    year: int
    match_id: str

class RankingEntry(NamedTuple):
    rank: int
    player_name: str
    player_ref: PlayerRef
    player_age: int
    points: int
    points_move: str
    tournaments_played: int
    dropping: int
    next_best: int

class TournamentEvent(NamedTuple):
    tournament_name: str
    tournament_ref: TournamentRef
    location: str
    date: str
    team_winner: Optional[str]
    singles_winner: Optional[PlayerRef]
    doubles_winners: Optional[Tuple[PlayerRef, PlayerRef]]

class MatchResult(NamedTuple):
    match_ref: MatchRef
    date: datetime.date
    duration: int
    best_of: int
    winner: PlayerRef
    loser: PlayerRef
    w1: Optional[int]
    w1_tb: Optional[int]
    w2: Optional[int]
    w2_tb: Optional[int]
    w3: Optional[int]
    w3_tb: Optional[int]
    w4: Optional[int]
    w4_tb: Optional[int]
    w5: Optional[int]
    w5_tb: Optional[int]
    l1: Optional[int]
    l1_tb: Optional[int]
    l2: Optional[int]
    l2_tb: Optional[int]
    l3: Optional[int]
    l3_tb: Optional[int]
    l4: Optional[int]
    l4_tb: Optional[int]
    l5: Optional[int]
    l5_tb: Optional[int]

class SetStats(NamedTuple):
    duration: int
    df: int
    aces: int
    svpt: int
    fst_srv: int
    fst_srv_won: int
    snd_srv_won: int
    fst_srv_ret_won: int
    snd_srv_ret_won: int
    bp_saved: int
    total_svc_won: int
    total_ret_won: int
    total_pts_won: int

class MatchStats(NamedTuple):
    match_ref: MatchRef
    duration: int
    sets_played: int
    winner_stats: List[SetStats]
    loser_stats: List[SetStats]

class PlayerDetails(NamedTuple):
    first_name: str
    mid_initial: str
    last_name: str
    birth_place: str
    nationality: str
    residence: str
    coach: str
    date_of_birth: datetime.date
    height_in: int
    height_ft: str
    height_cm: int
    weight_lb: int
    weight_kg: int
    playhand: str
    backhand: str
    pro_year: int
    social_links: Dict[str, str]

class ATP:

    BASE_URL = 'https://www.atptour.com/en'

    async def get_player_details(self, session: ClientSession, player_ref: PlayerRef) -> PlayerDetails:
        async with session.get(f'{self.BASE_URL}/-/www/players/hero/{player_ref.id}', params={'v': 1}) as response:
            data = await response.json()
            return PlayerDetails(first_name=data['FirstName'], mid_initial=data['MidInitial'],
                                 last_name=data['LastName'], birth_place=data['BirthCity'],
                                 nationality=data['Nationality'], residence=data['Residence'],
                                 coach=data['Coach'],
                                 date_of_birth=datetime.fromisoformat(data['BirthDate']).date(),
                                 height_in=data['HeightIn'], height_ft=data['HeightFt'], height_cm=data['HeightCm'],
                                 weight_lb=data['WeightLb'], weight_kg=data['WeightKg'],
                                 playhand=data['PlayHand']['Description'], backhand=data['BackHand']['Description'],
                                 pro_year=data['ProYear'], social_links={
                                    link['SocialId']: link['SocialLink'] for link in data['SocialLinks']
                                 })

    async def get_tournaments(self, session: ClientSession, year: int=None) -> List[TournamentEvent]:
        params = {}
        if year is not None:
            params['year'] = year

        async with session.get(f'{self.BASE_URL}/scores/results-archive', params=params) as response:
            entries = []
            doctree = html.fromstring(await response.read())
            tournament_list = doctree.xpath('//div[contains(@class, "tournament-list")]')[0]
            for li in tournament_list.xpath('ul/li'):
                tournament_link = li.xpath('.//a[@class="tournament__profile"]')[0]
                tournament_href = tournament_link.get('href')
                name = li.xpath('.//div[@class="top"]/span[@class="name"]')[0].text_content().strip()
                location = li.xpath('.//div[@class="bottom"]/span[@class="venue"]')[0].text_content().strip().rstrip(' |')
                date = li.xpath('.//div[@class="bottom"]/span[@class="Date"]')[0].text_content().strip()

                team_winner, singles_winner, doubles_winners = None, None, None
                for w in li.xpath('.//dl[@class="winner"]'):
                    match w.xpath('dt/text()')[0]:
                        case 'Team Winner':
                            w_name = w.xpath('dd/text()')
                            if len(w_name) == 1:
                                team_winner = w_name[0].strip()

                        case 'Singles Winner':
                            w_href = w.xpath('dd/a/@href')
                            w_name = w.xpath('dd/a/text()')
                            if len(w_name) != 1:
                                continue
                            singles_winner = PlayerRef(id=w_href[0].split('/')[4],
                                                       slug=w_href[0].split('/')[3])

                        case 'Doubles Winners':
                            w_hrefs = w.xpath('dd/a/@href')
                            w_names = w.xpath('dd/a/text()')
                            if len(w_names) != 2:
                                continue
                            w1_ref = PlayerRef(id=w_hrefs[0].split('/')[4],
                                               slug=w_hrefs[0].split('/')[3])
                            w2_ref = PlayerRef(id=w_hrefs[1].split('/')[4],
                                               slug=w_hrefs[1].split('/')[3])
                            doubles_winners = w1_ref, w2_ref

                entries.append(TournamentEvent(tournament_name=name, tournament_ref=TournamentRef(
                                                   id=int(tournament_href.split('/')[4]),
                                                   slug=tournament_href.split('/')[3]
                                               ),
                                               location=location, date=date, team_winner=team_winner,
                                               singles_winner=singles_winner, doubles_winners=doubles_winners))
            return entries

    async def get_tournament_singles_results(self, session: ClientSession, tournament: TournamentRef, year: int) -> List[MatchResult]:
        tournament_id, tournament_slug = tournament.id, tournament.slug
        async with session.get(f'{self.BASE_URL}/scores/archive/-/{tournament_id}/{year}/results') as response:
            doctree = html.fromstring(await response.read())
            accordion = doctree.xpath('//div[@class="atp_accordion-items"]')[0]

            entries = []
            for tday in accordion.xpath('.//div[@class="atp_accordion-item"]'):
                date = tday.xpath('.//div[@class="tournament-day"]/h4/text()')[0].strip()
                date = datetime.strptime(date, '%a, %d %B, %Y').date()

                stats_href = tday.xpath('.//div[@class="match-cta"]/a[text()="Stats"]/@href')
                match_ref = MatchRef(tournament_id=tournament.id, year=year,
                                     match_id=stats_href[0].split('/')[-1])

                for match in tday.xpath('.//div[@class="match"]'):
                    duration = match.xpath('.//div[@class="match-header"]/span[2]/text()')
                    duration = duration[0].strip() if len(duration) == 1 else None
                    if duration is not None:
                        dur_hrs, dur_mins, _ = map(int, duration.split(':'))
                        duration = dur_hrs * 60 + dur_mins

                    players, player_sets, player_tbs, winner_idx = [], [], [], None
                    for i, player_info in enumerate(match.xpath('.//div[@class="stats-item"]')):
                        player_href = player_info.xpath('.//div[@class="name"]/a/@href')[0]
                        players.append(PlayerRef(id=player_href.split('/')[4],
                                                 slug=player_href.split('/')[3]))

                        sets, tiebreaks = [], []
                        for score_item in player_info.xpath('.//div[@class="score-item"]'):
                            scores = score_item.xpath('span/text()')
                            match len(scores):
                                case 1:
                                    sets.append(int(scores[0]))
                                    tiebreaks.append(None)
                                case 2:
                                    sets.append(int(scores[0]))
                                    tiebreaks.append(int(scores[1]))
                        player_sets.append(sets)
                        player_tbs.append(tiebreaks)

                        if player_info.xpath('.//div[@class="winner"]'):
                            winner_idx = i

                    if len(players) != 2 or winner_idx is None:
                        continue

                    sets_played, winner_won_sets = 0, 0
                    for wset, lset, wtbs in zip(player_sets[winner_idx],
                                                player_sets[1-winner_idx],
                                                player_tbs[winner_idx]):
                        winner_won_sets += wset >= lset or wtbs is not None
                        sets_played += 1

                    entries.append(MatchResult(match_ref=match_ref, date=date, duration=duration,
                                               best_of=3 if winner_won_sets == 2 else 5,
                                               winner=players[winner_idx], loser=players[1-winner_idx],
                                               w1=player_sets[winner_idx][0] if sets_played >= 1 else None,
                                               w1_tb=player_tbs[winner_idx][0] if sets_played >= 1 else None,
                                               w2=player_sets[winner_idx][1] if sets_played >= 2 else None,
                                               w2_tb=player_tbs[winner_idx][1] if sets_played >= 2 else None,
                                               w3=player_sets[winner_idx][2] if sets_played >= 3 else None,
                                               w3_tb=player_tbs[winner_idx][2] if sets_played >= 3 else None,
                                               w4=player_sets[winner_idx][3] if sets_played >= 4 else None,
                                               w4_tb=player_tbs[winner_idx][3] if sets_played >= 4 else None,
                                               w5=player_sets[winner_idx][4] if sets_played >= 5 else None,
                                               w5_tb=player_tbs[winner_idx][4] if sets_played >= 5 else None,
                                               l1=player_sets[1-winner_idx][0] if sets_played >= 1 else None,
                                               l1_tb=player_tbs[1-winner_idx][0] if sets_played >= 1 else None,
                                               l2=player_sets[1-winner_idx][1] if sets_played >= 2 else None,
                                               l2_tb=player_tbs[1-winner_idx][1] if sets_played >= 2 else None,
                                               l3=player_sets[1-winner_idx][2] if sets_played >= 3 else None,
                                               l3_tb=player_tbs[1-winner_idx][2] if sets_played >= 3 else None,
                                               l4=player_sets[1-winner_idx][3] if sets_played >= 4 else None,
                                               l4_tb=player_tbs[1-winner_idx][3] if sets_played >= 4 else None,
                                               l5=player_sets[1-winner_idx][4] if sets_played >= 5 else None,
                                               l5_tb=player_tbs[1-winner_idx][4] if sets_played >= 5 else None))
            return entries

    def _extract_set_stats(self, data: Dict[str, str]) -> SetStats:
        pass

    async def get_match_singles_stats(self, session: ClientSession, match: MatchRef) -> MatchStats:
        year, tournament_id, match_id = match.year, match.tournament_id, match.match_id
        async with session.get(f'{self.BASE_URL}/-/Hawkeye/MatchStats/Complete/{year}/{tournament_id}/{match_id}') as response:
            data = await response.json()

            duration = data['Match']['MatchTimeTotal']
            dur_hrs, dur_mins, _ = duration.split(':')
            duration = dur_hrs * 60 + dur_mins

            sets_played = data['Match']['NumberOfSets']

            winner_id = data['Match']['Winner']
            player = data['Match']['PlayerTeam']
            opponent = data['Match']['OpponentTeam']

            pass

    async def get_ranking_weeks(self, session, type='singles') -> List[str]:
        async with session.get(f'{self.BASE_URL}/rankings/{type}') as response:
            doctree = html.fromstring(await response.read())
            dropdown = doctree.xpath('//div[@data-key="DateWeek"]/*[@class="dropdown"]/ul')[0]
            return [ date_week.get('data-value') for date_week in dropdown.xpath('li/a') ]

    async def get_ranking_regions(self, session, type='singles') -> Dict[str, str]:
        async with session.get(f'{self.BASE_URL}/rankings/{type}') as response:
            doctree = html.fromstring(await response.read())
            dropdown = doctree.xpath('//div[@data-key="Region"]/*[@class="dropdown"]/ul')[0]
            return {
                region.text_content().strip(): region.get('data-value')
                    for region in dropdown.xpath('li/a')
            }

    async def get_singles_rankings(self, session, week=None, region=None, ranking_start=None,
                                   ranking_end=None) -> List[RankingEntry]:
        params = {}
        ranking_start = ranking_start or 0
        ranking_end = ranking_end or ranking_start + 100
        params['RankRange'] = f'{ranking_start}-{ranking_end}'
        if region is not None:
            params['Region'] = region
        if week is not None:
            params['DateWeek'] = week

        async with session.get(f'{self.BASE_URL}/rankings/singles', params=params) as response:
            entries = []
            doctree = html.fromstring(await response.read())
            for tr in doctree.xpath('.//table[contains(@class, "desktop-table")]/tbody/tr'):
                rank = tr.xpath('td[contains(@class, "rank")]')
                if not rank:
                    continue
                rank = int(rank[0].text_content())
                player = tr.xpath('td[contains(@class, "player")]//li[contains(@class, "name")]')
                player_name = player[0].text_content().strip()
                player_link = player[0].xpath('a/@href')[0]
                player_slug = player_link.split('/')[3]
                player_id = player_link.split('/')[4]
                age = int(tr.xpath('td[contains(@class, "age")]')[0].text_content().strip())
                points = tr.xpath('td[contains(@class, "points")]')[0].text_content().strip()
                points = int(points.replace(',', ''))
                points_move = tr.xpath('td[contains(@class, "pointsMove")]')[0].text_content().strip()
                tournaments = int(tr.xpath('td[contains(@class, "tourns")]/text()')[0].strip())
                dropping = tr.xpath('td[contains(@class, "drop")]/text()')[0].strip()
                dropping = int(dropping) if dropping != '-' else 0
                next_best = tr.xpath('td[contains(@class, "best")]/text()')[0].strip()
                next_best = int(next_best) if next_best != '-' else 0
                entries.append(RankingEntry(rank=rank, player=PlayerRef(player_id, player_slug, player_name),
                                            player_age=age, points=points, points_move=points_move,
                                            tournaments_played=tournaments, dropping=dropping,
                                            next_best=next_best))
        return entries