# -*- coding: utf-8 -*-
"""
历史赛果拉取 (football-analyzer)
=================================
从 openligadb 拉取完赛赛季逐场数据, 计算最终积分榜排名, 落盘为紧凑 JSON:
  {league, season, league_avg, standings, matches:[{date, round, home, away, hg, ag, hthg, htag, rank_h, rank_a}]}

用法: python fetch_history.py
输出: data/history_<league>_<season>.json
"""
import urllib.request, json, os, sys

API = 'https://api.openligadb.de/getmatchdata/{league}/{season}'
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode('utf-8'))


def final_result(m):
    """取终场比分 (优先 Endergebnis)"""
    for r in m['matchResults']:
        if r['resultName'] == 'Endergebnis':
            return int(r['pointsTeam1']), int(r['pointsTeam2'])
    return None


def halftime_result(m):
    for r in m['matchResults']:
        if r['resultName'] == 'Halbzeit':
            return int(r['pointsTeam1']), int(r['pointsTeam2'])
    return None, None


def build(league, season):
    ms = fetch(API.format(league=league, season=season))
    rows = []
    for m in ms:
        if not m.get('matchIsFinished'):
            continue
        fr = final_result(m)
        if fr is None:
            continue
        hg, ag = fr
        hthg, htag = halftime_result(m)
        rnd = m.get('group', {}).get('groupOrderID') or int(
            m.get('group', {}).get('groupName', '').split()[0] or 0)
        rows.append({
            'date': m['matchDateTime'][:10],
            'round': rnd,
            'home': m['team1']['teamName'],
            'away': m['team2']['teamName'],
            'hg': hg, 'ag': ag,
            'hthg': hthg, 'htag': htag,
        })
    rows.sort(key=lambda x: (x['round'], x['date']))

    # 最终积分榜 (3-1-0, 净胜球决胜)
    pts, gd, gf = {}, {}, {}
    for r in rows:
        for t, scored, conc in ((r['home'], r['hg'], r['ag']), (r['away'], r['ag'], r['hg'])):
            pts[t] = pts.get(t, 0) + (3 if scored > conc else 1 if scored == conc else 0)
            gd[t] = gd.get(t, 0) + scored - conc
            gf[t] = gf.get(t, 0) + scored
    order = sorted(pts, key=lambda t: (-pts[t], -gd[t], -gf[t], t))
    rank = {t: i + 1 for i, t in enumerate(order)}

    total_goals = sum(r['hg'] + r['ag'] for r in rows)
    league_avg = round(total_goals / len(rows), 3) if rows else None
    for r in rows:
        r['rank_h'] = rank[r['home']]
        r['rank_a'] = rank[r['away']]

    return {
        'league': league, 'season': season,
        'league_avg': league_avg,
        'standings': [{'rank': rank[t], 'team': t, 'points': pts[t], 'gd': gd[t], 'gf': gf[t]} for t in order],
        'matches': rows,
    }


if __name__ == '__main__':
    jobs = [('bl1', '2025'), ('bl2', '2025')]
    for lg, se in jobs:
        data = build(lg, se)
        path = os.path.join(DATA, f'history_{lg}_{se}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f'{lg}/{se}: {len(data["matches"])} 场, 场均{data["league_avg"]}球, -> {path}')
