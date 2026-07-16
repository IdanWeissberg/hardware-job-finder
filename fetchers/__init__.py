from .workday import fetch_workday
from .greenhouse import fetch_greenhouse
from .lever import fetch_lever
from .comeet import fetch_comeet
from .amazon import fetch_amazon
from .apple import fetch_apple
from .microsoft import fetch_microsoft
from .smartrecruiters import fetch_smartrecruiters
from .icims import fetch_icims
from .google_careers import fetch_google
from .eightfold import fetch_eightfold
from .eightfold_sitemap import fetch_eightfold_sitemap
from .workable import fetch_workable
from .scraper import fetch_scraper
from .linkedin_search import fetch_linkedin_search

FETCHER_MAP = {
    "workday": fetch_workday,
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "comeet": fetch_comeet,
    "amazon": fetch_amazon,
    "apple": fetch_apple,
    "microsoft": fetch_microsoft,
    "smartrecruiters": fetch_smartrecruiters,
    "icims": fetch_icims,
    "google": fetch_google,
    "eightfold": fetch_eightfold,
    "eightfold_sitemap": fetch_eightfold_sitemap,
    "workable": fetch_workable,
    "scraper": fetch_scraper,
    "linkedin_search": fetch_linkedin_search,
}
