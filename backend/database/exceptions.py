class DatabaseError(Exception):
    pass

class RecordNotFoundError(DatabaseError):
    pass

class StorageError(DatabaseError):
    pass
