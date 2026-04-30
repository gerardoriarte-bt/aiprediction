"""Domain errors for the clients repository."""

from __future__ import annotations


class ClientNotFoundError(Exception):
    def __init__(self, identifier):
        self.identifier = identifier
        super().__init__(f"Client not found: {identifier}")


class ClientSlugTaken(Exception):
    def __init__(self, slug: str):
        self.slug = slug
        super().__init__(f"Slug already in use: {slug}")
