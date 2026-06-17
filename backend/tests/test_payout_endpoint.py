def test_payout_models_importable_and_persist(db):
    import uuid
    from app.models.payout import Payout, PayoutItem

    payout = Payout(event_id=uuid.uuid4(), allocation_id=uuid.uuid4(),
                    team_label="Team Satoshi", total_sats=210, status="pending")
    db.add(payout)
    db.flush()
    item = PayoutItem(payout_id=payout.id, participant_id=uuid.uuid4(),
                      lightning_address="ada@getalby.com", amount_sats=105, status="pending")
    db.add(item)
    db.commit()
    assert payout.id is not None and item.payout_id == payout.id
