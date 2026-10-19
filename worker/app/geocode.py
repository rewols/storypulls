"""Google Places API (New) Text Search: verify each place and get coordinates."""

from urllib.parse import quote_plus

import httpx

from app.config import settings
from app.models import ExtractedPlace, Geo, Place

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.location",
    "places.rating", "places.userRatingCount", "places.googleMapsUri",
])


def _query(place: ExtractedPlace, use_local: bool) -> str:
    name = place.name_local if use_local and place.name_local else place.name
    parts = [name, place.address_hint, place.city, place.country]
    return " ".join(p for p in parts if p)


def search_url(place: ExtractedPlace) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(_query(place, use_local=False))


def _search(client: httpx.Client, text: str) -> dict | None:
    resp = client.post(SEARCH_URL, json={"textQuery": text, "pageSize": 1})
    resp.raise_for_status()
    places = resp.json().get("places") or []
    return places[0] if places else None


def geocode_place(client: httpx.Client | None, place: ExtractedPlace) -> Place:
    hit = None
    if client is not None:
        queries = [_query(place, use_local=False)]
        if place.name_local and place.name_local != place.name:
            queries.append(_query(place, use_local=True))
        for q in queries:
            try:
                hit = _search(client, q)
            except httpx.HTTPError:
                hit = None
            if hit:
                break

    if not hit or "location" not in hit:
        return Place(**place.model_dump(), geo=None, maps_url=search_url(place))

    geo = Geo(
        place_id=hit["id"],
        lat=hit["location"]["latitude"],
        lng=hit["location"]["longitude"],
        address=hit.get("formattedAddress"),
        rating=hit.get("rating"),
        rating_count=hit.get("userRatingCount"),
        matched_name=(hit.get("displayName") or {}).get("text"),
    )
    maps_url = hit.get("googleMapsUri") or f"https://www.google.com/maps/place/?q=place_id:{geo.place_id}"
    return Place(**place.model_dump(), geo=geo, maps_url=maps_url)


def geocode_all(places: list[ExtractedPlace]) -> list[Place]:
    if not settings.google_maps_api_key:
        return [geocode_place(None, p) for p in places]
    headers = {"X-Goog-Api-Key": settings.google_maps_api_key, "X-Goog-FieldMask": FIELD_MASK}
    with httpx.Client(headers=headers, timeout=15) as client:
        return [geocode_place(client, p) for p in places]
