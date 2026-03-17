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
    "https://www.gov.uk/government/speeches/foreign-secretary-statement-to-the-house-on-greenland-and-wider-arctic-security"
]
for url in seed_urls:
    process_url(url)