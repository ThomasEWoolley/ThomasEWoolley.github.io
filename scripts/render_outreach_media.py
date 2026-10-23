#!/usr/bin/env python3
"""Regenerate the dated outreach cards from data/outreach-media.json."""

from collections import defaultdict
from datetime import date
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def chronology_key(entry):
    published = date.fromisoformat(entry['published'])
    if 'event_year' in entry:
        return (int(entry['event_year']), 0, 0, entry['id'])
    return (published.year, published.month, published.day, entry['id'])


def render():
    records = json.loads((ROOT / 'data/outreach-media.json').read_text(encoding='utf-8'))
    keys = [(entry['platform'], entry['id']) for entry in records]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate media entry')
    years = defaultdict(list)
    for entry in sorted(records, key=chronology_key, reverse=True):
        published = date.fromisoformat(entry['published'])
        years[int(entry.get('event_year', published.year))].append((entry, published))

    lines = [
        '      <section class="section section-tint" id="videos">',
        '        <div class="container">',
        '          <div class="section-heading">',
        '            <h2>Videos and social media</h2>',
        '            <p>Talks, demonstrations, interviews and social posts, newest first. Dates are publication dates unless an event year is shown.</p>',
        '          </div>',
        '          <nav class="media-year-nav" aria-label="Browse media by year">',
        '            ' + ' '.join(f'<a href="#media-{year}">{year}</a>' for year in years),
        '          </nav>',
    ]
    for year, entries in years.items():
        lines.extend([
            f'          <section class="media-year" aria-labelledby="media-{year}">',
            f'            <h3 id="media-{year}">{year}</h3>',
            '            <div class="media-grid">',
        ])
        for entry, published in entries:
            platform = entry['platform']
            lines.append(f'              <a class="media-card dated-media-card" href="{escape(entry["url"], quote=True)}">')
            if platform == 'YouTube':
                lines.append(f'                <img src="https://i.ytimg.com/vi/{escape(entry["id"], quote=True)}/mqdefault.jpg" width="320" height="180" loading="lazy" alt="">')
            else:
                lines.append(f'                <img class="instagram-thumbnail" src="{escape(entry["thumbnail"], quote=True)}" width="320" height="180" loading="lazy" alt="">')
            if 'event_year' in entry:
                date_label = f'{int(entry["event_year"])} (event year)'
            else:
                date_label = f'<time datetime="{published.isoformat()}">{published.day} {published.strftime("%B %Y")}</time>'
            lines.extend([
                '                <div class="media-card-details">',
                f'                  <span class="media-card-title">{escape(entry["title"])}</span>',
                f'                  <p class="media-card-date">{platform} · {date_label}</p>',
            ])
            if entry.get('channel'):
                lines.append(f'                  <p class="media-card-channel">{escape(entry["channel"])}</p>')
            if entry.get('description'):
                lines.append(f'                  <p class="media-card-description">{escape(entry["description"])}</p>')
            lines.extend(['                </div>', '              </a>'])
        lines.extend(['            </div>', '          </section>'])
    lines.extend(['        </div>', '      </section>'])
    page = ROOT / 'outreach.html'
    source = page.read_text(encoding='utf-8')
    pattern = r'      <section class="section section-tint" id="videos">.*?(?=      <section class="section" id="audio">)'
    updated, count = re.subn(pattern, lambda match: '\n'.join(lines) + '\n', source, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Could not locate the outreach media section')
    page.write_text(updated, encoding='utf-8')
    print(f'Rendered {len(records)} media cards across {len(years)} years.')


if __name__ == '__main__':
    render()
