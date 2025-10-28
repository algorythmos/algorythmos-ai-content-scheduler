# linkedin_poster.py
import os, requests

def post_to_linkedin(text: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('LINKEDIN_ACCESS_TOKEN')}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202510",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    payload = {
        "author": os.getenv("LINKEDIN_ORG_URN"),
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED"},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    r = requests.post("https://api.linkedin.com/rest/posts", headers=headers, json=payload)
    r.raise_for_status()
    urn = r.headers.get("x-restli-id") or r.json().get("id")
    return f"https://www.linkedin.com/feed/update/{urn}"
