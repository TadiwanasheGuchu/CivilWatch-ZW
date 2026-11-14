"""Boundaries, locating councils, map clusters and nearby search."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.cli import load_sample_boundaries
from tests.conftest import csrf_headers
from tests.issue_helpers import new_resident, report_payload, set_status, setup_councils, submit
from tests.operations_helpers import build_council

HARARE_CENTRE = (-17.8292, 31.0522)


def square(lat: float, lon: float, half: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lon - half, lat - half],
                [lon + half, lat - half],
                [lon + half, lat + half],
                [lon - half, lat + half],
                [lon - half, lat - half],
            ]
        ],
    }


def put_boundary(
    client: TestClient, session: dict, council_id: str, geometry: dict, source="official"
):
    return client.put(
        f"/api/v1/councils/{council_id}/boundary",
        json={"geometry": geometry, "source": source},
        headers=csrf_headers(session),
    )


@pytest.fixture
def world(make_client: Callable[[], TestClient]):
    return setup_councils(make_client)


# --- Boundaries ------------------------------------------------------------------------------


def test_platform_admin_sets_a_boundary(world) -> None:
    platform, session = world["platform"], world["platform_session"]
    lat, lon = HARARE_CENTRE
    response = put_boundary(platform, session, world["harare"]["id"], square(lat, lon, 0.1))
    assert response.status_code == 200, response.text
    body = response.json()
    assert 400 < body["area_km2"] < 600
    assert body["vertex_count"] == 5
    assert body["overlaps"] == []
    audit = platform.get(f"/api/v1/councils/{world['harare']['id']}/audit-logs").json()["items"]
    assert audit[0]["action"] == "council.boundary_set"
    assert audit[0]["details"]["source"] == "official"


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "Feature", "properties": {}, "geometry": square(-17.83, 31.05, 0.05)},
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": square(-17.83, 31.05, 0.05)}
            ],
        },
        {"type": "MultiPolygon", "coordinates": [square(-17.83, 31.05, 0.05)["coordinates"]]},
    ],
    ids=["feature", "feature-collection", "multipolygon"],
)
def test_common_geojson_shapes_are_accepted(world, geometry) -> None:
    response = put_boundary(
        world["platform"], world["platform_session"], world["harare"]["id"], geometry
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize(
    ("geometry", "message"),
    [
        (
            {"type": "LineString", "coordinates": [[31.0, -17.8], [31.1, -17.9]]},
            "Polygon or MultiPolygon",
        ),
        (
            {
                "type": "Polygon",
                "coordinates": [
                    [[31.0, -17.8], [31.1, -17.9], [31.1, -17.8], [31.0, -17.9], [31.0, -17.8]]
                ],
            },
            "invalid",
        ),
        (square(31.05, -17.83, 0.05), "longitude, latitude"),  # swapped coordinates
        (square(51.5, -0.12, 0.05), "outside the area"),
        ({"type": "Polygon", "coordinates": "not coordinates"}, "not valid GeoJSON"),
        ({"type": "FeatureCollection", "features": []}, "one feature"),
    ],
    ids=["linestring", "bowtie", "swapped", "london", "garbage", "empty-collection"],
)
def test_bad_boundaries_are_explained(world, geometry, message) -> None:
    response = put_boundary(
        world["platform"], world["platform_session"], world["harare"]["id"], geometry
    )
    assert response.status_code == 422, response.text
    detail = response.json()["error"]["details"][0]
    assert detail["location"] == ["body", "geometry"]
    assert message in detail["message"]


def test_only_platform_admins_change_boundaries(make_client) -> None:
    c = build_council(make_client)
    for actor in (c["admin"], c["resident"]):
        response = put_boundary(
            actor.client, actor.session, c["council_id"], square(-17.83, 31.05, 0.05)
        )
        assert response.status_code == 403
    response = c["admin"].client.delete(
        f"/api/v1/councils/{c['council_id']}/boundary", headers=csrf_headers(c["admin"].session)
    )
    assert response.status_code == 403


def test_overlaps_are_reported_and_boundaries_can_be_cleared(world) -> None:
    platform, session = world["platform"], world["platform_session"]
    put_boundary(platform, session, world["harare"]["id"], square(-17.83, 31.05, 0.1))
    second = put_boundary(
        platform, session, world["bulawayo"]["id"], square(-17.80, 31.08, 0.1)
    ).json()
    assert second["overlaps"] == ["Harare City Council"]
    cleared = platform.delete(
        f"/api/v1/councils/{world['bulawayo']['id']}/boundary", headers=csrf_headers(session)
    )
    assert cleared.status_code == 204
    names = [
        f["properties"]["slug"]
        for f in platform.get("/api/v1/councils/boundaries").json()["features"]
    ]
    assert names == ["harare"]


def test_public_boundaries_and_locate(world, client: TestClient, owner_engine: Engine) -> None:
    platform, session = world["platform"], world["platform_session"]
    put_boundary(platform, session, world["harare"]["id"], square(-17.83, 31.05, 0.2), "sample")
    put_boundary(platform, session, world["bulawayo"]["id"], square(-17.83, 31.05, 0.05))
    boundaries = client.get("/api/v1/councils/boundaries")
    assert boundaries.headers["Cache-Control"] == "public, max-age=300"
    features = {f["properties"]["slug"]: f for f in boundaries.json()["features"]}
    assert features["harare"]["properties"]["is_sample"] is True
    assert features["bulawayo"]["properties"]["is_sample"] is False
    assert features["harare"]["geometry"]["type"] == "MultiPolygon"

    located = client.get("/api/v1/councils/locate?latitude=-17.83&longitude=31.05").json()
    assert [c["slug"] for c in located] == ["bulawayo", "harare"]  # smallest area first
    assert located[1]["is_sample_boundary"] is True
    assert client.get("/api/v1/councils/locate?latitude=-20.15&longitude=28.58").json() == []
    assert client.get("/api/v1/councils/locate?latitude=95&longitude=0").status_code == 422

    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE councils SET is_active = false WHERE slug = 'bulawayo'"))
    assert [
        f["properties"]["slug"]
        for f in client.get("/api/v1/councils/boundaries").json()["features"]
    ] == ["harare"]


def test_sample_boundaries_command(client: TestClient, owner_engine: Engine) -> None:
    report = load_sample_boundaries(create_missing=True)
    assert len(report) == 6 and all("sample boundary loaded" in line for line in report)
    located = client.get("/api/v1/councils/locate?latitude=-17.8292&longitude=31.0522").json()
    assert [c["slug"] for c in located] == ["harare"]
    assert located[0]["is_sample_boundary"] is True
    bulawayo = client.get("/api/v1/councils/locate?latitude=-20.15&longitude=28.5833").json()
    assert [c["slug"] for c in bulawayo] == ["bulawayo"]
    # An official boundary is never replaced by a sample one.
    with owner_engine.begin() as connection:
        connection.execute(
            text("UPDATE councils SET boundary_source = 'official' WHERE slug = 'harare'")
        )
    again = load_sample_boundaries()
    assert "harare: kept its official boundary" in again


def test_reports_outside_a_sample_boundary_are_refused(make_client) -> None:
    load_sample_boundaries(create_missing=True)
    client, session = new_resident(make_client, "r@example.com")
    councils = {c["slug"]: c["id"] for c in client.get("/api/v1/councils").json()["items"]}
    categories = {c["code"]: c["id"] for c in client.get("/api/v1/categories").json()}
    world = {"harare": {"id": councils["harare"]}, "categories": categories}
    inside = submit(client, session, report_payload(world))
    assert inside.status_code == 201
    # Bulawayo's coordinates, sent to Harare.
    outside = submit(client, session, report_payload(world, latitude=-20.15, longitude=28.5833))
    assert outside.status_code == 422


# --- Map clusters --------------------------------------------------------------------------------


@pytest.fixture
def mapped(make_client, owner_engine):
    world = setup_councils(make_client)
    reporter, session = new_resident(make_client, "mapper@example.com")
    ids = {}
    points = {
        "a": (-17.8292, 31.0522),
        "b": (-17.8295, 31.0525),  # ~40 m from a
        "c": (-17.8000, 31.0700),  # about 4 km away
        "private": (-17.8292, 31.0522),
        "unverified": (-17.8292, 31.0522),
    }
    for name, (lat, lon) in points.items():
        ids[name] = submit(
            reporter,
            session,
            report_payload(
                world,
                latitude=lat,
                longitude=lon,
                visibility="PRIVATE" if name == "private" else "PUBLIC",
                category_id=world["categories"]["water" if name == "c" else "roads"],
            ),
        ).json()["id"]
    for name in ("a", "b", "c", "private"):
        set_status(owner_engine, ids[name], "VERIFIED")
    set_status(owner_engine, ids["c"], "RESOLVED")
    return {**world, "ids": ids}


BBOX = "30.9,-17.95,31.2,-17.7"


def test_public_clusters_contain_only_published_public_reports(mapped, client: TestClient) -> None:
    low = client.get(f"/api/v1/map/clusters?bbox={BBOX}&zoom=8").json()
    assert low["total"] == 3
    assert len(low["clusters"]) < 3  # grouped at low zoom
    high = client.get(f"/api/v1/map/clusters?bbox={BBOX}&zoom=20").json()
    singles = {c["issue_id"] for c in high["clusters"] if c["count"] == 1}
    assert singles == {mapped["ids"]["a"], mapped["ids"]["b"], mapped["ids"]["c"]}
    assert mapped["ids"]["private"] not in str(high) and mapped["ids"]["unverified"] not in str(
        high
    )


def test_cluster_filters_and_validation(mapped, client: TestClient) -> None:
    def total(query: str) -> int:
        return client.get(f"/api/v1/map/clusters?bbox={BBOX}&zoom=12&{query}").json()["total"]

    assert total("category=water") == 1
    assert total("status=RESOLVED") == 1
    assert total(f"council_id={mapped['bulawayo']['id']}") == 0
    assert client.get("/api/v1/map/clusters?bbox=28,-21,29,-20&zoom=12").json()["total"] == 0
    for bad in ("bbox=31,-17,30,-18&zoom=5", "bbox=nonsense&zoom=5", f"bbox={BBOX}&zoom=30"):
        assert client.get(f"/api/v1/map/clusters?{bad}").status_code == 422, bad


def test_staff_clusters_include_private_reports_of_their_council_only(
    make_client, owner_engine
) -> None:
    c = build_council(make_client)  # its report is PRIVATE and unverified
    staff = c["verifier"].get(f"{c['base']}/map/clusters?bbox={BBOX}&zoom=20").json()
    assert staff["total"] == 1
    assert c["resident"].get(f"{c['base']}/map/clusters?bbox={BBOX}&zoom=20").status_code == 403
    public = make_client().get(f"/api/v1/map/clusters?bbox={BBOX}&zoom=20").json()
    assert public["total"] == 0


# --- Nearby ---


def test_nearby_public_reports_are_sorted_and_limited(mapped, client: TestClient) -> None:
    rows = client.get(
        "/api/v1/issues/nearby?latitude=-17.8292&longitude=31.0522&radius_m=200"
    ).json()
    assert [r["id"] for r in rows] == [mapped["ids"]["a"], mapped["ids"]["b"]]
    assert rows[0]["distance_m"] < 1 and 20 < rows[1]["distance_m"] < 80
    assert all("reporter" not in str(r) for r in rows)
    wide = client.get(
        "/api/v1/issues/nearby?latitude=-17.8292&longitude=31.0522&radius_m=5000"
    ).json()
    assert mapped["ids"]["c"] in [r["id"] for r in wide]
    water = client.get(
        "/api/v1/issues/nearby?latitude=-17.8292&longitude=31.0522&radius_m=5000&category=water"
    ).json()
    assert [r["id"] for r in water] == [mapped["ids"]["c"]]
    assert (
        client.get("/api/v1/issues/nearby?latitude=-17.8&longitude=31&radius_m=99999").status_code
        == 422
    )


def test_staff_nearby_finds_possible_duplicates_in_their_council(make_client) -> None:
    c = build_council(make_client)
    resident = c["resident"]
    twin = submit(resident.client, resident.session, report_payload(c)).json()
    elsewhere = submit(
        resident.client, resident.session, report_payload(c, council_id=c["bulawayo"]["id"])
    ).json()  # same spot, other council
    rows = c["verifier"].get(f"{c['issue_url']}/nearby?radius_m=100").json()
    ids = [r["id"] for r in rows]
    assert ids == [twin["id"]]
    assert elsewhere["id"] not in ids and c["issue"]["id"] not in ids
    assert rows[0]["distance_m"] < 1
    assert c["resident"].get(f"{c['issue_url']}/nearby").status_code == 403
