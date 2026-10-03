# ShopSignal

ShopSignal gives a small seller a city-targeted Google Shopping snapshot for one specific product. It shows returned titles, sellers, listed prices, links, and a median/range computed only from the numeric prices SerpApi returned. A seller may enter their own price to see where it sits relative to that sample.

The app does not claim the results are perfect matches, advise a final selling price, copy product facts, or promise sales. Sellers should verify size, condition, availability, shipping, tax, and currency directly on each listing. Product descriptions should use only facts the seller confirms.

## Run locally

Requires Python 3.10+ and a SerpApi API key. The app uses only Python's standard library.

```sh
export SERPAPI_API_KEY='your-key'
python server.py
```

Open `http://127.0.0.1:8000`. The key is read from the server environment, never sent to the browser, and never written to a file by ShopSignal. Keep the server bound to localhost; do not expose it publicly without adding authentication and deployment security.

The app calls SerpApi's `google_shopping` engine with `gl=in`, `hl=en`, and the supplied city/region. It caches identical queries in memory for one hour and limits new searches to one every four seconds. SerpApi currently advertises 250 free searches per month; API availability, quota, and terms are controlled by SerpApi. Search data may be incomplete or stale.

## Hackathon context

Potential track: **Commerce & Market Intelligence**. This is a new, standalone project prepared for the SerpApi India Hackathon. The official event requires an eligible India-resident participant aged 18+, meaningful SerpApi usage, a public GitHub repository, and a publicly accessible demo under three minutes. It lists cash awards for winners, but entry is competitive and no award is guaranteed. The project has not been submitted.

AI-assisted implementation must be disclosed in any submission. The account holder must review the code, confirm eligibility, supply participant details, record the live demo with their own API key, accept the official rules and terms, and submit through the event dashboard. Do not put the API key in GitHub or the demo.

## Local setup for Termux

No Python packages need installing. Set the key in the shell that starts the server, run `python server.py`, then open the local address in the phone browser. Do not paste the key into chat or into a public issue.
