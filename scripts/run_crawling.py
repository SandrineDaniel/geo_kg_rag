"""
run_crawling.py
===============
Script to crawl and extract content from seed URLs.

Iterates over a list of manually selected seed URLs related to
Greenland and Arctic defense, fetches each page using Trafilatura,
and saves the cleaned text to data/raw/crawler_output.jsonl.

Pages with fewer than 500 words are automatically discarded.

Run with:
    python scripts/run_crawling.py

Output:
    data/raw/crawler_output.jsonl
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.crawling import process_url

seed_urls = [
   
    "https://www.reuters.com/business/aerospace-defense/sweden-send-fighter-jets-patrol-around-greenland-part-natos-arctic-sentry-2026-02-12/",
    "https://apnews.com/article/35855929d7709c60e1192bb6778df712",
    "https://www.lemonde.fr/en/international/article/2026/02/12/nato-launches-new-arctic-defense-initiative-after-greenland-crisis_6750421_4.html",
    "https://www.theguardian.com/world/2026/feb/14/denmark-us-powers-legal-action-greenland-washington-donald-trump-europe",
    "https://apnews.com/article/2b12bb104faaaafda2ed270febfb0522",
    "https://commonslibrary.parliament.uk/research-briefings/cbp-10472/",
    "https://www.thearcticinstitute.org/trump-greenland-logic-chaos/",
    "https://english.elpais.com/international/2026-01-12/how-trump-can-take-greenland-the-easy-way-or-the-hard-way.html",
    "https://english.elpais.com/international/2026-01-10/a-trump-intervention-in-greenland-would-destroy-nato.html",
    "https://english.elpais.com/economy-and-business/2026-01-20/the-us-europe-standoff-reaches-davos-set-to-hold-a-critical-meeting-on-greenland.html",
    "https://www.gov.uk/government/speeches/foreign-secretary-statement-to-the-house-on-greenland-and-wider-arctic-security",

    
    "https://en.wikipedia.org/wiki/Greenland",
    "https://en.wikipedia.org/wiki/Politics_of_Greenland",
    "https://en.wikipedia.org/wiki/Denmark%E2%80%93United_States_relations",
    "https://en.wikipedia.org/wiki/Arctic_Council",
    "https://en.wikipedia.org/wiki/NATO",
    "https://en.wikipedia.org/wiki/Arctic_policy_of_the_United_States",
    "https://en.wikipedia.org/wiki/Greenland_in_World_War_II",
    "https://en.wikipedia.org/wiki/Pituffik_Space_Base",
    "https://en.wikipedia.org/wiki/Donald_Trump_foreign_policy",
    "https://en.wikipedia.org/wiki/Foreign_policy_of_Denmark",
    "https://en.wikipedia.org/wiki/Arctic_sovereignty",
    "https://en.wikipedia.org/wiki/Mette_Frederiksen",
    "https://en.wikipedia.org/wiki/Mark_Rutte",
    "https://en.wikipedia.org/wiki/Ursula_von_der_Leyen",

    
    "https://www.thearcticinstitute.org/greenland-arctic-strategy-trump/",
    "https://www.thearcticinstitute.org/nato-arctic-defense-greenland/",
    "https://www.bbc.com/news/articles/c9dlgpgl34go",
    "https://www.dw.com/en/greenland-trump-denmark-what-you-need-to-know/a-71302579",
    "https://www.politico.eu/article/donald-trump-greenland-denmark-europe-security-nato/",
    "https://www.aljazeera.com/news/2025/1/8/why-does-trump-want-to-buy-greenland",
    "https://foreignpolicy.com/2025/01/07/trump-greenland-denmark-buy-purchase-annexation/",
    "https://www.cfr.org/backgrounder/trumps-greenland-gambit",
]
for url in seed_urls:
    process_url(url)