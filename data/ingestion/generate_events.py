"""Generate synthetic user signature events for streaming simulation."""

import json
import random
import uuid
from datetime import datetime
from pathlib import Path

from faker import Faker

from contracts.schemas.petition_events import SignatureSource, UserSignatureEvent

fake = Faker()


class EventGenerator:
    """Generate realistic synthetic user events."""

    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_signature_event(self, petition_id: int) -> UserSignatureEvent:
        """Generate a single signature event."""
        return UserSignatureEvent(
            event_id=str(uuid.uuid4()),
            petition_id=petition_id,
            user_id=str(uuid.uuid4()),
            user_email=fake.email(),
            user_name=fake.name(),
            user_ip=fake.ipv4(),
            source=random.choice(list(SignatureSource)),
            signed_at=fake.date_time_between(start_date="-30d", end_date="now"),
            country=fake.country_code(),
            postcode=fake.postcode() if random.random() > 0.3 else None,
        )

    def generate_batch(
        self, petition_ids: list[int], events_per_petition: int = 100
    ) -> list[UserSignatureEvent]:
        """Generate batch of events for multiple petitions."""
        events = []
        for petition_id in petition_ids:
            count = random.randint(1, events_per_petition)
            for _ in range(count):
                events.append(self.generate_signature_event(petition_id))
        return events

    def save_events(self, events: list[UserSignatureEvent], run_id: str) -> str:
        """Save events to bronze layer."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"user_events_{timestamp}_{run_id}.json"
        data = [e.model_dump(mode="json") for e in events]
        path.write_text(json.dumps(data, indent=2, default=str))
        return str(path)

    def run(
        self, petition_ids: list[int], events_per_petition: int = 100, run_id: str = "manual"
    ) -> dict[str, any]:
        """Generate and save events."""
        events = self.generate_batch(petition_ids, events_per_petition)
        path = self.save_events(events, run_id)
        return {"path": path, "event_count": len(events)}


if __name__ == "__main__":
    # Example: generate events for petition IDs 1-10
    generator = EventGenerator()
    result = generator.run(petition_ids=list(range(1, 11)), events_per_petition=50)
    print(f"Generated: {result}")
