class VectorException(Exception):
    pass


class VectorDimensionMismatch(VectorException):
    def __init__(self, collection: str, expected: int, actual: int) -> None:
        super().__init__(f"Vector dimension mismatch for {collection}: expected {expected}, got {actual}")


class CollectionNotFound(VectorException):
    def __init__(self, collection: str) -> None:
        super().__init__(f"Collection not found: {collection}")


class VectorUpsertFailed(VectorException):
    def __init__(self, material_id: str, reason: str) -> None:
        super().__init__(f"Failed to upsert vector for {material_id}: {reason}")


class VectorNotFound(VectorException):
    def __init__(self, point_id: str) -> None:
        super().__init__(f"Vector not found: {point_id}")
