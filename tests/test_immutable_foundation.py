from datetime import datetime, timedelta, timezone

import pytest

from meme_coin_radar.models import (
    CandidateObservation,
    FomoExecutability,
    ObservationStore,
    Provenance,
    TokenIdentity,
)


@pytest.fixture
def base_time():
    return datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)


def test_token_identity_requires_chain_and_contract(base_time):
    with pytest.raises(ValueError):
        TokenIdentity(
            chain='base',
            contract_address='',
            symbol='MCR',
            observed_at=base_time,
            provenance=Provenance(source_id='source-1', source_type='manual', observed_at=base_time),
        )

    with pytest.raises(ValueError):
        TokenIdentity(
            chain='',
            contract_address='0x1234',
            symbol='MCR',
            observed_at=base_time,
            provenance=Provenance(source_id='source-1', source_type='manual', observed_at=base_time),
        )


def test_validation_requires_timestamp_and_provenance(base_time):
    with pytest.raises(ValueError):
        CandidateObservation(
            coin_id='base:0x1234',
            observed_at=None,
            narrative='Community narrative is visible.',
            provenance=Provenance(source_id='source-1', source_type='manual', observed_at=base_time),
        )

    with pytest.raises(ValueError):
        CandidateObservation(
            coin_id='base:0x1234',
            observed_at=base_time,
            narrative='Community narrative is visible.',
            provenance=None,
        )


def test_immutable_history_supports_as_of_reconstruction(base_time):
    store = ObservationStore()

    first = CandidateObservation(
        coin_id='base:0x1234',
        observed_at=base_time,
        narrative='Early narrative noted',
        provenance=Provenance(source_id='source-1', source_type='manual', observed_at=base_time),
    )
    second = CandidateObservation(
        coin_id='base:0x1234',
        observed_at=base_time + timedelta(minutes=10),
        narrative='Later narrative updated',
        provenance=Provenance(source_id='source-2', source_type='manual', observed_at=base_time + timedelta(minutes=10)),
    )

    store.append(first)
    store.append(second)

    as_of_first = store.as_of(base_time + timedelta(minutes=5))
    assert [record.narrative for record in as_of_first] == ['Early narrative noted']

    as_of_second = store.as_of(base_time + timedelta(minutes=30))
    assert [record.narrative for record in as_of_second] == ['Early narrative noted', 'Later narrative updated']

    with pytest.raises(AttributeError):
        store.records[0].narrative = 'tampered-history'

    assert store.as_of(base_time + timedelta(minutes=5))[0].narrative == 'Early narrative noted'
    assert first.record_id == store.records[0].record_id


def test_fomo_executability_states_are_valid():
    assert FomoExecutability.TRUE.value == 'TRUE'
    assert FomoExecutability.FALSE.value == 'FALSE'
    assert FomoExecutability.UNVERIFIED.value == 'UNVERIFIED'

    with pytest.raises(ValueError):
        FomoExecutability('MAYBE')
