"""Tests for NeighbourGraph — geo/neighbours.py."""

import pytest

from agromind.geo.neighbours import NeighbourGraph


NEIGHBOUR_CSV = "bolbhav-data/District Neighbour Map India.csv"


@pytest.fixture(scope="module")
def graph():
    return NeighbourGraph(NEIGHBOUR_CSV)


class TestNeighbourGraphLoad:
    def test_loads_without_error(self):
        g = NeighbourGraph(NEIGHBOUR_CSV)
        assert g is not None

    def test_district_count_nonzero(self, graph):
        assert graph.total_districts > 0


class TestNeighbourGraphLookup:
    def test_get_neighbours_returns_list(self, graph):
        neighbours = graph.get_neighbours(state="Punjab", district="Ludhiana")
        assert isinstance(neighbours, list)
        assert len(neighbours) > 0

    def test_get_neighbours_structure(self, graph):
        neighbours = graph.get_neighbours(state="Punjab", district="Ludhiana")
        # Each neighbour should be a dict with district name
        for n in neighbours:
            assert "district_name" in n

    def test_get_neighbours_case_insensitive(self, graph):
        n1 = graph.get_neighbours(state="Punjab", district="Ludhiana")
        n2 = graph.get_neighbours(state="PUNJAB", district="ludhiana")
        assert {d["district_name"] for d in n1} == {d["district_name"] for d in n2}

    def test_unknown_district_returns_empty(self, graph):
        result = graph.get_neighbours(state="Punjab", district="NoSuchDistrict")
        assert result == []

    def test_get_neighbour_names(self, graph):
        names = graph.get_neighbour_names(state="Punjab", district="Ludhiana")
        assert isinstance(names, list)
        assert len(names) > 0
        assert all(isinstance(n, str) for n in names)

    def test_are_neighbours_true(self, graph):
        # Ludhiana should be adjacent to at least one known Punjab district
        neighbours = graph.get_neighbour_names(state="Punjab", district="Ludhiana")
        assert len(neighbours) > 0
        first_neighbour = neighbours[0]
        assert graph.are_neighbours(
            state1="Punjab", district1="Ludhiana",
            state2="Punjab", district2=first_neighbour,
        )

    def test_are_neighbours_false(self, graph):
        # Ludhiana and a far-away district should not be neighbours
        assert not graph.are_neighbours(
            state1="Punjab", district1="Ludhiana",
            state2="Uttar Pradesh", district2="Agra",
        )
