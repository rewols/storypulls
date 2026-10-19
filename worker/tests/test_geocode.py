import json

import httpx

from app.geocode import geocode_place
from app.models import ExtractedPlace

PLACE = ExtractedPlace(
    name="Xingbo Coffee", name_local="興波咖啡", category="cafe", address_hint="Huashan 1914",
    city="Taipei", country="Taiwan", description="Award-winning pour-over.",
    evidence=[{"source": "caption", "detail": "Simple Kaffa 興波咖啡"}], confidence="high",
)

HIT = {
    "id": "ChIJabc", "displayName": {"text": "Simple Kaffa Flagship"},
    "formattedAddress": "No. 1, Bade Rd, Zhongzheng District, Taipei",
    "location": {"latitude": 25.0441, "longitude": 121.5293},
    "rating": 4.5, "userRatingCount": 3210, "googleMapsUri": "https://maps.google.com/?cid=123",
}


def client_with(responses):
    queries = []

    def handler(request):
        queries.append(json.loads(request.content)["textQuery"])
        return httpx.Response(200, json=responses.pop(0))

    return httpx.Client(transport=httpx.MockTransport(handler)), queries


def test_hit_on_first_query():
    client, queries = client_with([{"places": [HIT]}])
    place = geocode_place(client, PLACE)
    assert queries == ["Xingbo Coffee Huashan 1914 Taipei Taiwan"]
    assert place.geo.place_id == "ChIJabc"
    assert place.geo.lat == 25.0441
    assert place.maps_url == "https://maps.google.com/?cid=123"


def test_falls_back_to_local_name():
    client, queries = client_with([{}, {"places": [HIT]}])
    place = geocode_place(client, PLACE)
    assert queries[1].startswith("興波咖啡")
    assert place.geo is not None


def test_no_match_keeps_place_with_search_link():
    client, _ = client_with([{}, {}])
    place = geocode_place(client, PLACE)
    assert place.geo is None
    assert place.maps_url.startswith("https://www.google.com/maps/search/?api=1&query=Xingbo+Coffee")


def test_no_api_key_means_unverified():
    place = geocode_place(None, PLACE)
    assert place.geo is None and "maps/search" in place.maps_url
