# Copyright 2026 Google LLC
# Seed script for Smart Weather & Lifestyle Assistant Firestore backend.

import datetime
from google.cloud import firestore

# IMPORTANT: Hardcode project ID as string.
# Do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT env var.
GCP_PROJECT_ID = "qwiklabs-gcp-02-6bcd5cb9c516"

COLLECTION_NAME = "saved_locations"

SEED_LOCATIONS = [
    {
        "city": "San Francisco",
        "state_country": "CA, USA",
        "temperature_pref": "mild",
        "activity": "Running",
        "notes": "Loves foggy mornings and cool jogging routes near Golden Gate Park.",
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "city": "New York",
        "state_country": "NY, USA",
        "temperature_pref": "warm",
        "activity": "Park Walk",
        "notes": "Prefers sunny afternoon walks in Central Park.",
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "city": "Tokyo",
        "state_country": "Japan",
        "temperature_pref": "moderate",
        "activity": "Sightseeing",
        "notes": "Enjoys clear skies for exploring Shibuya and Shinjuku.",
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
]


def seed_firestore():
    print(f"Connecting to Firestore for project: '{GCP_PROJECT_ID}'...")
    db = firestore.Client(project=GCP_PROJECT_ID)

    collection_ref = db.collection(COLLECTION_NAME)

    for item in SEED_LOCATIONS:
        doc_id = item["city"].lower().replace(" ", "_")
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(item)
        print(f"  ✓ Seeded location: '{item['city']}' -> document ID '{doc_id}'")

    print("\n✅ Firestore seeding complete!")


if __name__ == "__main__":
    seed_firestore()
