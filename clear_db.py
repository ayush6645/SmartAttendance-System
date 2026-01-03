import firebase_admin
from firebase_admin import credentials, firestore

# --- Initialize Firestore ---
# Make sure your serviceAccountKey.json is in the same folder
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    print("Please ensure 'serviceAccountKey.json' is present and valid.")
    exit()

def delete_collection(coll_ref, batch_size):
    """
    Deletes all documents in a collection in batches.
    """
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        doc.reference.delete()
        deleted += 1

    # Recurse until the collection is empty
    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


# --- Main Deletion Logic ---

# Add the names of all collections you want to clear to this list.
# I've included all the ones we've discussed.
collections_to_delete = [
    'users', 
    'teachers', # To remove the old, obsolete collection
    'courses', 
    'rooms', 
    'branches',
    'timetable' # Clearing timetable entries as well
]

print("🧹 Starting to clean the pantry (deleting collections)...")

for coll_name in collections_to_delete:
    try:
        coll_ref = db.collection(coll_name)
        print(f"\nAttempting to delete all documents in '{coll_name}'...")
        delete_collection(coll_ref, 100) # Deleting 100 documents at a time
        print(f"✅ Successfully cleared '{coll_name}'.")
    except Exception as e:
        # This can happen if a collection doesn't exist, which is fine.
        print(f"Could not process collection '{coll_name}'. It might not exist. Error: {e}")

print("\n✨ Pantry cleaning complete! Your Firestore is ready for fresh data.")