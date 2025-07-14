try:
    db.collection('test').document('test_doc').set({'test': 'success'})
    print("Firestore connection successful")
except Exception as e:
    print(f"Firestore connection failed: {e}")